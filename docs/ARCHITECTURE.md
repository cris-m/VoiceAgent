# Architecture

How VoiceAgent moves bytes from a microphone to an LLM and back to a speaker.

## Top-level layout

Three Python services, one React app, nginx, two databases.

```
nginx :8080  ──┬──  client :3000   (Vite dev server with HMR)
               ├──  backend :8000  (FastAPI: voice WS, narrate, transcribe, music, auth)
               └──  agent :8000    (LangGraph deploy: reasoning, tools, skills)

backend ──── postgres :5432   (users, file metadata)
agent ────── postgres :5432   (LangGraph checkpoints, threads, store)
backend ──── redis :6379      (token blacklist, rate-limit counters)
```

The two Python services have separate process boundaries. The backend talks to the agent over the LangGraph SDK (HTTP). The agent never talks to the backend directly. All user-facing routes are the backend's responsibility.

## The voice pipeline

`backend/services/voice_pipeline.py` owns the lifecycle of three components:

```python
class VoicePipeline:
    self._stt: BaseSTT       # Whisper
    self._tts: BaseTTS       # Pocket TTS or Kokoro
    self._vad: SileroVAD     # speech / silence detector (end-of-turn arm)
    self._aec: EchoCanceller # boolean flag for "is TTS playing"
```

The voice WebSocket route also instantiates a per-connection `WebRTCVAD` as a fast-trigger arm for barge-in (`backend/services/vad/webrtc.py`). Silero is used for end-of-turn detection; WebRTC GMM is used to detect when the user has started speaking during AI playback.

There are two entry points:

- `get_voice_pipeline()` returns a process-wide singleton holding the loaded models. It is created at app startup; warmup runs in the background so HTTP routes serve immediately.
- `create_voice_pipeline_for_connection()` returns a per-WebSocket pipeline. It reuses the singleton's STT and TTS (both stateless after model load) but creates a fresh VAD because VAD state is per-conversation and would leak between concurrent users if shared.

## VAD (Silero)

`backend/services/vad/silero.py`

VAD is "voice activity detection". It tells the system when a user is speaking and when they have stopped, which removes the need for push-to-talk.

The implementation uses Silero VAD, a 1.5 MB neural network that takes 32 ms audio chunks and returns a probability (0.0 to 1.0) that the chunk contains speech. It is cheap (about 5 ms inference per chunk on CPU) and is distributed via PyPI as `silero-vad`.

### State machine

```
SILENCE → SPEECH_START → SPEAKING → SPEECH_END → SILENCE
```

Transitions use Schmitt-trigger hysteresis. A single threshold flickers on noisy audio.

| Threshold | Default | Crossed when |
|---|---|---|
| `speech_threshold` | 0.5 | "is this speech?" Going from silence into speech. |
| `silence_threshold` | 0.35 | "is this silence?" Going from speech back to silence. |
| `min_speech_duration_ms` | 100 | Brief noise spikes do not count as speech. |
| `min_silence_duration_ms` | 300 | A pause shorter than this is treated as continued speech. |

Between state changes, audio accumulates in `_audio_buffer`. When `SPEECH_END` fires, the whole buffer is shipped to STT in one batch (Whisper is non-streaming and needs the full utterance).

A 300 ms pre-roll buffer captures audio during `SILENCE` so the leading consonant is not chopped off when speech starts.

### Probability smoothing

Raw VAD scores are noisy frame to frame. Scores are averaged over the last 5 frames before thresholds are applied. The client sends 100 ms audio chunks, so the smoothing window is roughly 500 ms in practice. That is fine for end-of-turn detection (where false positives produce bad transcripts) but too slow for barge-in, which is why barge-in uses the separate WebRTC fast-trigger arm.

### Per-connection requirement

Silero's underlying LSTM has internal state. Sharing one VAD instance between users would cross-talk their audio. That is why `voice_pipeline.create_voice_pipeline_for_connection()` instantiates a fresh `SileroVAD` per WebSocket.

## WebRTC fast-trigger VAD (barge-in arm)

`backend/services/vad/webrtc.py`

A second VAD, instantiated per WebSocket, runs alongside Silero. It wraps the standard WebRTC GMM detector (`webrtcvad`) and produces a speech/non-speech verdict per 20 ms frame in microseconds. No neural network, no smoothing buffer, no warmup. The verdict is used only for barge-in detection.

### Why two VADs?

Silero's strength is precision: a low false-positive rate on end-of-turn. The price is the ~500 ms smoothing window described above. For barge-in, that window translates to a 600 to 800 ms delay between the user starting to speak and the AI being interrupted, which is well over the 200 to 300 ms threshold for a turn to feel natural.

