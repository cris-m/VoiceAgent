import { useRef, useCallback, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useVoiceConfig } from '@context/VoiceConfigContext';
import type { VoiceConfigMessage } from '@context/VoiceConfigContext';
import type { ServerMessage } from '@typing';
import type { UseVoiceAgentReturn, UseVoiceAgentOptions } from '@typing';
import type { RootState } from '@store';
import {
  addMessage,
  updateMessage,
  setStatus,
  setIsConnected,
  setAudioLevel,
  setIsPlaying,
  setIsMuted,
  setCurrentAiMessageId,
  setCurrentPartialId,
  setCurrentThreadId,
  addThread,
  markTitleSet,
  renameThread,
  appendToMessage,
  setSampleRate,
  reset,
} from '@store';

const TARGET_SAMPLE_RATE = 16000;

const audioProcessorCode = `
class AudioCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 4800; // ~100ms at 48kHz
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;

    this.warmupChunks = 5; // skip initial chunks while mic stabilizes (~500ms @ 100ms/chunk)
    this.chunksProcessed = 0;

    this.isFirstBuffer = true;
  }

  applyFadeIn(buffer, fadeSamples) {
    const fadeLength = Math.min(fadeSamples, buffer.length);
    for (let i = 0; i < fadeLength; i++) {
      const gain = 0.5 * (1 - Math.cos(Math.PI * i / fadeLength));
      buffer[i] *= gain;
    }
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const inputChannel = input[0];
    this.chunksProcessed++;

    if (this.chunksProcessed <= this.warmupChunks) {
      return true;
    }

    for (let i = 0; i < inputChannel.length; i++) {
      this.buffer[this.bufferIndex++] = inputChannel[i];

      if (this.bufferIndex >= this.bufferSize) {
        const audioData = this.buffer.slice();

        if (this.isFirstBuffer) {
          this.applyFadeIn(audioData, 480);
          this.isFirstBuffer = false;
        }

        this.port.postMessage(audioData.buffer, [audioData.buffer]);

        this.buffer = new Float32Array(this.bufferSize);
        this.bufferIndex = 0;
      }
    }
    return true;
  }
}
registerProcessor('audio-capture-processor', AudioCaptureProcessor);
`;

function removeDCOffset(buffer: Float32Array): void {
  let sum = 0;
  for (let i = 0; i < buffer.length; i++) {
    sum += buffer[i];
  }
  const dcOffset = sum / buffer.length;

  if (Math.abs(dcOffset) > 0.001) {
    for (let i = 0; i < buffer.length; i++) {
      buffer[i] -= dcOffset;
    }
  }
}

function applyMicroFades(buffer: Float32Array, fadeSamples: number): void {
  const fadeLen = Math.min(fadeSamples, Math.floor(buffer.length / 4));

  for (let i = 0; i < fadeLen; i++) {
    const gain = i / fadeLen;
    buffer[i] *= gain;
  }

  for (let i = 0; i < fadeLen; i++) {
    const gain = i / fadeLen;
    buffer[buffer.length - 1 - i] *= gain;
  }
}

async function resampleAudio(
  audioData: Float32Array,
  sourceSampleRate: number,
  targetSampleRate: number,
  isFirstChunkRef: React.MutableRefObject<boolean>
): Promise<Int16Array> {
  removeDCOffset(audioData);

  if (sourceSampleRate === targetSampleRate) {
    const int16Data = new Int16Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) {
      const sample = Math.max(-1, Math.min(1, audioData[i]));
      int16Data[i] = Math.floor(sample * 32767);
    }
    return int16Data;
  }

  const outputLength = Math.round(audioData.length * targetSampleRate / sourceSampleRate);
  const offlineCtx = new OfflineAudioContext(1, outputLength, targetSampleRate);

  const sourceBuffer = offlineCtx.createBuffer(1, audioData.length, sourceSampleRate);
  sourceBuffer.getChannelData(0).set(audioData);

  const source = offlineCtx.createBufferSource();
  source.buffer = sourceBuffer;
  source.connect(offlineCtx.destination);
  source.start();

  const renderedBuffer = await offlineCtx.startRendering();
  const resampledData = new Float32Array(renderedBuffer.getChannelData(0));

  if (isFirstChunkRef.current) {
    applyMicroFades(resampledData, 160);
    isFirstChunkRef.current = false;
  }

  const int16Data = new Int16Array(resampledData.length);
  for (let i = 0; i < resampledData.length; i++) {
    const sample = Math.max(-1, Math.min(1, resampledData[i]));
    int16Data[i] = Math.floor(sample * 32767);
  }

  return int16Data;
}

