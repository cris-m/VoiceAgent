import { useEffect, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import { setAuth, logout } from '@/features/auth';
import { useRefreshMutation } from '@/services/auth';

interface AuthInitializerProps {
  children: React.ReactNode;
}

// Module-level flag to prevent double initialization in StrictMode
let _authInitStarted = false;

export function AuthInitializer({ children }: AuthInitializerProps) {
  const dispatch = useDispatch();
  const hasRun = useRef(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [refresh] = useRefreshMutation();

  useEffect(() => {
    if (_authInitStarted || hasRun.current) {
      setIsInitializing(false);
      return;
    }
    _authInitStarted = true;
    hasRun.current = true;

    const initializeAuth = async () => {
      try {
        const rememberMe = localStorage.getItem('auth_remember') === 'true';
        if (!rememberMe) {
          dispatch(logout());
          return;
        }

        const data = await refresh().unwrap();
        dispatch(
          setAuth({
            token: data.access_token,
            userId: data.user_id,
            username: data.username,
          }),
        );
      } catch (error) {
        const e = error as { error?: { message?: string }; status?: number };
        console.debug(
          `[Auth] Initialization failed (${e.error?.message ?? 'unknown'}), logging out`,
        );
        dispatch(logout());
      } finally {
        setIsInitializing(false);
      }
    };

    initializeAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isInitializing) {
    return (
      <div
        className="flex items-center justify-center min-h-screen"
        style={{ backgroundColor: 'var(--color-surface-base)' }}
      >
        <div className="flex flex-col items-center gap-4">
          <div
            className="animate-spin rounded-full h-8 w-8"
            style={{ borderBottom: '2px solid var(--color-accent)' }}
          />
          <p className="text-sm" style={{ color: 'var(--color-fg-muted)' }}>
            Loading...
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