WebRTC's GMM has the opposite tradeoff: high recall, modest precision, near-zero latency. For barge-in this is the right tradeoff because the user has *explicitly* started speaking and the cost of an occasional false interrupt (the AI stops, the user repeats) is much lower than the cost of an unresponsive agent.

### Barge-in flow

1. WebRTC reports speech in any 20 ms sub-frame of the incoming 100 ms client chunk.
2. The route stamps a barge-in candidate the first time this happens during AI playback.
3. The continuous-speech run is tracked in 20 ms increments. When it reaches `BARGE_IN_HOLD_MS` (150 ms), the route fires the interrupt.
4. If WebRTC drops speech and the candidate has been outstanding for `CANDIDATE_TIMEOUT_MS` (300 ms) without re-arming, the candidate is discarded (treated as a backchannel like a cough or "uh-huh").

End-to-end barge-in latency is roughly 150 to 200 ms versus the ~600 to 800 ms of the Silero-only path. The article ["Voice Agent Barge-In: VAD Tuning 2026"](https://www.syncsoft.ai/en/blog/voice-agent-barge-in-vad-tuning-2026) describes the same dual-pass pattern.

## AEC (echo state)

`backend/services/audio/aec.py`

The name is misleading. This module is not an acoustic echo canceller in the DSP sense. It is a single boolean: `_is_playing`. Set to `True` while TTS is sending chunks, set back to `False` once playback drains.

The browser's `getUserMedia({ echoCancellation: true })` does the actual echo cancellation in real time. The server flag exists only so callers can ask "should I treat this incoming chunk as potential bleed?". It is not used for anything load-bearing today. The barge-in detector specifically does NOT gate on `is_echo`, because doing so would make interrupting the AI impossible (the AI is always playing during a barge-in).

The flag has a deferred cleanup. When TTS finishes streaming on the server, the system waits `playback_duration + 150 ms` before flipping the flag to false, so VAD does not briefly think bleed is the user starting to speak.

## STT (Whisper)

`backend/services/stt/whisper.py` wraps `faster-whisper` (CTranslate2 backend).

The pipeline deliberately uses non-streaming Whisper:

- VAD already tells the system when the user finished talking.
- Whisper's native streaming mode adds significant latency overhead on short utterances.
- `distil-large-v3` int8 transcribes a 2-second clip in about 600 ms on a single CPU core.

Decoding parameters are tuned for short conversational turns:

- `beam_size=1`, `best_of=1` (greedy). Roughly 5x faster than the default beam search with negligible quality loss on short text.
- `word_timestamps=False`. Adding timestamps doubles inference time.
- `condition_on_previous_text=False`. No cross-turn priming; every utterance is independent.
- Hallucination guards: `repetition_penalty=1.05`, `no_repeat_ngram_size=4`, `compression_ratio_threshold=2.4`.

Warmup: at app startup the system transcribes one second of silence to JIT-compile the kernels, so the user's first real turn has the same latency as subsequent ones.

## TTS (Pocket TTS or Kokoro)

Two TTS providers are supported, selected by `TTS_PROVIDER` in `backend/.env`.

|  | Kokoro | Pocket TTS |
|---|---|---|
| Repo | `kokoro-onnx` | `pocket-tts` (Kyutai) |
| Size | 82M params, ONNX | 100M params |
| First-byte latency | about 300 ms | about 200 ms |
| Voices | 8 curated (US/UK English) | 27 curated (EN, FR, DE, ES, IT, PT) |
| Voice cloning | no | yes, via 1+ minute reference audio |
| Speed adjustment | yes | no (model cannot change rate) |
| Per-call language | yes | no (set at model-load time) |
| Streaming | pseudo (synthesize all, yield 100 ms chunks) | native token-level streaming |

Voice-cloning weights are gated on HuggingFace. To enable Pocket TTS cloning:

```bash
# 1. Generate a token at https://huggingface.co/settings/tokens
# 2. Accept the model terms at https://huggingface.co/kyutai/pocket-tts
# 3. Add to backend/.env:
HF_TOKEN=hf_xxx
```

The `/voice/voices` endpoint reports the active provider's capabilities (`supports_cloning`, `supports_speed`, `supports_language`) so the UI can hide controls the underlying model cannot honor.

## The voice route

`backend/api/routes/v1/voice.py` is the WebSocket handler at `/api/v1/voice/ws`.

Each connection runs four asyncio tasks concurrently:

```
audio_receiver → transcript_collector → response_orchestrator → tts_streamer
        │                  │                     │                    │
        ▼                  ▼                     ▼                    ▼
   reads PCM         reads STT events     calls agent.stream     reads sentence
   feeds STT          + auto-titles       + splits sentences     queue, calls TTS,
   runs VAD           thread              + queues to TTS        sends audio bytes
```

Queues decouple stages. The LLM does not wait for TTS, TTS does not wait for the LLM to finish, and STT runs during user speech rather than after.

### audio_receiver

- Reads binary frames (Int16Array PCM at 16 kHz) and JSON config messages from the WebSocket.
- Forwards PCM to the streaming STT session.
- Runs local VAD on every chunk and emits `vad` state-change events to the client for the orb UI.
- Watches for barge-in (see below).

### transcript_collector

- Consumes events from the STT session.
- Implements semantic turn detection. If the transcript ends in a hanging word ("what time is the…"), the text is held for `SEMANTIC_GRACE_MS` (700 ms) before being dispatched, in case more speech arrives.
- On the very first user transcript of the conversation, sets the LangGraph thread's `metadata.name` so the sidebar gets a real title instead of "New conversation".

### response_orchestrator

- Pulls finalized transcripts and calls `agent.stream_events(thread_id, text, mode="voice", voice_name=..., voice_description=...)`.
- Schedules a filler-phrase task. If the LLM has not produced a token in 1.2 s, a short "Hmm." or "Let me think." is queued into the TTS queue so the user hears something while the LLM warms up.
- As tokens arrive, it splits them into complete sentences (with a comma-break shortcut for the very first sentence to start TTS sooner) and pushes them to the TTS queue.
- Tracks `is_responding_ref` so barge-in detection knows whether AI output is in flight.

### tts_streamer

- Pulls sentences off the queue and calls `pipeline.synthesize_stream(text, voice=..., speed=..., lang=...)`.
- Sends audio chunks back to the client over the WebSocket as binary frames, plus a `spoken_text` JSON event so the chat UI can show what was actually spoken.
- On end-of-response sentinel, clears the barge-in candidate and flips `is_responding_ref` to False.

## Barge-in

When the user starts talking while the AI is still talking, the AI should stop immediately. This is harder than it looks:

1. The browser's mic is picking up the AI's own audio (echo). That has to be distinguished from real user speech.
2. Short bursts ("uh-huh", coughs, throat-clears) should not fire. Only sustained speech should.
3. The AI's audio is queued ahead in the browser. Cancelling on the server alone is not enough.

### Server-side gate

```python
ai_audible = is_responding_ref["value"] or pipeline.is_ai_speaking()
```

`ai_audible` is True when EITHER the response orchestrator is running OR the deferred AEC cleanup is still active (TTS just finished but the browser has not drained playback). Both have to be False for the next user turn to be processed normally.

### Two-phase confirmation

1. **Phase 1.** When `ai_audible` is True and WebRTC reports speech in any sub-frame of the incoming chunk, stamp a candidate timestamp.
2. **Phase 2.** Track continuous WebRTC speech in 20 ms increments. When the continuous run reaches `BARGE_IN_HOLD_MS` (150 ms), `interrupt_event.set()`. If WebRTC drops speech and the candidate is older than `CANDIDATE_TIMEOUT_MS` (300 ms) with no fresh continuous-speech evidence, the candidate is discarded; it was a backchannel.

150 ms is the article's recommended threshold for natural-feeling barge-in. The Silero state machine continues to run in parallel for end-of-turn detection but is not consulted by the barge-in path, so its smoothing window does not add latency here.

### Why the system does NOT gate on `is_echo`

The `EchoCanceller._is_playing` flag is True throughout the entire TTS playback window. Gating on `not is_echo` would make barge-in physically impossible during AI speech. Browser AEC handles speaker bleed; the 200 ms hold combined with Silero's 0.5/0.35 hysteresis filters anything that gets through.

### Client side

When the server sends `{type: "interrupt"}`:

1. Bump an interrupt-epoch counter.
2. Iterate every active `AudioBufferSourceNode` and call `.stop(0)`. Closing the AudioContext alone does not synchronously stop nodes that were already started.
3. Clear the playback queue.
4. Recreate the AudioContext to cancel any in-flight `decodeAudioData` Promises.
5. Reset `llmDoneRef`, `nextPlayTimeRef`, and related timers.

## Latency budget

For natural-feeling conversation, the round trip from "user stops talking" to "user hears first word" should be under 800 ms. The typical end-to-end on this stack:

```
user stops talking
        │  ~300 ms       VAD silence-detection threshold (configurable)
        │
  end-of-turn fires
        │  ~600-1000 ms  Whisper distil-large-v3 transcribe (depends on length)
        │
  text → agent.stream_events
        │  ~600-1500 ms  LLM time-to-first-token (depends on model and prompt size)
        │
  first LLM token
        │  ~50-200 ms    sentence-boundary buffer (waiting for "." or "!" or first comma)
        │
  first sentence → TTS queue
        │  ~200-300 ms   Pocket TTS first-byte
        │
  user hears first word
```

Total: typically 2 to 3 seconds. Filler phrases bridge the dead air for slow LLM TTFTs.

What got it down to that range:

- Greedy Whisper saves about 500 ms versus beam=5.
- VAD silence reduced from 500 ms (LiveKit default) to 300 ms (Vapi default).
- First-sentence comma break saves about 200 ms on first audio byte.
- Filler phrases when LLM TTFT exceeds 1.2 s. Perceptual win.
- Whisper and TTS warmup at startup. Kills first-turn cold start.
- Voice prompt heavily slimmed. The previous "read /memories at conversation start" mandate cost 2 to 5 s on the first turn.

## Agent integration

`backend/services/agent/client.py` wraps `langgraph_sdk` and exposes:

- `create_thread(metadata?)` opens a new thread and returns its id.
- `stream_events(thread_id, text, mode, voice_name, voice_description, user_id)` sends a user message and yields normalized events: `{type: 'token' | 'message' | 'error' | 'done'}`.
- `update_thread_metadata(thread_id, metadata)` sets the auto-title.
- `delete_thread(thread_id)`.

The `mode` (`voice` or `chat`) is passed through `context` to LangGraph, where `assistant/graph.py::select_prompt` swaps between `VOICE_SYSTEM_PROMPT` (terse, no markdown, conversational) and `CHAT_SYSTEM_PROMPT` (full, structured). `voice_name` and `voice_description` are interpolated into the voice prompt so the LLM stays in character.

The agent itself uses **deepagents** (Anthropic's framework) layered on LangGraph:

- `create_deep_agent(model, tools, middleware, store, ...)` builds the graph.
- Middleware stack: `select_prompt` → `TokenCountMiddleware` → `ToolCallLimitMiddleware` → retry middleware (×2) → `ContextEditingMiddleware` → `HumanInTheLoopMiddleware(interrupt_on={memory_*})` → `SkillsMiddleware`.
- Tools live under `agent/assistant/tools/` (web, news, weather, finance, memory).
- Skills live under `agent/assistant/skills/` and are loaded by `SkillsMiddleware`.

## WebSocket protocol reference

Endpoint: `ws://<host>/api/v1/voice/ws`

### Client to server

| Type | Body | Notes |
|---|---|---|
| binary | `Int16Array` | 16 kHz mono PCM. The browser captures at 48 kHz and resamples client-side. |
| `config` | `{voice_id, personality_id, speed, language}` | Sent on connect and on each change. `speed` and `language` are honored only if the active TTS provider supports them. |
| `text_input` | `{text}` | Skips STT and sends text directly to the agent. Useful for a "type instead" affordance in voice mode. |

### Server to client

| Type | Body | Fired when |
|---|---|---|
| `thread` | `{thread_id}` | Once, immediately after the WebSocket opens. |
| `thread_title` | `{thread_id, title}` | After the first user transcript, when the backend sets `metadata.name`. |
| `vad` | `{state, probability, is_speaking, is_echo, aec_state, is_responding}` | On VAD state changes (rate-limited to actual transitions). |
| `partial_transcript` | `{text, is_final}` | Live transcript updates. `is_final=true` means end-of-turn was confirmed. |
| `text_stream` | `{text, done}` | LLM token stream for the in-progress AI message bubble. |
| `spoken_text` | `{text}` | Sentence-by-sentence record of what TTS will speak (post-sanitization, post-markdown-strip). Drives the chat-message text. |
| `audio_info` | `{sample_rate}` | Once per response. The sample rate the upcoming PCM frames will use. |
| binary | `Int16Array` | TTS audio chunk. Same wire format as the client-to-server PCM. |
| `interrupt` | `{}` | Server confirmed barge-in. Client should drop its playback queue. |
| `error` | `{message}` | Pipeline error. The connection may still be alive. |

### Connection lifecycle

```
client opens WS
  └─→ server accepts
       └─→ server creates LangGraph thread
            └─→ server sends {type: "thread", thread_id}

client sends config + binary frames
  └─→ server runs VAD + STT
       └─→ on end-of-turn: server sends {type: "partial_transcript", is_final: true}
            └─→ server calls agent.stream_events
                 └─→ server sends {type: "text_stream", ...} as tokens arrive
                      └─→ on each complete sentence: server synthesizes
                           └─→ server sends {type: "audio_info"} once
                                └─→ server sends binary audio frames
                                     └─→ server sends {type: "spoken_text", ...}
```

If the user starts talking again mid-response, the server fires `{type: "interrupt"}` and resets to listening. Authentication is currently skipped when `API_KEY` is unset (development); when set, the client must include `?token=<key>` in the WebSocket URL.
