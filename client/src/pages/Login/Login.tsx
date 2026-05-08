import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router';
import { useSelector } from 'react-redux';
import { useLoginMutation } from '@/services/auth';
import { authSelectors } from '@/features/auth';
import { Alert } from '@/components/Alert';
import { LoginSchema } from '@/schemas/auth';
import { ZodError } from 'zod';
import type { RootState } from '@/store/store';
import type { NormalizedError } from '@/types/errors';

export function Login() {
  const navigate = useNavigate();
  const [login, { isLoading, error }] = useLoginMutation();
  const isAuthenticated = useSelector((state: RootState) =>
    authSelectors.selectIsAuthenticated(state)
  );

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [clientErrors, setClientErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLocalError(null);
    setClientErrors({});

    try {
      LoginSchema.parse({ username, password });
    } catch (err) {
      if (err instanceof ZodError) {
        const fieldErrors: Record<string, string> = {};
        const flattened = err.flatten();
        if (flattened.fieldErrors) {
          const entries = Object.entries(flattened.fieldErrors) as [
            string,
            string[] | undefined,
          ][];
          entries.forEach(([field, messages]) => {
            if (messages && messages.length > 0) {
              fieldErrors[field] = messages[0];
            }
          });
        }
        setClientErrors(fieldErrors);
        return;
      }
    }

    try {
      await login({ username, password }).unwrap();

      if (rememberMe) {
        localStorage.setItem('auth_remember', 'true');
      } else {
        localStorage.removeItem('auth_remember');
      }

      navigate('/');
    } catch {
      // Error is already in RTK Query state
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ backgroundColor: 'var(--color-surface-base)' }}
    >
      <div className="w-full max-w-sm">
        <div
          className="rounded-lg p-8"
          style={{
            backgroundColor: 'var(--color-surface-raised)',
            border: '1px solid var(--color-border)',
          }}
        >
          <div className="mb-7">
            <h1
              className="text-xl font-semibold"
              style={{ color: 'var(--color-fg-primary)' }}
            >
              Sign in
            </h1>
            <p className="mt-1 text-sm" style={{ color: 'var(--color-fg-muted)' }}>
              Don't have an account?{' '}
              <Link
                to="/register"
                className="font-medium"
                style={{ color: 'var(--color-accent)' }}
              >
                Create one
              </Link>
            </p>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            {(() => {
              const apiError = error as NormalizedError | undefined;
              const hasFieldErrors =
                apiError?.error?.fields && Object.keys(apiError.error.fields).length > 0;
              if (!hasFieldErrors && (apiError || localError)) {
                return (
                  <Alert
                    type="error"
                    message={apiError?.error?.message ?? localError ?? 'Login failed'}
                  />
                );
              }
              return null;
            })()}

            {(() => {
              const apiError = error as NormalizedError | undefined;
              const usernameErr = clientErrors.username || apiError?.error?.fields?.username?.[0];
              const passwordErr = clientErrors.password || apiError?.error?.fields?.password?.[0];

              return (
                <>
                  <div>
                    <label
                      htmlFor="username"
                      className="block text-sm font-medium mb-1.5"
                      style={{ color: 'var(--color-fg-secondary)' }}
                    >
                      Username
                    </label>
                    <input
                      id="username"
                      type="text"
                      autoComplete="username"
                      placeholder="Enter your username"
                      value={username}
                      onChange={(e) => {
                        setUsername(e.target.value);
                        if (clientErrors.username) {
                          setClientErrors({ ...clientErrors, username: '' });
                        }
                      }}
                      className="w-full px-3 py-2 text-sm rounded-md transition-colors focus:outline-none"
                      style={{
                        backgroundColor: usernameErr
                          ? 'var(--color-danger-muted)'
                          : 'var(--color-surface-sunken)',
                        border: `1px solid ${usernameErr ? 'var(--color-danger)' : 'var(--color-border)'}`,
                        color: 'var(--color-fg-primary)',
                      }}
                    />
                    {usernameErr && (
                      <p className="mt-1 text-xs" style={{ color: 'var(--color-danger)' }}>
                        {usernameErr}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="password"
                      className="block text-sm font-medium mb-1.5"
                      style={{ color: 'var(--color-fg-secondary)' }}
                    >
                      Password
                    </label>
                    <input
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (clientErrors.password) {
                          setClientErrors({ ...clientErrors, password: '' });
                        }
                      }}
                      className="w-full px-3 py-2 text-sm rounded-md transition-colors focus:outline-none"
                      style={{
                        backgroundColor: passwordErr
                          ? 'var(--color-danger-muted)'
                          : 'var(--color-surface-sunken)',
                        border: `1px solid ${passwordErr ? 'var(--color-danger)' : 'var(--color-border)'}`,
                        color: 'var(--color-fg-primary)',
                      }}
                    />
                    {passwordErr && (
                      <p className="mt-1 text-xs" style={{ color: 'var(--color-danger)' }}>
                        {passwordErr}
                      </p>
                    )}
                  </div>
                </>
              );
            })()}

            <label
              className="flex items-center gap-2 text-sm cursor-pointer"
              style={{ color: 'var(--color-fg-secondary)' }}
            >
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="rounded"
                style={{ accentColor: 'var(--color-accent)' }}
              />
              Remember me
            </label>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2 px-4 text-sm font-medium rounded-md text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: 'var(--color-accent)' }}
              onMouseEnter={(e) => {
                if (!isLoading) e.currentTarget.style.backgroundColor = 'var(--color-accent-dim)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-accent)';
              }}
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
