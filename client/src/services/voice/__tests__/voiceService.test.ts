/**
 * Tests for VoiceAPI RTK Query slice (voiceService.ts).
 *
 * Strategy: mock the baseQuery so we can assert what URL/method/body
 * RTK Query passes down to it, without hitting real network or AbortSignal
 * compatibility issues between jsdom and Node's built-in fetch/undici.
 *
 * We intercept at the baseQuery layer using vi.mock on the baseQuery module.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import { authReducer } from '@/features/auth';
import { AuthAPI } from '@/services/auth';

// ---------------------------------------------------------------------------
// Mock the baseQuery — capture calls without real HTTP
// ---------------------------------------------------------------------------

type RequestDescriptor = {
  url: string;
  method?: string;
  body?: unknown;
};

const capturedRequests: RequestDescriptor[] = [];

vi.mock('@/services/auth/baseQuery', () => ({
  baseQueryWithReauth: vi.fn(async (arg: string | RequestDescriptor) => {
    const desc: RequestDescriptor = typeof arg === 'string' ? { url: arg } : arg;
    capturedRequests.push(desc);
    return { data: {} };
  }),
  authBaseQuery: vi.fn(async (arg: string | RequestDescriptor) => {
    const desc: RequestDescriptor = typeof arg === 'string' ? { url: arg } : arg;
    capturedRequests.push(desc);
    return { data: {} };
  }),
}));

// Import AFTER mock is registered
import { VoiceAPI } from '@/services/voice';

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function makeStore() {
  return configureStore({
    reducer: {
      auth: authReducer,
      [AuthAPI.reducerPath]: AuthAPI.reducer,
      [VoiceAPI.reducerPath]: VoiceAPI.reducer,
    },
    preloadedState: {
      auth: {
        token: 'test-token',
        userId: 'uid-1',
        username: 'tester',
        email: null,
        isAuthenticated: true,
        isLoading: false,
        error: null,
        rememberMe: false,
      },
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(AuthAPI.middleware, VoiceAPI.middleware),
  });
}

// ---------------------------------------------------------------------------
// Helper: dispatch and wait for the baseQuery to be called
// ---------------------------------------------------------------------------

async function dispatchAndWait(store: ReturnType<typeof makeStore>, action: unknown) {
  capturedRequests.length = 0;
  const promise = store.dispatch(action as Parameters<typeof store.dispatch>[0]);
  await promise;
  return capturedRequests[capturedRequests.length - 1];
}

// ---------------------------------------------------------------------------
// Tests: query endpoints
// ---------------------------------------------------------------------------

describe('VoiceAPI – query endpoints', () => {
  beforeEach(() => {
    capturedRequests.length = 0;
  });

  it('getVoices → GET /voice/voices', async () => {
    const store = makeStore();
    const req = await dispatchAndWait(store, VoiceAPI.endpoints.getVoices.initiate());
    expect(req?.url).toBe('/voice/voices');
  });

  it('getLanguages → GET /voice/languages', async () => {
    const store = makeStore();
    const req = await dispatchAndWait(store, VoiceAPI.endpoints.getLanguages.initiate());
    expect(req?.url).toBe('/voice/languages');
  });

  it('getVoiceConfig → GET /voice/config', async () => {
    const store = makeStore();
    const req = await dispatchAndWait(store, VoiceAPI.endpoints.getVoiceConfig.initiate());
    expect(req?.url).toBe('/voice/config');
  });

  it('getNarrations → GET /voice/narrations', async () => {
    const store = makeStore();
    const req = await dispatchAndWait(store, VoiceAPI.endpoints.getNarrations.initiate());
    expect(req?.url).toBe('/voice/narrations');
  });
});

describe('VoiceAPI – mutation endpoints', () => {
  beforeEach(() => {
    capturedRequests.length = 0;
  });

  it('narrate → POST /voice/narrate with body', async () => {
    const store = makeStore();
    const body = { text: 'Say this', voice_id: 'v1', speed: 1.0 };
    const req = await dispatchAndWait(
      store,
      VoiceAPI.endpoints.narrate.initiate(body),
    );
    expect(req?.url).toBe('/voice/narrate');
    expect(req?.method).toBe('POST');
    expect((req?.body as typeof body)?.text).toBe('Say this');
    expect((req?.body as typeof body)?.voice_id).toBe('v1');
  });

  it('previewVoice → POST /voice/narrate', async () => {
    const store = makeStore();
    const req = await dispatchAndWait(
      store,
      VoiceAPI.endpoints.previewVoice.initiate({ text: 'Preview', voice_id: 'v2' }),
    );
    expect(req?.url).toBe('/voice/narrate');
    expect(req?.method).toBe('POST');
  });

  it('deleteNarration → DELETE /voice/narrations/:id', async () => {
    const store = makeStore();
    const req = await dispatchAndWait(
      store,
      VoiceAPI.endpoints.deleteNarration.initiate('narr-7'),
    );
    expect(req?.url).toBe('/voice/narrations/narr-7');
    expect(req?.method).toBe('DELETE');
  });

  it('deleteCloneVoice → DELETE /voice/clones/:id', async () => {
    const store = makeStore();
    const req = await dispatchAndWait(
      store,
      VoiceAPI.endpoints.deleteCloneVoice.initiate('clone-42'),
    );
    expect(req?.url).toBe('/voice/clones/clone-42');
    expect(req?.method).toBe('DELETE');
  });

  it('transcribe → POST /voice/transcribe', async () => {
    const store = makeStore();
    const formData = new FormData();
    const req = await dispatchAndWait(
      store,
      VoiceAPI.endpoints.transcribe.initiate(formData),
    );
    expect(req?.url).toBe('/voice/transcribe');
    expect(req?.method).toBe('POST');
  });

  it('cloneVoice → POST /voice/clone', async () => {
    const store = makeStore();
    const formData = new FormData();
    const req = await dispatchAndWait(
      store,
      VoiceAPI.endpoints.cloneVoice.initiate(formData),
    );
    expect(req?.url).toBe('/voice/clone');
    expect(req?.method).toBe('POST');
  });
});

// ---------------------------------------------------------------------------
// API-level configuration
// ---------------------------------------------------------------------------

describe('VoiceAPI – configuration', () => {
  it('reducerPath is voiceAPI', () => {
    expect(VoiceAPI.reducerPath).toBe('voiceAPI');
  });

  it('exports all expected React hooks', () => {
    expect(typeof VoiceAPI.useGetVoicesQuery).toBe('function');
    expect(typeof VoiceAPI.useGetLanguagesQuery).toBe('function');
    expect(typeof VoiceAPI.useGetVoiceConfigQuery).toBe('function');
    expect(typeof VoiceAPI.useGetNarrationsQuery).toBe('function');
    expect(typeof VoiceAPI.useNarrateMutation).toBe('function');
    expect(typeof VoiceAPI.usePreviewVoiceMutation).toBe('function');
    expect(typeof VoiceAPI.useDeleteNarrationMutation).toBe('function');
    expect(typeof VoiceAPI.useTranscribeMutation).toBe('function');
    expect(typeof VoiceAPI.useCloneVoiceMutation).toBe('function');
    expect(typeof VoiceAPI.useDeleteCloneVoiceMutation).toBe('function');
  });
});
