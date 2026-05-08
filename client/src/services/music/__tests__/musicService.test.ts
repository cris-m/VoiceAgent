/**
 * Tests for MusicAPI RTK Query slice (musicService.ts).
 * Uses the same mocked-baseQuery strategy as voiceService.test.ts.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import { authReducer } from '@/features/auth';
import { AuthAPI } from '@/services/auth';

// ---------------------------------------------------------------------------
// Mock baseQuery
// ---------------------------------------------------------------------------

type RequestDescriptor = { url: string; method?: string; body?: unknown };
const capturedRequests: RequestDescriptor[] = [];

vi.mock('@/services/auth/baseQuery', () => ({
  baseQueryWithReauth: vi.fn(async (arg: string | RequestDescriptor) => {
    capturedRequests.push(typeof arg === 'string' ? { url: arg } : arg);
    return { data: {} };
  }),
  authBaseQuery: vi.fn(async (arg: string | RequestDescriptor) => {
    capturedRequests.push(typeof arg === 'string' ? { url: arg } : arg);
    return { data: {} };
  }),
}));

import { MusicAPI } from '@/services/music';

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function makeStore() {
  return configureStore({
    reducer: {
      auth: authReducer,
      [AuthAPI.reducerPath]: AuthAPI.reducer,
      [MusicAPI.reducerPath]: MusicAPI.reducer,
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
    middleware: (g) => g().concat(AuthAPI.middleware, MusicAPI.middleware),
  });
}

async function dispatchAndWait(store: ReturnType<typeof makeStore>, action: unknown) {
  capturedRequests.length = 0;
  await store.dispatch(action as Parameters<typeof store.dispatch>[0]);
  return capturedRequests[capturedRequests.length - 1];
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('MusicAPI – getMusicList', () => {
  beforeEach(() => { capturedRequests.length = 0; });

  it('calls GET /music/list', async () => {
    const store = makeStore();
    const req = await dispatchAndWait(store, MusicAPI.endpoints.getMusicList.initiate());
    expect(req?.url).toBe('/music/list');
  });
});

describe('MusicAPI – generateMusic', () => {
  beforeEach(() => { capturedRequests.length = 0; });

  it('calls POST /music/generate', async () => {
    const store = makeStore();
    const body = { prompt: 'Upbeat jazz', style_tags: ['jazz'], duration: 30 };
    const req = await dispatchAndWait(store, MusicAPI.endpoints.generateMusic.initiate(body));
    expect(req?.url).toBe('/music/generate');
    expect(req?.method).toBe('POST');
  });

  it('sends the prompt and style_tags in the body', async () => {
    const store = makeStore();
    const body = { prompt: 'Calm ambient', style_tags: ['ambient', 'calm'], duration: 60 };
    const req = await dispatchAndWait(store, MusicAPI.endpoints.generateMusic.initiate(body));
    expect((req?.body as typeof body)?.prompt).toBe('Calm ambient');
    expect((req?.body as typeof body)?.style_tags).toEqual(['ambient', 'calm']);
    expect((req?.body as typeof body)?.duration).toBe(60);
  });
});

describe('MusicAPI – deleteMusic', () => {
  beforeEach(() => { capturedRequests.length = 0; });

  it('calls DELETE /music/:id', async () => {
    const store = makeStore();
    const req = await dispatchAndWait(store, MusicAPI.endpoints.deleteMusic.initiate('track-5'));
    expect(req?.url).toBe('/music/track-5');
    expect(req?.method).toBe('DELETE');
  });
});

describe('MusicAPI – configuration', () => {
  it('reducerPath is musicAPI', () => {
    expect(MusicAPI.reducerPath).toBe('musicAPI');
  });

  it('exports React hooks', () => {
    expect(typeof MusicAPI.useGetMusicListQuery).toBe('function');
    expect(typeof MusicAPI.useGenerateMusicMutation).toBe('function');
    expect(typeof MusicAPI.useDeleteMusicMutation).toBe('function');
  });
});
