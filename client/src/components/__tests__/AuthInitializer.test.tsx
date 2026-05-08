/**
 * Tests for AuthInitializer.
 *
 * The component has a module-level `_authInitStarted` flag that guards against
 * double-initialization in React StrictMode. We mock `@/services/auth` at the
 * top level and use vi.resetModules() between tests to get a fresh module so
 * the guard is always in its initial (false) state.
 *
 * Pattern: each test calls `importFresh()` which reloads the component module
 * after resetting the module registry.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, waitFor, cleanup, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';
import type { ReactNode } from 'react';

// ---------------------------------------------------------------------------
// Shared mock refresh function — replaced per test via mockReturnValue
// ---------------------------------------------------------------------------

const mockRefresh = vi.fn();

vi.mock('@/services/auth', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useRefreshMutation: () => [mockRefresh, { isLoading: false }],
  };
});

// ---------------------------------------------------------------------------
// Inline minimal Redux store — avoids re-importing slices with shared state
// ---------------------------------------------------------------------------

interface AuthStateShape {
  token: string | null;
  userId: string | null;
  username: string | null;
  email: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  rememberMe: boolean;
}

const authInitial: AuthStateShape = {
  token: null,
  userId: null,
  username: null,
  email: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  rememberMe: false,
};

function authReducerMini(
  state: AuthStateShape = authInitial,
  action: { type: string; payload?: unknown } = { type: '@@INIT' },
): AuthStateShape {
  if (action.type === 'auth/setAuth') {
    const p = action.payload as { token: string; userId: string; username: string };
    return { ...state, token: p.token, userId: p.userId, username: p.username, isAuthenticated: true };
  }
  if (action.type === 'auth/logout') {
    return { ...state, token: null, userId: null, username: null, isAuthenticated: false };
  }
  return state;
}

function makeStore() {
  return configureStore({ reducer: { auth: authReducerMini } });
}

type TestStore = ReturnType<typeof makeStore>;

function wrap(store: TestStore) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return React.createElement(Provider, { store }, children);
  };
}

// ---------------------------------------------------------------------------
// Import component — AFTER vi.mock so the mock is in place
// ---------------------------------------------------------------------------

// We import once per file and rely on the module-level flag being reset
// between describe blocks by re-importing the module dynamically.
// NOTE: because vi.resetModules() + dynamic import within the same test
// file scope is unreliable in vitest 1.x, we test the external behavior
// (what renders / what state changes) rather than internal call counts.

// ---------------------------------------------------------------------------
// Helper: fresh import so the module-level _authInitStarted flag resets
// ---------------------------------------------------------------------------

async function importFreshAuthInitializer() {
  vi.resetModules();
  // Re-apply the mock after resetModules clears the registry
  vi.mock('@/services/auth', async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>();
    return {
      ...actual,
      useRefreshMutation: () => [mockRefresh, { isLoading: false }],
    };
  });
  const mod = await import('@/components/AuthInitializer');
  return mod.AuthInitializer;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('AuthInitializer', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders children after init when rememberMe is not set (no refresh call)', async () => {
    mockRefresh.mockReturnValue({
      unwrap: () => Promise.resolve({ access_token: 'tok', user_id: 'u', username: 'u', token_type: 'bearer' }),
    });

    const AuthInitializer = await importFreshAuthInitializer();
    const store = makeStore();

    await act(async () => {
      render(
        <Provider store={store}>
          <AuthInitializer>
            <div data-testid="child">Hello</div>
          </AuthInitializer>
        </Provider>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('child')).toBeInTheDocument();
    });

    // rememberMe not set → logout dispatched; not authenticated
    const auth = store.getState().auth;
    expect(auth.isAuthenticated).toBe(false);
  });

  it('calls refresh and updates auth when rememberMe is true', async () => {
    localStorage.setItem('auth_remember', 'true');
    mockRefresh.mockReturnValue({
      unwrap: () =>
        Promise.resolve({
          access_token: 'tok-new',
          user_id: 'uid-1',
          username: 'alice',
          token_type: 'bearer',
        }),
    });

    const AuthInitializer = await importFreshAuthInitializer();
    const store = makeStore();

    await act(async () => {
      render(
        <Provider store={store}>
          <AuthInitializer>
            <div data-testid="child">Hello</div>
          </AuthInitializer>
        </Provider>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('child')).toBeInTheDocument();
    });

    const auth = store.getState().auth;
    expect(auth.token).toBe('tok-new');
    expect(auth.isAuthenticated).toBe(true);
  });

  it('dispatches logout when refresh throws', async () => {
    localStorage.setItem('auth_remember', 'true');
    mockRefresh.mockReturnValue({
      unwrap: () => Promise.reject({ error: { message: 'Expired' }, status: 401 }),
    });

    const AuthInitializer = await importFreshAuthInitializer();
    const store = makeStore();

    await act(async () => {
      render(
        <Provider store={store}>
          <AuthInitializer>
            <div data-testid="child">Hello</div>
          </AuthInitializer>
        </Provider>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('child')).toBeInTheDocument();
    });

    const auth = store.getState().auth;
    expect(auth.isAuthenticated).toBe(false);
    expect(auth.token).toBeNull();
  });

  it('StrictMode: renders children without crashing', async () => {
    localStorage.setItem('auth_remember', 'true');
    mockRefresh.mockReturnValue({
      unwrap: () =>
        Promise.resolve({
          access_token: 'tok-sm',
          user_id: 'uid-sm',
          username: 'sm-user',
          token_type: 'bearer',
        }),
    });

    const AuthInitializer = await importFreshAuthInitializer();
    const store = makeStore();

    await act(async () => {
      render(
        <React.StrictMode>
          <Provider store={store}>
            <AuthInitializer>
              <div data-testid="child">Hello</div>
            </AuthInitializer>
          </Provider>
        </React.StrictMode>,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('child')).toBeInTheDocument();
    });
  });
});
