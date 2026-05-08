import { fetchBaseQuery } from '@reduxjs/toolkit/query';
import type {
  BaseQueryFn,
  FetchArgs,
} from '@reduxjs/toolkit/query';
import type { RootState } from '@/store/store';
import type { NormalizedError, ApiError } from '@/types/errors';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';

interface TokenRefreshResponse {
  access_token: string;
  user_id: string;
  username: string;
  token_type: string;
}

/**
 * Simple Promise-based mutex to prevent concurrent token refresh requests
 * Prevents token refresh storms when multiple requests fail with 401 simultaneously
 * Uses a FIFO queue of waiters to ensure all concurrent acquirers are resolved
 */
class SimpleMutex {
  private _isLocked = false;
  private _waiters: Array<() => void> = [];

  async acquire(): Promise<() => void> {
    while (this._isLocked) {
      await new Promise<void>((resolve) => {
        this._waiters.push(resolve);
      });
    }
    this._isLocked = true;
    return () => this.release();
  }

  private release() {
    this._isLocked = false;
    const nextWaiter = this._waiters.shift();
    if (nextWaiter) {
      nextWaiter();
    }
  }
}

const mutex = new SimpleMutex();

/**
 * Normalize any API error shape to the standard NormalizedError format.
 * Handles:
 * - New normalized format: {"error": {...}}
 * - Legacy FastAPI detail shapes: {"detail": "string" | array}
 * - Unknown errors
 */
function normalizeError(raw: unknown): NormalizedError {
  const err = raw as { status?: number; data?: unknown };
  const status = typeof err.status === 'number' ? err.status : 0;
  const data = err.data as Record<string, unknown> | null | undefined;

  // Already our normalized format
  if (data && typeof data.error === 'object' && data.error !== null) {
    return { status, error: data.error as ApiError };
  }

  // Legacy FastAPI: {"detail": "string" | array}
  const detail = data?.detail;
  if (typeof detail === 'string') {
    return {
      status,
      error: { code: 'HTTP_ERROR', message: detail },
    };
  }

  if (Array.isArray(detail)) {
    // Legacy 422 array — extract first message
    const first = detail[0] as Record<string, unknown> | undefined;
    return {
      status,
      error: {
        code: 'VALIDATION_ERROR',
        message: String(first?.msg ?? 'Validation failed'),
      },
    };
  }

  return {
    status,
    error: { code: 'UNKNOWN_ERROR', message: 'An error occurred' },
  };
}

export const authBaseQuery = fetchBaseQuery({
  baseUrl: API_URL,
  credentials: 'include',
  prepareHeaders: (headers, { getState }) => {
    const state = getState() as RootState;
    const token = state.auth.token;

    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    return headers;
  },
});

const rtkBaseQuery = fetchBaseQuery({
  baseUrl: API_URL,
  credentials: 'include',
  prepareHeaders: (headers, { getState }) => {
    const state = getState() as RootState;
    const token = state.auth.token;

    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    return headers;
  },
});

/**
 * Enhanced base query with automatic token refresh on 401
 *
 * Flow:
 * 1. Make request
 * 2. If 401 and not auth endpoint:
 *    - Wait for any concurrent refresh (mutex)
 *    - Check if token already refreshed by another request
 *    - If not, acquire mutex and refresh
 *    - Retry original request with new token
 * 3. Return result with normalized error
 *
 * Note: Error is cast to NormalizedError on the component side.
 * RTK Query's type system treats this as FetchBaseQueryError at the hook level.
 */
export const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  NormalizedError
> = async (args, api, extraOptions) => {
  let result = await rtkBaseQuery(args, api, extraOptions);

  // Don't attempt refresh for auth endpoints themselves
  const isAuthRequest =
    (typeof args === 'string' && args.startsWith('/auth')) ||
    (typeof args !== 'string' && args.url?.startsWith('/auth'));

  if (result.error?.status === 401 && !isAuthRequest) {
    // Wait for any concurrent refresh attempt
    const release = await mutex.acquire();

    try {
      // Double-check: if another concurrent request already refreshed, use the new token
      const state = api.getState() as RootState;
      const authState = state.auth;
      if (authState.token) {
        // Token was updated by another concurrent request, retry with new token
        result = await rtkBaseQuery(args, api, extraOptions);
        if (result.error) {
          return { error: normalizeError(result.error) };
        }
        return result;
      }
      // No token; proceed with refresh below

      // Attempt token refresh using httpOnly cookie
      const refreshResult = await rtkBaseQuery(
        { url: '/auth/refresh', method: 'POST' },
        api,
        extraOptions
      );

      if (refreshResult.data) {
        const tokenData = refreshResult.data as TokenRefreshResponse;

        // Update Redux state with new access token
        api.dispatch({
          type: 'auth/setAuth',
          payload: {
            token: tokenData.access_token,
            userId: tokenData.user_id,
            username: tokenData.username,
          },
        });

        // Retry original request with new token
        result = await rtkBaseQuery(args, api, extraOptions);
      } else {
        // Refresh failed, logout
        api.dispatch({ type: 'auth/logout' });
      }
    } finally {
      release();
    }
  }

  // Normalize error before returning
  if (result.error) {
    return { error: normalizeError(result.error) };
  }

  return result;
};
