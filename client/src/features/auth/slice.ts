import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';

export interface AuthState {
  userId: string | null;
  username: string | null;
  email: string | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  rememberMe: boolean;
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

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout: (state) => {
      state.userId = null;
      state.username = null;
      state.email = null;
      state.token = null;
      state.isAuthenticated = false;
      state.error = null;
    },
    clearError: (state) => {
      state.error = null;
    },
    setAuth: (state, action: PayloadAction<{ token: string; userId: string; username: string }>) => {
      state.token = action.payload.token;
      state.userId = action.payload.userId;
      state.username = action.payload.username;
      state.isAuthenticated = true;
      // Server is authority on token validity; baseQueryWithReauth handles 401 refresh
    },
  },
});

export const { logout, clearError, setAuth } = authSlice.actions;
export const authReducer = authSlice.reducer;
export default authReducer;
