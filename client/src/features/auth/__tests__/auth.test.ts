import { describe, it, expect, beforeEach } from 'vitest';
import { authReducer, setAuth, logout, clearError } from '../slice';
import type { AuthState } from '../slice';
import {
  selectIsAuthenticated,
  selectAuthToken,
  selectUserId,
  selectUsername,
  selectIsLoading,
  selectAuthError,
} from '../selectors';
import type { RootState } from '@/store/store';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a minimal RootState fragment that satisfies the selectors. */
function makeRootState(auth: Partial<AuthState>): RootState {
  const fullAuth: AuthState = {
    userId: null,
    username: null,
    email: null,
    token: null,
    isLoading: false,
    isAuthenticated: false,
    error: null,
    rememberMe: false,
    ...auth,
  };
  return { auth: fullAuth } as unknown as RootState;
}

const initialState: AuthState = {
  userId: null,
  username: null,
  email: null,
  token: null,
  isLoading: false,
  isAuthenticated: false,
  error: null,
  rememberMe: false,
};

// ---------------------------------------------------------------------------
// Reducer — state initialization
// ---------------------------------------------------------------------------

describe('authReducer – state initialization', () => {
  it('returns the initial state when called with undefined state', () => {
    const state = authReducer(undefined, { type: '@@INIT' });
    expect(state).toEqual(initialState);
  });
});

// ---------------------------------------------------------------------------
// Reducer — setAuth action
// ---------------------------------------------------------------------------

