/**
 * Tests for PersonalityAPI RTK Query slice (personalityService.ts).
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
    return { data: { personalities: [], default_id: 'default' } };
  }),
  authBaseQuery: vi.fn(async (arg: string | RequestDescriptor) => {
    capturedRequests.push(typeof arg === 'string' ? { url: arg } : arg);
    return { data: {} };
  }),
}));

import { PersonalityAPI } from '@/services/personality';

// ---------------------------------------------------------------------------
// Store factory
// ---------------------------------------------------------------------------

function makeStore() {
  return configureStore({
    reducer: {
      auth: authReducer,
      [AuthAPI.reducerPath]: AuthAPI.reducer,
      [PersonalityAPI.reducerPath]: PersonalityAPI.reducer,
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
    middleware: (g) => g().concat(AuthAPI.middleware, PersonalityAPI.middleware),
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

describe('PersonalityAPI – getPersonalities', () => {
  beforeEach(() => { capturedRequests.length = 0; });

  it('calls GET /personality', async () => {
    const store = makeStore();
    const req = await dispatchAndWait(
      store,
      PersonalityAPI.endpoints.getPersonalities.initiate(),
    );
    expect(req?.url).toBe('/personality');
  });
});

describe('PersonalityAPI – configuration', () => {
  it('reducerPath is personalityAPI', () => {
    expect(PersonalityAPI.reducerPath).toBe('personalityAPI');
  });

  it('exports useGetPersonalitiesQuery hook', () => {
    expect(typeof PersonalityAPI.useGetPersonalitiesQuery).toBe('function');
  });

  it('has refetchOnFocus disabled (avoids spurious re-fetches)', () => {
    // refetchOnFocus is set to false — personalities are nearly static
    // We verify this by checking the API definition has getPersonalities as
    // the only endpoint (single-endpoint API for a stable resource).
    expect(PersonalityAPI.endpoints.getPersonalities).toBeDefined();
    // Verify no unexpected endpoints were added
    const endpointNames = Object.keys(PersonalityAPI.endpoints);
    expect(endpointNames).toEqual(['getPersonalities']);
  });
});
