import { describe, it, expect, beforeEach } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import type { RootState } from '@/store/store';
import authReducer, { setAuth, logout } from '@/features/auth/slice';

describe('useAuth Hook', () => {
  let store = configureStore({
    reducer: {
      auth: authReducer,
    },
  });

  beforeEach(() => {
    store = configureStore({
      reducer: {
        auth: authReducer,
      },
    });
  });

  it('should return initial null values', () => {
    const state = store.getState() as RootState;
    expect(state.auth.token).toBeNull();
    expect(state.auth.userId).toBeNull();
    expect(state.auth.username).toBeNull();
    expect(state.auth.isAuthenticated).toBe(false);
  });

  it('should return authenticated user data after setAuth', () => {
    const authPayload = {
      token: 'jwt-token-123',
      userId: 'user-456',
      username: 'johndoe',
    };

    store.dispatch(setAuth(authPayload));
    const state = store.getState() as RootState;

    expect(state.auth.token).toBe('jwt-token-123');
    expect(state.auth.userId).toBe('user-456');
    expect(state.auth.username).toBe('johndoe');
    expect(state.auth.isAuthenticated).toBe(true);
  });

  it('should clear auth state on logout', () => {
    store.dispatch(
      setAuth({
        token: 'test-token',
        userId: 'user-123',
        username: 'testuser',
      })
    );

    expect(store.getState().auth.isAuthenticated).toBe(true);

    store.dispatch(logout());
    const state = store.getState() as RootState;

    expect(state.auth.token).toBeNull();
    expect(state.auth.userId).toBeNull();
    expect(state.auth.username).toBeNull();
    expect(state.auth.isAuthenticated).toBe(false);
  });

  it('should update token independently without affecting other fields', () => {
    store.dispatch(
      setAuth({
        token: 'old-token',
        userId: 'user-123',
        username: 'testuser',
      })
    );

    store.dispatch(
      setAuth({
        token: 'new-token',
        userId: 'user-123',
        username: 'testuser',
      })
    );

    const state = store.getState() as RootState;
    expect(state.auth.token).toBe('new-token');
    expect(state.auth.userId).toBe('user-123');
  });

  it('should maintain error state separately', () => {
    const state = store.getState() as RootState;
    expect(state.auth.error).toBeNull();
  });

  it('should not have expiresAt field', () => {
    const state = store.getState() as RootState;
    expect('expiresAt' in state.auth).toBe(false);
  });
});
