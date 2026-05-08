import type { RootState } from '@/store/store';
import type { AuthState } from './slice';

const selectAuthState = (state: RootState): AuthState => state.auth;

export const selectIsAuthenticated = (state: RootState): boolean =>
  selectAuthState(state).isAuthenticated;

export const selectAuthToken = (state: RootState): string | null =>
  selectAuthState(state).token;

export const selectUserId = (state: RootState): string | null =>
  selectAuthState(state).userId;

export const selectUsername = (state: RootState): string | null =>
  selectAuthState(state).username;

export const selectIsLoading = (state: RootState): boolean =>
  selectAuthState(state).isLoading;

export const selectAuthError = (state: RootState): string | null =>
  selectAuthState(state).error;