const generateId = () => Math.random().toString(36).substring(2, 9);

export function useVoiceAgent(options: UseVoiceAgentOptions = {}): UseVoiceAgentReturn {
  const defaultWsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/voice/ws`;
  const { wsUrl = defaultWsUrl, onError, onThreadCreated } = options;
  const onThreadCreatedRef = useRef(onThreadCreated);
  onThreadCreatedRef.current = onThreadCreated;

  const dispatch = useDispatch();
  const state = useSelector((s: RootState) => s.voiceAgent);
  const {
    status,
    messages,
    isConnected,
    audioLevel,
    isMuted,
    titleSetForThreads,
  } = state;

  const voiceConfig = useVoiceConfig();

  // Keep refs in sync with Redux state to avoid stale closures in WebSocket
  // handlers and the Web Audio worklet callback.
  useEffect(() => {
    stateRef.current = state;
    statusRef.current = status;
    isMutedRef.current = isMuted;
  }, [state, status, isMuted]);

  const wsRef = useRef<WebSocket | null>(null);
  const isConnectingRef = useRef(false);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Mirror Redux isMuted into a ref so the audio-worklet callback can read it.
  const isMutedRef = useRef(false);
  // Ref-pinned versions of connect/disconnect so callbacks scheduled by
  // setTimeout or by useEffect cleanup always invoke the CURRENT version,
  // not a stale closure captured at first render. Without this, picking a
  // different voice (which re-creates voiceConfig → re-creates disconnect →
  // useEffect cleanup runs old disconnect) silently cancels pending reconnects.
  const connectRef = useRef<(() => Promise<void>) | undefined>(undefined);
  const disconnectRef = useRef<(() => void) | undefined>(undefined);
  const MAX_RECONNECT_ATTEMPTS = 30;
  const BASE_RECONNECT_DELAY_MS = 1000;  // Start with 1s, exponential backoff
  const MAX_RECONNECT_DELAY_MS = 30000;  // Cap at 30s

  const inputContextRef = useRef<AudioContext | null>(null);
  const outputContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);

  const playbackQueueRef = useRef<Int16Array[]>([]);
  const nextPlayTimeRef = useRef(0);
  const schedulerIntervalRef = useRef<number | null>(null);
  // WS → AudioContext jitter buffer. 150 × 100ms ≈ 15s headroom.
  const MAX_PLAYBACK_QUEUE_ITEMS = 150;
  const queueOverflowCountRef = useRef(0);
  const scheduleAudioRef = useRef<(() => Promise<void>) | undefined>(undefined);
  // Bubble is closed only when BOTH llmDone is true AND playback has drained
  const llmDoneRef = useRef(false);
  const isFirstChunkOfSessionRef = useRef(true);  // Per-instance state to avoid race conditions
  // Interrupt-handling state. activeSourcesRef tracks every BufferSourceNode
  // we've scheduled so we can call .stop(0) on each when interrupt fires —
  // closing the AudioContext alone doesn't synchronously stop nodes that
  // were start()-ed before close. interruptEpochRef is bumped on each
  // interrupt so in-flight decodeAudioData promises can detect they belong
  // to a stale response and bail without playing.
  const activeSourcesRef = useRef<AudioBufferSourceNode[]>([]);
  const interruptEpochRef = useRef(0);

  // Store latest Redux state in refs to avoid stale closure in event handlers
  const stateRef = useRef(state);
  const statusRef = useRef(status);

  const scheduleAudio = useCallback(async () => {
    const ctx = outputContextRef.current;
    if (!ctx || ctx.state === 'closed') return;

    if (ctx.state === 'suspended') {
      try { await ctx.resume(); } catch { return; }
    }

    const now = ctx.currentTime;
    const storeState = stateRef.current;

    if (playbackQueueRef.current.length === 0 && storeState.isPlaying) {
      if (nextPlayTimeRef.current <= now + 0.1) {
        // Inter-sentence drain guard: TTS works one sentence at a time, so
        // the playback queue briefly empties between sentences while the
        // next one synthesizes. Dropping status to 'listening' here causes
        // a visible blink as the next chunk flips it back to 'speaking'.
        // Only declare the response complete once the LLM has signalled
        // done (text_stream done=true) AND the queue has drained.
        if (!llmDoneRef.current) {
          return;
        }
        dispatch(setIsPlaying(false));
        dispatch(setStatus('listening'));
        dispatch(setCurrentAiMessageId(null));
        llmDoneRef.current = false;
        return;
      }
    }

    if (playbackQueueRef.current.length === 0) return;

    if (nextPlayTimeRef.current < now) {
      nextPlayTimeRef.current = now;
    }

    // Capture the epoch at the start of this scheduling pass. If an interrupt
    // fires during an `await` below, the epoch advances and we bail before
    // playing audio that belongs to the cancelled response.
    const epochAtStart = interruptEpochRef.current;

    while (playbackQueueRef.current.length > 0 && nextPlayTimeRef.current < now + 0.2) {
      const audioData = playbackQueueRef.current.shift()!;
      const sampleRate = storeState.currentSampleRate;

      if (!sampleRate || sampleRate <= 0) {
        // audio_info event not yet received — wait for it before playing audio
        // Put chunk back in queue to retry after audio_info arrives
        playbackQueueRef.current.unshift(audioData);
        return;
      }

      if (epochAtStart !== interruptEpochRef.current) return;
      if ((ctx.state as string) === 'closed') return;

      try {
        // Synchronous Int16 PCM → AudioBuffer (no WAV header, no decodeAudioData).
        const audioBuffer = ctx.createBuffer(1, audioData.length, sampleRate);
        const channel = audioBuffer.getChannelData(0);
        for (let i = 0; i < audioData.length; i++) {
          channel[i] = audioData[i] / 32768;
        }

        const sourceNode = ctx.createBufferSource();
        sourceNode.buffer = audioBuffer;
        sourceNode.connect(ctx.destination);
        // Track the node so interrupt can stop it. Auto-clean on natural end.
        activeSourcesRef.current.push(sourceNode);
        sourceNode.onended = () => {
          const idx = activeSourcesRef.current.indexOf(sourceNode);
          if (idx >= 0) activeSourcesRef.current.splice(idx, 1);
        };
        sourceNode.start(nextPlayTimeRef.current);
        nextPlayTimeRef.current += audioBuffer.duration;
        if (!storeState.isPlaying) {
          dispatch(setIsPlaying(true));
        }
      } catch {
        // AudioBuffer creation failed; skip this chunk
      }
    }
  }, [dispatch]);

  scheduleAudioRef.current = scheduleAudio;

  const startScheduler = useCallback(() => {
    if (!schedulerIntervalRef.current) {
      schedulerIntervalRef.current = window.setInterval(() => {
        scheduleAudioRef.current?.();
      }, 50);
    }
  }, []);

  const stopScheduler = useCallback(() => {
    if (schedulerIntervalRef.current) {
      clearInterval(schedulerIntervalRef.current);
      schedulerIntervalRef.current = null;
    }
  }, []);

  const handleMessage = useCallback((event: MessageEvent) => {
    if (event.data instanceof ArrayBuffer) {
      const audioData = new Int16Array(event.data);

      // Bound playback queue to prevent OOM on slow networks or suspended AudioContext
      if (playbackQueueRef.current.length < MAX_PLAYBACK_QUEUE_ITEMS) {
        playbackQueueRef.current.push(audioData);
        // Reset overflow counter when we have headroom
        if (queueOverflowCountRef.current > 0 && playbackQueueRef.current.length < MAX_PLAYBACK_QUEUE_ITEMS * 0.5) {
          queueOverflowCountRef.current = 0;
        }
      } else {
        // Queue is full; increment overflow counter
        queueOverflowCountRef.current++;
        if (queueOverflowCountRef.current === 1) {
          console.error(`Audio playback queue overflow (${MAX_PLAYBACK_QUEUE_ITEMS} items). Network latency or suspended AudioContext is causing frame drops.`);
        }
      }

      // Only dispatch when transitioning, not on every chunk
      if (statusRef.current !== 'speaking') {
        dispatch(setStatus('speaking'));
      }
      startScheduler();
    } else {
      try {
        const data = JSON.parse(event.data) as ServerMessage;
        const storeState = stateRef.current;

        if (data.type === 'thread') {
          const threadId = data.thread_id;
          dispatch(setCurrentThreadId(threadId));
          dispatch(addThread({
            id: threadId,
            title: 'New conversation',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            messageCount: 1,
          }));

          if (!titleSetForThreads.includes(threadId)) {
            dispatch(markTitleSet(threadId));
          }

          onThreadCreatedRef.current?.(threadId);
        } else if (data.type === 'thread_title') {
          // Backend auto-titles the thread on the user's first transcript
          // (mirrors chat-mode useChat behavior). Update the sidebar copy
          // immediately so the user sees their conversation labelled.
          dispatch(renameThread({ id: data.thread_id, title: data.title }));
        } else if (data.type === 'partial_transcript') {
          const partialId = storeState.currentPartialId || 'partial-live';
          if (!storeState.currentPartialId) {
            dispatch(setCurrentPartialId(partialId));
            dispatch(addMessage({
              id: partialId,
              role: 'user',
              content: data.text,
              timestamp: new Date().toISOString(),
              isStreaming: true,
            }));
          } else {
            dispatch(updateMessage({ id: partialId, updates: { content: data.text } }));
          }
          if (data.is_final) {
            dispatch(updateMessage({ id: partialId, updates: { isStreaming: false, content: data.text } }));
            dispatch(setCurrentPartialId(null));
            dispatch(setStatus('processing'));
          } else {
            dispatch(setStatus('listening'));
          }
        } else if (data.type === 'spoken_text') {
          // Build from spoken sentences (not raw LLM tokens) so displayed
          // text matches exactly what was synthesized after TTS processing.
          if (!storeState.currentAiMessageId) {
            const aiMessageId = generateId();
            dispatch(setCurrentAiMessageId(aiMessageId));
            dispatch(addMessage({
              id: aiMessageId,
              role: 'assistant',
              content: data.text,
              timestamp: new Date().toISOString(),
              isStreaming: true,
            }));
          } else {
            dispatch(appendToMessage({ id: storeState.currentAiMessageId, text: ' ' + data.text }));
          }
        } else if (data.type === 'text_stream') {
          // Voice mode: LLM is done but TTS may still be playing; arm flag for scheduleAudio
          if (data.done) {
            llmDoneRef.current = true;
            if (storeState.currentAiMessageId) {
              dispatch(updateMessage({ id: storeState.currentAiMessageId, updates: { isStreaming: false } }));
            }
          }
        } else if (data.type === 'audio_info') {
          dispatch(setSampleRate(data.sample_rate));
          nextPlayTimeRef.current = outputContextRef.current?.currentTime || 0;
        } else if (data.type === 'vad') {
          if (data.is_speaking && statusRef.current !== 'processing' && statusRef.current !== 'speaking') {
            dispatch(setStatus('listening'));
          }
        } else if (data.type === 'interrupt') {
          // Bump epoch FIRST so any in-flight decodeAudioData promise that
          // resolves after this point sees the new epoch and bails out
          // instead of playing stale audio.
          interruptEpochRef.current += 1;

          // Stop every BufferSource we've scheduled. Closing the context
          // alone doesn't synchronously stop nodes that already had .start()
          // called — they keep playing until the close completes (which is
          // async). Calling .stop(0) on each cuts audio immediately.
          for (const node of activeSourcesRef.current) {
            try { node.stop(0); } catch { /* already ended */ }
            try { node.disconnect(); } catch { /* already disconnected */ }
          }
          activeSourcesRef.current = [];

          // Drop any queued chunks that haven't started decoding yet.
          playbackQueueRef.current = [];
          queueOverflowCountRef.current = 0;

          // Restarts when the next binary audio frame arrives.
          stopScheduler();

          // Do NOT recreate the AudioContext — sources already stopped,
          // synchronous playback has no in-flight async work to cancel.
          nextPlayTimeRef.current = 0;
          // Reset llmDoneRef so the NEXT response's drain logic doesn't
          // immediately tear down playback because of stale state.
          llmDoneRef.current = false;
          dispatch(setIsPlaying(false));
          dispatch(setStatus('listening'));

          if (storeState.currentAiMessageId) {
            const current = storeState.messages.find(
              (m) => m.id === storeState.currentAiMessageId,
            );
            dispatch(updateMessage({
              id: storeState.currentAiMessageId,
              updates: {
                isStreaming: false,
                content: (current?.content ?? '') + ' [interrupted]',
              },
            }));
            dispatch(setCurrentAiMessageId(null));
          }
        }
      } catch {
        // Non-JSON text message received; ignore
      }
    }
  }, [
    startScheduler,
    stopScheduler,
    dispatch,
    titleSetForThreads,
  ]);

  const scheduleReconnect = useCallback(() => {
    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    // Don't reconnect if already at max attempts
    if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      console.error(`[VoiceAgent] Max reconnection attempts (${MAX_RECONNECT_ATTEMPTS}) reached. Giving up.`);
      onError?.(new Error('WebSocket connection lost and max retries exceeded'));
      return;
    }

    // Calculate exponential backoff delay
    const delayMs = Math.min(
      BASE_RECONNECT_DELAY_MS * Math.pow(2, reconnectAttemptsRef.current),
      MAX_RECONNECT_DELAY_MS
    );

    reconnectAttemptsRef.current += 1;
    console.info(`[VoiceAgent] Scheduling reconnect attempt ${reconnectAttemptsRef.current} in ${delayMs}ms...`);

    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectTimeoutRef.current = null;
      // Always call the CURRENT connect via ref. If the attempt fails
      // (backend still booting, mic permission revoked, etc.), schedule
      // another attempt instead of letting the unhandled rejection kill
      // the reconnect chain.
      const currentConnect = connectRef.current;
      if (!currentConnect) return;
      Promise.resolve(currentConnect()).catch((err) => {
        console.warn('[VoiceAgent] Reconnect attempt failed:', err?.message ?? err);
        scheduleReconnect();
      });
    }, delayMs);
  }, [onError]);

  const connect = useCallback(async () => {
    // Prevent double-connect (guards against React Strict Mode)
    if (isConnectingRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) return;

    isConnectingRef.current = true;

    // Detach handlers before close — old onclose firing after the new
    // onopen would overwrite status='listening' back to 'idle'.
    const oldWs = wsRef.current;
    if (oldWs) {
      oldWs.onopen = null;
      oldWs.onmessage = null;
      oldWs.onerror = null;
      oldWs.onclose = null;
      try { oldWs.close(); } catch { /* ignore */ }
    }
    wsRef.current = null;
    try {
      mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    } catch { /* ignore */ }
    mediaStreamRef.current = null;
    try { sourceRef.current?.disconnect(); } catch { /* ignore */ }
    sourceRef.current = null;
    try { workletNodeRef.current?.disconnect(); } catch { /* ignore */ }
    workletNodeRef.current = null;
    try { inputContextRef.current?.close(); } catch { /* ignore */ }
    inputContextRef.current = null;
    try { outputContextRef.current?.close(); } catch { /* ignore */ }
    outputContextRef.current = null;

    try {
      // Reset audio session state for this connection instance
      isFirstChunkOfSessionRef.current = true;

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
      mediaStreamRef.current = stream;

      inputContextRef.current = new AudioContext();
      outputContextRef.current = new AudioContext();


      const blob = new Blob([audioProcessorCode], { type: 'application/javascript' });
      const url = URL.createObjectURL(blob);
      try {
        await inputContextRef.current.audioWorklet.addModule(url);
      } finally {
        URL.revokeObjectURL(url);
      }

      if (mediaStreamRef.current) {
        sourceRef.current = inputContextRef.current!.createMediaStreamSource(mediaStreamRef.current);
        workletNodeRef.current = new AudioWorkletNode(
          inputContextRef.current!,
          'audio-capture-processor'
        );
      }

      wsRef.current = new WebSocket(wsUrl);
      wsRef.current.binaryType = 'arraybuffer';

      wsRef.current.onopen = () => {
        console.info('[VoiceAgent] WebSocket open → status=listening');
        isConnectingRef.current = false;
        reconnectAttemptsRef.current = 0;  // Reset reconnect counter on success
        dispatch(setIsConnected(true));
        dispatch(setStatus('listening'));

        const sendConfig = (config: VoiceConfigMessage) => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(config));
          }
        };

        sendConfig(voiceConfig.getCurrentConfig());
        voiceConfig.setBroadcaster(sendConfig);

        if (sourceRef.current && workletNodeRef.current) {
          sourceRef.current.connect(workletNodeRef.current);

          workletNodeRef.current.port.onmessage = async (e) => {
            try {
              // Check WebSocket state at send time to handle race conditions
              if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
                return;
              }

              // Pause-mute: when the user has hit "pause", we keep the
              // WebSocket and AudioContext alive (no expensive teardown),
              // but skip sending mic frames upstream. Server VAD therefore
              // never fires and the agent stops listening. Resuming is
              // instant — just flip the ref back.
              if (isMutedRef.current) {
                // Also zero the audio-level UI gauge so it doesn't show
                // stale activity from before the mute.
                dispatch(setAudioLevel(0));
                return;
              }

              const float32Data = new Float32Array(e.data);
              const int16Data = await resampleAudio(
                float32Data,
                inputContextRef.current?.sampleRate || 48000,
                TARGET_SAMPLE_RATE,
                isFirstChunkOfSessionRef
              );

              try {
                wsRef.current.send(int16Data.buffer as ArrayBuffer);
              } catch {
                // WebSocket may be closing; ignore and let reconnect handle it
                return;
              }

              let sum = 0;
              for (let i = 0; i < int16Data.length; i++) {
                sum += Math.abs(int16Data[i]);
              }
              const level = Math.min(1, (sum / int16Data.length) / 10000);
              dispatch(setAudioLevel(level));
            } catch {
              // Resampling failed; skip this audio chunk
            }
          };
        }
      };

      wsRef.current.onmessage = handleMessage;

      wsRef.current.onerror = (e) => {
        console.warn('[VoiceAgent] WebSocket error', e);
        isConnectingRef.current = false;
        dispatch(setStatus('idle'));
        scheduleReconnect();
      };

      wsRef.current.onclose = (e) => {
        console.info(`[VoiceAgent] WebSocket close (code=${e.code}, reason=${e.reason || 'n/a'}) → reconnect`);
        isConnectingRef.current = false;
        dispatch(setIsConnected(false));
        dispatch(setStatus('idle'));
        scheduleReconnect();
      };

    } catch (error) {
      isConnectingRef.current = false;
      // Clean up any partially initialized resources
      mediaStreamRef.current?.getTracks().forEach(t => t.stop());
      mediaStreamRef.current = null;
      sourceRef.current?.disconnect();
      sourceRef.current = null;
      workletNodeRef.current?.disconnect();
      workletNodeRef.current = null;
      inputContextRef.current?.close();
      inputContextRef.current = null;
      outputContextRef.current?.close();
      outputContextRef.current = null;
      wsRef.current?.close();
      wsRef.current = null;

      onError?.(error as Error);
      // Don't rethrow — scheduleReconnect's promise chain catches and
      // re-schedules. Throwing here would also work but only because we
      // .catch() at the call site; keep the API non-throwing for clarity.
      throw error;
    }
  }, [wsUrl, handleMessage, onError, scheduleReconnect, dispatch, voiceConfig]);

  // Keep refs in sync so setTimeout / useEffect cleanup always invoke the
  // CURRENT connect/disconnect, not a stale closure.
  connectRef.current = connect;

  const disconnect = useCallback(() => {
    isConnectingRef.current = false;

    // Clear any pending reconnect attempts
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttemptsRef.current = 0;

    stopScheduler();
    voiceConfig.setBroadcaster(null);

    // CRITICAL: detach the WS handlers BEFORE closing. Otherwise the
    // old socket's onclose fires asynchronously after disconnect()
    // returns — and that handler calls scheduleReconnect(), which
    // 1 second later spawns a NEW connection (and a NEW agent thread)
    // even though the component has unmounted. This was the cause of
    // phantom threads being created when the user navigated away from
    // /converse or React Strict Mode double-invoked the effect.
    const oldWs = wsRef.current;
    if (oldWs) {
      oldWs.onopen = null;
      oldWs.onmessage = null;
      oldWs.onerror = null;
      oldWs.onclose = null;
      try { oldWs.close(); } catch { /* already closed */ }
    }
    wsRef.current = null;

    workletNodeRef.current?.disconnect();
    workletNodeRef.current = null;

    sourceRef.current?.disconnect();
    sourceRef.current = null;

    inputContextRef.current?.close();
    inputContextRef.current = null;

    outputContextRef.current?.close();
    outputContextRef.current = null;

    mediaStreamRef.current?.getTracks().forEach(t => t.stop());
    mediaStreamRef.current = null;

    playbackQueueRef.current = [];
    nextPlayTimeRef.current = 0;

    dispatch(reset());
  }, [stopScheduler, voiceConfig, dispatch]);

  // Pin disconnect to a ref so the unmount effect below doesn't fire on
  // every voiceConfig change (which would silently cancel pending reconnects).
  disconnectRef.current = disconnect;

  useEffect(() => {
    // Empty deps → cleanup runs ONLY on actual unmount. Calls the latest
    // disconnect via ref, not a stale captured one.
    return () => {
      disconnectRef.current?.();
    };
  }, []);

  // Pause stops the MediaStreamTrack so the OS mic indicator turns off;
  // resume reacquires via getUserMedia and rewires the worklet.
  const togglePause = useCallback(async () => {
    const wasPaused = isMutedRef.current;

    if (!wasPaused) {
      try { sourceRef.current?.disconnect(); } catch { /* ignore */ }
      sourceRef.current = null;
      mediaStreamRef.current?.getAudioTracks().forEach((t) => {
        try { t.stop(); } catch { /* ignore */ }
      });
      mediaStreamRef.current = null;
      dispatch(setAudioLevel(0));
      dispatch(setIsMuted(true));
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
      mediaStreamRef.current = stream;

      if (inputContextRef.current && workletNodeRef.current) {
        if (inputContextRef.current.state === 'suspended') {
          try { await inputContextRef.current.resume(); } catch { /* ignore */ }
        }
        const source = inputContextRef.current.createMediaStreamSource(stream);
        sourceRef.current = source;
        source.connect(workletNodeRef.current);
      }
      isFirstChunkOfSessionRef.current = true;
      dispatch(setIsMuted(false));
    } catch (e) {
      console.error('[VoiceAgent] Failed to reacquire mic on resume:', e);
    }
  }, [dispatch]);

  return {
    status,
    messages,
    isConnected,
    audioLevel,
    connect,
    disconnect,
    isMuted,
    togglePause,
  };
}