describe('authReducer – setAuth', () => {
  let state: AuthState;

  beforeEach(() => {
    state = { ...initialState };
  });

  it('sets token in state', () => {
    const result = authReducer(
      state,
      setAuth({ token: 'tok-123', userId: 'u-1', username: 'alice' }),
    );
    expect(result.token).toBe('tok-123');
  });

  it('sets userId in state', () => {
    const result = authReducer(
      state,
      setAuth({ token: 'tok-123', userId: 'u-1', username: 'alice' }),
    );
    expect(result.userId).toBe('u-1');
  });

  it('sets username in state', () => {
    const result = authReducer(
      state,
      setAuth({ token: 'tok-123', userId: 'u-1', username: 'alice' }),
    );
    expect(result.username).toBe('alice');
  });

  it('marks isAuthenticated as true', () => {
    const result = authReducer(
      state,
      setAuth({ token: 'tok-123', userId: 'u-1', username: 'alice' }),
    );
    expect(result.isAuthenticated).toBe(true);
  });

  it('does not mutate original state slice', () => {
    authReducer(state, setAuth({ token: 'tok-123', userId: 'u-1', username: 'alice' }));
    expect(state.token).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('overwrites a previously set token when called again', () => {
    const first = authReducer(
      state,
      setAuth({ token: 'old-tok', userId: 'u-1', username: 'alice' }),
    );
    const second = authReducer(
      first,
      setAuth({ token: 'new-tok', userId: 'u-2', username: 'bob' }),
    );
    expect(second.token).toBe('new-tok');
    expect(second.userId).toBe('u-2');
    expect(second.username).toBe('bob');
  });
});

// ---------------------------------------------------------------------------
// Reducer — logout action
// ---------------------------------------------------------------------------

describe('authReducer – logout', () => {
  it('clears token', () => {
    const authenticated: AuthState = {
      ...initialState,
      token: 'tok-abc',
      userId: 'u-1',
      username: 'alice',
      isAuthenticated: true,
    };
    const result = authReducer(authenticated, logout());
    expect(result.token).toBeNull();
  });

  it('clears userId', () => {
    const authenticated: AuthState = {
      ...initialState,
      token: 'tok-abc',
      userId: 'u-1',
      username: 'alice',
      isAuthenticated: true,
    };
    const result = authReducer(authenticated, logout());
    expect(result.userId).toBeNull();
  });

  it('clears username', () => {
    const authenticated: AuthState = {
      ...initialState,
      token: 'tok-abc',
      userId: 'u-1',
      username: 'alice',
      isAuthenticated: true,
    };
    const result = authReducer(authenticated, logout());
    expect(result.username).toBeNull();
  });

  it('clears email', () => {
    const withEmail: AuthState = {
      ...initialState,
      token: 'tok-abc',
      userId: 'u-1',
      username: 'alice',
      email: 'alice@example.com',
      isAuthenticated: true,
    };
    const result = authReducer(withEmail, logout());
    expect(result.email).toBeNull();
  });

  it('sets isAuthenticated to false', () => {
    const authenticated: AuthState = {
      ...initialState,
      token: 'tok-abc',
      userId: 'u-1',
      username: 'alice',
      isAuthenticated: true,
    };
    const result = authReducer(authenticated, logout());
    expect(result.isAuthenticated).toBe(false);
  });

  it('clears any existing error', () => {
    const withError: AuthState = {
      ...initialState,
      error: 'Something went wrong',
    };
    const result = authReducer(withError, logout());
    expect(result.error).toBeNull();
  });

  it('is idempotent when called on already-logged-out state', () => {
    const result = authReducer(initialState, logout());
    expect(result).toEqual(initialState);
  });
});

// ---------------------------------------------------------------------------
// Reducer — clearError action
// ---------------------------------------------------------------------------

describe('authReducer – clearError', () => {
  it('sets error to null', () => {
    const withError: AuthState = { ...initialState, error: 'Network error' };
    const result = authReducer(withError, clearError());
    expect(result.error).toBeNull();
  });

  it('leaves other fields intact', () => {
    const withError: AuthState = {
      ...initialState,
      token: 'tok',
      userId: 'u-1',
      username: 'alice',
      isAuthenticated: true,
      error: 'Oops',
    };
    const result = authReducer(withError, clearError());
    expect(result.token).toBe('tok');
    expect(result.userId).toBe('u-1');
    expect(result.isAuthenticated).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// Selectors
// ---------------------------------------------------------------------------

describe('selectIsAuthenticated', () => {
  it('returns false from initial state', () => {
    expect(selectIsAuthenticated(makeRootState({}))).toBe(false);
  });

  it('returns true when isAuthenticated is set', () => {
    expect(selectIsAuthenticated(makeRootState({ isAuthenticated: true }))).toBe(true);
  });
});

describe('selectAuthToken', () => {
  it('returns null from initial state', () => {
    expect(selectAuthToken(makeRootState({}))).toBeNull();
  });

  it('returns the stored token', () => {
    expect(selectAuthToken(makeRootState({ token: 'jwt-xyz' }))).toBe('jwt-xyz');
  });
});

describe('selectUserId', () => {
  it('returns null from initial state', () => {
    expect(selectUserId(makeRootState({}))).toBeNull();
  });

  it('returns the stored userId', () => {
    expect(selectUserId(makeRootState({ userId: 'uid-99' }))).toBe('uid-99');
  });
});

describe('selectUsername', () => {
  it('returns null from initial state', () => {
    expect(selectUsername(makeRootState({}))).toBeNull();
  });

  it('returns the stored username', () => {
    expect(selectUsername(makeRootState({ username: 'bob' }))).toBe('bob');
  });
});

describe('selectIsLoading', () => {
  it('returns false from initial state', () => {
    expect(selectIsLoading(makeRootState({}))).toBe(false);
  });

  it('returns true when isLoading is set', () => {
    expect(selectIsLoading(makeRootState({ isLoading: true }))).toBe(true);
  });
});

describe('selectAuthError', () => {
  it('returns null from initial state', () => {
    expect(selectAuthError(makeRootState({}))).toBeNull();
  });

  it('returns the error string', () => {
    expect(selectAuthError(makeRootState({ error: 'Unauthorized' }))).toBe('Unauthorized');
  });
});

// ---------------------------------------------------------------------------
// selectTokenExists — derived selector (token !== null)
// ---------------------------------------------------------------------------

describe('selectAuthToken as selectTokenExists', () => {
  it('is falsy when no token is stored', () => {
    expect(Boolean(selectAuthToken(makeRootState({})))).toBe(false);
  });

  it('is truthy when a token is stored', () => {
    expect(Boolean(selectAuthToken(makeRootState({ token: 'any-token' })))).toBe(true);
  });
});
