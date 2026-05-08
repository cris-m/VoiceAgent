import { describe, it, expect, beforeEach, vi } from 'vitest';
import { configureStore } from '@reduxjs/toolkit';
import type { RootState } from '@/store/store';
import authReducer, { setAuth, logout } from '@/features/auth/slice';

describe('Auth Integration', () => {
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

  it('should handle complete login flow', () => {
    const loginResponse = {
      access_token: 'login-token-xyz',
      user_id: 'user-789',
      username: 'johndoe',
    };

    store.dispatch(
      setAuth({
        token: loginResponse.access_token,
        userId: loginResponse.user_id,
        username: loginResponse.username,
      })
    );

    const state = store.getState() as RootState;
    expect(state.auth.token).toBe('login-token-xyz');
    expect(state.auth.userId).toBe('user-789');
    expect(state.auth.username).toBe('johndoe');
    expect(state.auth.isAuthenticated).toBe(true);
  });

  it('should handle token refresh flow', () => {
    store.dispatch(
      setAuth({
        token: 'old-access-token',
        userId: 'user-789',
        username: 'johndoe',
      })
    );

    const refreshResponse = {
      access_token: 'new-access-token',
      user_id: 'user-789',
      username: 'johndoe',
    };

    store.dispatch(
      setAuth({
        token: refreshResponse.access_token,
        userId: refreshResponse.user_id,
        username: refreshResponse.username,
      })
    );

    const state = store.getState() as RootState;
    expect(state.auth.token).toBe('new-access-token');
    expect(state.auth.userId).toBe('user-789');
  });

  it('should handle logout and clear all state', () => {
    store.dispatch(
      setAuth({
        token: 'active-token',
        userId: 'user-789',
        username: 'johndoe',
      })
    );

    let state = store.getState() as RootState;
    expect(state.auth.isAuthenticated).toBe(true);

    store.dispatch(logout());

    state = store.getState() as RootState;
    expect(state.auth.token).toBeNull();
    expect(state.auth.userId).toBeNull();
    expect(state.auth.username).toBeNull();
    expect(state.auth.isAuthenticated).toBe(false);
    expect(state.auth.error).toBeNull();
    expect(state.auth.isLoading).toBe(false);
  });

  it('should maintain auth state across multiple token refreshes', () => {
    const userId = 'user-persistent';
    const username = 'persistent-user';

    store.dispatch(
      setAuth({
        token: 'token-1',
        userId,
        username,
      })
    );

    for (let i = 2; i <= 5; i++) {
      store.dispatch(
        setAuth({
          token: `token-${i}`,
          userId,
          username,
        })
      );
    }

    const state = store.getState() as RootState;
    expect(state.auth.token).toBe('token-5');
    expect(state.auth.userId).toBe(userId);
    expect(state.auth.username).toBe(username);
  });

  it('should handle failed logout gracefully', () => {
    store.dispatch(
      setAuth({
        token: 'token',
        userId: 'user-123',
        username: 'user',
      })
    );

    store.dispatch(logout());

    const state = store.getState() as RootState;
    expect(state.auth.token).toBeNull();
    expect(state.auth.isAuthenticated).toBe(false);
  });
});
