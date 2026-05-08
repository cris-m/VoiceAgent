import React from 'react';
import type { ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  resetError = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '100vh',
              backgroundColor: 'var(--color-surface-base)',
            }}
          >
            <div style={{ textAlign: 'center', padding: '40px 32px', maxWidth: '400px' }}>
              <AlertTriangle
                size={36}
                style={{ color: 'var(--color-danger)', margin: '0 auto 20px' }}
              />
              <h1
                style={{
                  fontFamily: 'var(--font-sans)',
                  fontSize: '18px',
                  fontWeight: 600,
                  color: 'var(--color-fg-primary)',
                  marginBottom: '8px',
                }}
              >
                Something went wrong
              </h1>
              <p
                style={{
                  fontFamily: 'var(--font-sans)',
                  fontSize: '14px',
                  color: 'var(--color-fg-secondary)',
                  marginBottom: '24px',
                  lineHeight: 1.5,
                }}
              >
                {this.state.error?.message || 'An unexpected error occurred'}
              </p>
              <button
                onClick={this.resetError}
                style={{
                  padding: '8px 20px',
                  border: '1px solid var(--color-accent)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--color-accent)',
                  color: '#ffffff',
                  fontFamily: 'var(--font-sans)',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'background-color 150ms',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--color-accent-dim)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--color-accent)';
                }}
              >
                Try Again
              </button>
            </div>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
