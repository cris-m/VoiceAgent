import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router';
import { useSelector } from 'react-redux';
import { useRegisterMutation } from '@/services/auth';
import { authSelectors } from '@/features/auth';
import { Alert } from '@/components/Alert';
import { RegisterSchema } from '@/schemas/auth';
import { ZodError } from 'zod';
import type { RootState } from '@/store/store';
import type { NormalizedError } from '@/types/errors';

export function Register() {
  const navigate = useNavigate();
  const [register, { isLoading, error }] = useRegisterMutation();
  const isAuthenticated = useSelector((state: RootState) =>
    authSelectors.selectIsAuthenticated(state)
  );

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
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
      RegisterSchema.parse({ username, email, password, confirmPassword });
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
      await register({ username, email, password }).unwrap();
      navigate('/');
    } catch {
      // Error is already in RTK Query state
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-12"
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
              Create account
            </h1>
            <p className="mt-1 text-sm" style={{ color: 'var(--color-fg-muted)' }}>
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-medium"
                style={{ color: 'var(--color-accent)' }}
              >
                Sign in
              </Link>
            </p>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            {(() => {
              const apiError = error as NormalizedError | undefined;
              const hasFieldErrors =
                apiError?.error?.fields && Object.keys(apiError.error.fields).length > 0;
              if (!hasFieldErrors && (apiError || localError)) {
                return (
                  <Alert
                    type="error"
                    message={apiError?.error?.message ?? localError ?? 'Registration failed'}
                  />
                );
              }
              return null;
            })()}

            {(() => {
              const apiError = error as NormalizedError | undefined;
              const usernameErr = clientErrors.username || apiError?.error?.fields?.username?.[0];
              const emailErr = clientErrors.email || apiError?.error?.fields?.email?.[0];
              const passwordErr = clientErrors.password || apiError?.error?.fields?.password?.[0];
              const confirmPasswordErr =
                clientErrors.confirmPassword || apiError?.error?.fields?.confirmPassword?.[0];

              const fieldStyle = (hasErr: boolean) => ({
                backgroundColor: hasErr ? 'var(--color-danger-muted)' : 'var(--color-surface-sunken)',
                border: `1px solid ${hasErr ? 'var(--color-danger)' : 'var(--color-border)'}`,
                color: 'var(--color-fg-primary)',
              });

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
                      placeholder="Minimum 3 characters"
                      value={username}
                      onChange={(e) => {
                        setUsername(e.target.value);
                        if (clientErrors.username) setClientErrors({ ...clientErrors, username: '' });
                      }}
                      className="w-full px-3 py-2 text-sm rounded-md transition-colors focus:outline-none"
                      style={fieldStyle(!!usernameErr)}
                    />
                    {usernameErr && (
                      <p className="mt-1 text-xs" style={{ color: 'var(--color-danger)' }}>
                        {usernameErr}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="email"
                      className="block text-sm font-medium mb-1.5"
                      style={{ color: 'var(--color-fg-secondary)' }}
                    >
                      Email address
                    </label>
                    <input
                      id="email"
                      type="email"
                      autoComplete="email"
                      placeholder="your.email@example.com"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        if (clientErrors.email) setClientErrors({ ...clientErrors, email: '' });
                      }}
                      className="w-full px-3 py-2 text-sm rounded-md transition-colors focus:outline-none"
                      style={fieldStyle(!!emailErr)}
                    />
                    {emailErr && (
                      <p className="mt-1 text-xs" style={{ color: 'var(--color-danger)' }}>
                        {emailErr}
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
                      autoComplete="new-password"
                      placeholder="At least 8 characters"
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        if (clientErrors.password) setClientErrors({ ...clientErrors, password: '' });
                      }}
                      className="w-full px-3 py-2 text-sm rounded-md transition-colors focus:outline-none"
                      style={fieldStyle(!!passwordErr)}
                    />
                    {passwordErr && (
                      <p className="mt-1 text-xs" style={{ color: 'var(--color-danger)' }}>
                        {passwordErr}
                      </p>
                    )}
                  </div>

                  <div>
                    <label
                      htmlFor="confirmPassword"
                      className="block text-sm font-medium mb-1.5"
                      style={{ color: 'var(--color-fg-secondary)' }}
                    >
                      Confirm password
                    </label>
                    <input
                      id="confirmPassword"
                      type="password"
                      autoComplete="new-password"
                      placeholder="Confirm your password"
                      value={confirmPassword}
                      onChange={(e) => {
                        setConfirmPassword(e.target.value);
                        if (clientErrors.confirmPassword)
                          setClientErrors({ ...clientErrors, confirmPassword: '' });
                      }}
                      className="w-full px-3 py-2 text-sm rounded-md transition-colors focus:outline-none"
                      style={fieldStyle(!!confirmPasswordErr)}
                    />
                    {confirmPasswordErr && (
                      <p className="mt-1 text-xs" style={{ color: 'var(--color-danger)' }}>
                        {confirmPasswordErr}
                      </p>
                    )}
                  </div>
                </>
              );
            })()}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2 px-4 text-sm font-medium rounded-md text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-2"
              style={{ backgroundColor: 'var(--color-accent)' }}
              onMouseEnter={(e) => {
                if (!isLoading) e.currentTarget.style.backgroundColor = 'var(--color-accent-dim)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--color-accent)';
              }}
            >
              {isLoading ? 'Creating account...' : 'Create account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
