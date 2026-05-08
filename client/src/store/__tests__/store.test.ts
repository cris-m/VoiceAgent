/**
 * Tests for the voiceAgent Redux slice (store.ts).
 *
 * Covers:
 *  - Initial state shape and invariants
 *  - Every exported action creator / reducer case
 *  - The currentSampleRate "must be set before playback" invariant
 *  - Derived behaviour: appendToMessage, reset, markTitleSet deduplication
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { store, reset } from '@store';
import {
  setStatus,
  setIsConnected,
  setAudioLevel,
  setIsPlaying,
  setIsMuted,
  setSampleRate,
  addMessage,
  updateMessage,
  appendToMessage,
  setMessages,
  setCurrentAiMessageId,
  setCurrentPartialId,
  setCurrentThreadId,
  addThread,
  renameThread,
  markTitleSet,
} from '@store';
import type { RootState } from '@store';
import type { Message } from '@typing';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getVoiceState() {
  return (store.getState() as RootState).voiceAgent;
}

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: `msg-${Math.random().toString(36).substring(2, 7)}`,
    role: 'user',
    content: 'Hello',
    timestamp: new Date().toISOString(),
    isStreaming: false,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Reset between tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  store.dispatch(reset());
});

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

describe('voiceAgent slice – initial state', () => {
  it('status is idle', () => {
    expect(getVoiceState().status).toBe('idle');
  });

  it('isConnected is false', () => {
    expect(getVoiceState().isConnected).toBe(false);
  });

  it('audioLevel is 0', () => {
    expect(getVoiceState().audioLevel).toBe(0);
  });

  it('isMuted is false', () => {
    expect(getVoiceState().isMuted).toBe(false);
  });

  it('isPlaying is false', () => {
    expect(getVoiceState().isPlaying).toBe(false);
  });

  it('currentSampleRate is 0 (not yet received from server)', () => {
    // INVARIANT: 0 signals "audio_info not yet received" → playback must not start
    expect(getVoiceState().currentSampleRate).toBe(0);
  });

  it('messages is empty', () => {
    expect(getVoiceState().messages).toHaveLength(0);
  });

  it('currentThreadId is null', () => {
    expect(getVoiceState().currentThreadId).toBeNull();
  });

  it('currentAiMessageId is null', () => {
    expect(getVoiceState().currentAiMessageId).toBeNull();
  });

  it('currentPartialId is null', () => {
    expect(getVoiceState().currentPartialId).toBeNull();
  });

  it('threads is empty', () => {
    expect(getVoiceState().threads).toHaveLength(0);
  });

  it('titleSetForThreads is empty', () => {
    expect(getVoiceState().titleSetForThreads).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// setStatus
// ---------------------------------------------------------------------------

describe('voiceAgent slice – setStatus', () => {
  it('transitions to listening', () => {
    store.dispatch(setStatus('listening'));
    expect(getVoiceState().status).toBe('listening');
  });

  it('transitions to processing', () => {
    store.dispatch(setStatus('processing'));
    expect(getVoiceState().status).toBe('processing');
  });

  it('transitions to speaking', () => {
    store.dispatch(setStatus('speaking'));
    expect(getVoiceState().status).toBe('speaking');
  });

  it('transitions back to idle', () => {
    store.dispatch(setStatus('listening'));
    store.dispatch(setStatus('idle'));
    expect(getVoiceState().status).toBe('idle');
  });
});

// ---------------------------------------------------------------------------
// setIsConnected
// ---------------------------------------------------------------------------

describe('voiceAgent slice – setIsConnected', () => {
  it('sets isConnected to true', () => {
    store.dispatch(setIsConnected(true));
    expect(getVoiceState().isConnected).toBe(true);
  });

  it('sets isConnected back to false', () => {
    store.dispatch(setIsConnected(true));
    store.dispatch(setIsConnected(false));
    expect(getVoiceState().isConnected).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// setAudioLevel
// ---------------------------------------------------------------------------

describe('voiceAgent slice – setAudioLevel', () => {
  it('stores the audio level', () => {
    store.dispatch(setAudioLevel(0.75));
    expect(getVoiceState().audioLevel).toBe(0.75);
  });

  it('stores 0 (muted)', () => {
    store.dispatch(setAudioLevel(0.5));
    store.dispatch(setAudioLevel(0));
    expect(getVoiceState().audioLevel).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// setIsPlaying / setIsMuted
// ---------------------------------------------------------------------------

describe('voiceAgent slice – setIsPlaying and setIsMuted', () => {
  it('setIsPlaying true', () => {
    store.dispatch(setIsPlaying(true));
    expect(getVoiceState().isPlaying).toBe(true);
  });

  it('setIsPlaying false', () => {
    store.dispatch(setIsPlaying(true));
    store.dispatch(setIsPlaying(false));
    expect(getVoiceState().isPlaying).toBe(false);
  });

  it('setIsMuted true', () => {
    store.dispatch(setIsMuted(true));
    expect(getVoiceState().isMuted).toBe(true);
  });

  it('setIsMuted false', () => {
    store.dispatch(setIsMuted(true));
    store.dispatch(setIsMuted(false));
    expect(getVoiceState().isMuted).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// setSampleRate — "must be set before playback" invariant
// ---------------------------------------------------------------------------

describe('voiceAgent slice – setSampleRate', () => {
  it('sets currentSampleRate to the received value', () => {
    store.dispatch(setSampleRate(22050));
    expect(getVoiceState().currentSampleRate).toBe(22050);
  });

  it('INVARIANT: currentSampleRate starts at 0 (block audio until audio_info arrives)', () => {
    // This test documents the invariant used by scheduleAudio in useVoiceAgent:
    //   if (!sampleRate || sampleRate <= 0) → put chunk back, wait for audio_info
    const initial = getVoiceState().currentSampleRate;
    expect(initial).toBe(0);
    expect(initial <= 0).toBe(true);
  });

  it('can update sample rate multiple times (server config change)', () => {
    store.dispatch(setSampleRate(16000));
    store.dispatch(setSampleRate(44100));
    expect(getVoiceState().currentSampleRate).toBe(44100);
  });
});

// ---------------------------------------------------------------------------
// addMessage / updateMessage / appendToMessage
// ---------------------------------------------------------------------------

describe('voiceAgent slice – addMessage', () => {
  it('appends a message to the messages array', () => {
    const msg = makeMessage({ role: 'user', content: 'Hi' });
    store.dispatch(addMessage(msg));
    expect(getVoiceState().messages).toHaveLength(1);
    expect(getVoiceState().messages[0]?.id).toBe(msg.id);
  });

  it('preserves insertion order', () => {
    const m1 = makeMessage({ id: 'a', content: 'First' });
    const m2 = makeMessage({ id: 'b', content: 'Second' });
    store.dispatch(addMessage(m1));
    store.dispatch(addMessage(m2));
    const msgs = getVoiceState().messages;
    expect(msgs[0]?.id).toBe('a');
    expect(msgs[1]?.id).toBe('b');
  });
});

describe('voiceAgent slice – updateMessage', () => {
  it('updates content of an existing message', () => {
    const msg = makeMessage({ id: 'u1', content: 'Original' });
    store.dispatch(addMessage(msg));
    store.dispatch(updateMessage({ id: 'u1', updates: { content: 'Updated' } }));
    expect(getVoiceState().messages[0]?.content).toBe('Updated');
  });

  it('updates isStreaming flag', () => {
    const msg = makeMessage({ id: 'u2', isStreaming: true });
    store.dispatch(addMessage(msg));
    store.dispatch(updateMessage({ id: 'u2', updates: { isStreaming: false } }));
    expect(getVoiceState().messages[0]?.isStreaming).toBe(false);
  });

  it('is a no-op when id does not exist', () => {
    const msg = makeMessage({ id: 'u3' });
    store.dispatch(addMessage(msg));
    store.dispatch(updateMessage({ id: 'nonexistent', updates: { content: 'Oops' } }));
    expect(getVoiceState().messages[0]?.content).toBe('Hello');
  });
});

describe('voiceAgent slice – appendToMessage', () => {
  it('concatenates text onto existing message content', () => {
    const msg = makeMessage({ id: 'a1', content: 'Hello' });
    store.dispatch(addMessage(msg));
    store.dispatch(appendToMessage({ id: 'a1', text: ' world' }));
    expect(getVoiceState().messages[0]?.content).toBe('Hello world');
  });

  it('multiple appends accumulate in order', () => {
    const msg = makeMessage({ id: 'a2', content: 'A' });
    store.dispatch(addMessage(msg));
    store.dispatch(appendToMessage({ id: 'a2', text: 'B' }));
    store.dispatch(appendToMessage({ id: 'a2', text: 'C' }));
    expect(getVoiceState().messages[0]?.content).toBe('ABC');
  });

  it('is a no-op when id does not exist', () => {
    const msg = makeMessage({ id: 'a3', content: 'Unchanged' });
    store.dispatch(addMessage(msg));
    store.dispatch(appendToMessage({ id: 'wrong-id', text: 'extra' }));
    expect(getVoiceState().messages[0]?.content).toBe('Unchanged');
  });
});

// ---------------------------------------------------------------------------
// setMessages
// ---------------------------------------------------------------------------

describe('voiceAgent slice – setMessages', () => {
  it('replaces the messages array', () => {
    store.dispatch(addMessage(makeMessage({ id: 'old' })));
    const newMsgs = [makeMessage({ id: 'new1' }), makeMessage({ id: 'new2' })];
    store.dispatch(setMessages({ messages: newMsgs }));
    expect(getVoiceState().messages).toHaveLength(2);
    expect(getVoiceState().messages[0]?.id).toBe('new1');
  });

  it('with clearTracking=true resets currentAiMessageId and currentPartialId', () => {
    store.dispatch(setCurrentAiMessageId('ai-msg-1'));
    store.dispatch(setCurrentPartialId('partial-1'));
    store.dispatch(setMessages({ messages: [], clearTracking: true }));
    expect(getVoiceState().currentAiMessageId).toBeNull();
    expect(getVoiceState().currentPartialId).toBeNull();
  });

  it('without clearTracking preserves currentAiMessageId', () => {
    store.dispatch(setCurrentAiMessageId('ai-msg-2'));
    store.dispatch(setMessages({ messages: [] }));
    expect(getVoiceState().currentAiMessageId).toBe('ai-msg-2');
  });
});

// ---------------------------------------------------------------------------
// Thread management
// ---------------------------------------------------------------------------

describe('voiceAgent slice – addThread', () => {
  it('prepends the new thread to the list', () => {
    store.dispatch(addThread({ id: 't1', title: 'Thread 1', createdAt: '', updatedAt: '', messageCount: 0 }));
    store.dispatch(addThread({ id: 't2', title: 'Thread 2', createdAt: '', updatedAt: '', messageCount: 0 }));
    const threads = getVoiceState().threads;
    expect(threads[0]?.id).toBe('t2'); // Most recent first (unshift)
    expect(threads[1]?.id).toBe('t1');
  });
});

describe('voiceAgent slice – renameThread', () => {
  it('renames an existing thread', () => {
    store.dispatch(addThread({ id: 'r1', title: 'Old Name', createdAt: '', updatedAt: '', messageCount: 0 }));
    store.dispatch(renameThread({ id: 'r1', title: 'New Name' }));
    expect(getVoiceState().threads[0]?.title).toBe('New Name');
  });

  it('is a no-op for unknown thread id', () => {
    store.dispatch(addThread({ id: 'r2', title: 'Keep', createdAt: '', updatedAt: '', messageCount: 0 }));
    store.dispatch(renameThread({ id: 'unknown', title: 'Should Not Apply' }));
    expect(getVoiceState().threads[0]?.title).toBe('Keep');
  });
});

describe('voiceAgent slice – markTitleSet', () => {
  it('adds thread id to titleSetForThreads', () => {
    store.dispatch(markTitleSet('tid-1'));
    expect(getVoiceState().titleSetForThreads).toContain('tid-1');
  });

  it('allows duplicate entries (caller deduplication responsibility)', () => {
    store.dispatch(markTitleSet('tid-dup'));
    store.dispatch(markTitleSet('tid-dup'));
    // The slice just pushes; dedup is handled by the caller guard in useVoiceAgent
    expect(getVoiceState().titleSetForThreads.filter((t) => t === 'tid-dup')).toHaveLength(2);
  });
});

// ---------------------------------------------------------------------------
// reset
// ---------------------------------------------------------------------------

describe('voiceAgent slice – reset', () => {
  it('restores status to idle', () => {
    store.dispatch(setStatus('speaking'));
    store.dispatch(reset());
    expect(getVoiceState().status).toBe('idle');
  });

  it('clears messages', () => {
    store.dispatch(addMessage(makeMessage()));
    store.dispatch(reset());
    expect(getVoiceState().messages).toHaveLength(0);
  });

  it('clears threads', () => {
    store.dispatch(addThread({ id: 'tt1', title: 'T', createdAt: '', updatedAt: '', messageCount: 0 }));
    store.dispatch(reset());
    expect(getVoiceState().threads).toHaveLength(0);
  });

  it('resets currentSampleRate to 0', () => {
    store.dispatch(setSampleRate(48000));
    store.dispatch(reset());
    expect(getVoiceState().currentSampleRate).toBe(0);
  });

  it('clears currentThreadId', () => {
    store.dispatch(setCurrentThreadId('some-thread'));
    store.dispatch(reset());
    expect(getVoiceState().currentThreadId).toBeNull();
  });

  it('resets isConnected to false', () => {
    store.dispatch(setIsConnected(true));
    store.dispatch(reset());
    expect(getVoiceState().isConnected).toBe(false);
  });
});
