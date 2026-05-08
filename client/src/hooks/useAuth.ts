import { useCallback } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { logout } from '@/features/auth';
import { useLogoutMutation, AuthAPI } from '@/services/auth';
import { authSelectors } from '@/features/auth';
import { reset } from '@/store';
import type { RootState } from '@/store/store';

export function useAuth() {
  const dispatch = useDispatch();
  // Select individual fields to avoid recreating object on every store change
  const userId = useSelector((state: RootState) => authSelectors.selectUserId(state));
  const username = useSelector((state: RootState) => authSelectors.selectUsername(state));
  const email = useSelector((state: RootState) => state.auth.email);
  const token = useSelector((state: RootState) => authSelectors.selectAuthToken(state));
  const isLoading = useSelector((state: RootState) => authSelectors.selectIsLoading(state));
  const isAuthenticated = useSelector((state: RootState) => authSelectors.selectIsAuthenticated(state));
  const error = useSelector((state: RootState) => authSelectors.selectAuthError(state));
  const [logoutMutation] = useLogoutMutation();

  const handleLogout = useCallback(async () => {
    try {
      await logoutMutation().unwrap();
    } catch (error) {
      console.warn('Logout request failed:', error);
    } finally {
      dispatch(logout());
      // Clear RTK Query cache to prevent leaking previous user's data
      dispatch(AuthAPI.util.resetApiState());
      dispatch(reset());
    }
  }, [logoutMutation, dispatch]);

  return {
    userId,
    username,
    email,
    token,
    isLoading,
    isAuthenticated,
    error,
    logout: handleLogout,
  };
}
