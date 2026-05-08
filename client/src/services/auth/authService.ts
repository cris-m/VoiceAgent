import { createApi } from '@reduxjs/toolkit/query/react';
import { setAuth } from '@/features/auth';
import { baseQueryWithReauth } from './baseQuery';

export interface Credentials {
  username: string;
  password: string;
}

export interface RegistrationData {
  username: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  user_id: string;
  username: string;
  token_type: string;
}

export const AuthAPI = createApi({
  reducerPath: 'authAPI',
  baseQuery: baseQueryWithReauth,
  endpoints: (builder) => ({
    login: builder.mutation<AuthResponse, Credentials>({
      query: (credentials) => ({
        url: '/auth/login',
        method: 'POST',
        body: credentials,
      }),
      async onQueryStarted(_, { dispatch, queryFulfilled }) {
        try {
          const { data } = await queryFulfilled;
          dispatch(setAuth({
            token: data.access_token,
            userId: data.user_id,
            username: data.username,
          }));
        } catch {
          // Error handled by RTK Query error state
        }
      },
    }),

    register: builder.mutation<AuthResponse, RegistrationData>({
      query: (data) => ({
        url: '/auth/register',
        method: 'POST',
        body: data,
      }),
      async onQueryStarted(_, { dispatch, queryFulfilled }) {
        try {
          const { data } = await queryFulfilled;
          dispatch(setAuth({
            token: data.access_token,
            userId: data.user_id,
            username: data.username,
          }));
        } catch {
          // Error handled by RTK Query error state
        }
      },
    }),

    refresh: builder.mutation<AuthResponse, void>({
      query: () => ({
        url: '/auth/refresh',
        method: 'POST',
      }),
    }),

    logout: builder.mutation<void, void>({
      query: () => ({
        url: '/auth/logout',
        method: 'POST',
      }),
    }),
  }),
});

export const {
  useLoginMutation,
  useRegisterMutation,
  useRefreshMutation,
  useLogoutMutation,
} = AuthAPI;
