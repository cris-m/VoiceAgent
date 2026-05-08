import { describe, it, expect, beforeEach, vi } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import type { RootState } from '@/store/store';
import authReducer, { setAuth, logout } from '@/features/auth/slice';

describe('Auth Service', () => {
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

  it('should set auth state correctly', () => {
    const authPayload = {
      token: 'test-token',
      userId: 'user-123',
      username: 'testuser',
    };

    store.dispatch(setAuth(authPayload));
    const state = store.getState() as RootState;

    expect(state.auth.token).toBe('test-token');
    expect(state.auth.userId).toBe('user-123');
    expect(state.auth.username).toBe('testuser');
    expect(state.auth.isAuthenticated).toBe(true);
  });

  it('should clear auth on logout', () => {
    store.dispatch(
      setAuth({
        token: 'test-token',
        userId: 'user-123',
        username: 'testuser',
      })
    );

    store.dispatch(logout());
    const state = store.getState() as RootState;

    expect(state.auth.token).toBeNull();
    expect(state.auth.userId).toBeNull();
    expect(state.auth.username).toBeNull();
    expect(state.auth.isAuthenticated).toBe(false);
  });

  it('should maintain initial state', () => {
    const state = store.getState() as RootState;

    expect(state.auth.token).toBeNull();
    expect(state.auth.userId).toBeNull();
    expect(state.auth.username).toBeNull();
    expect(state.auth.isAuthenticated).toBe(false);
    expect(state.auth.error).toBeNull();
    expect(state.auth.isLoading).toBe(false);
  });
});
