import { Component } from 'react';
import type { ReactNode } from 'react';

interface ChunkErrorBoundaryState {
  hasError: boolean;
}

export class ChunkErrorBoundary extends Component<{ children: ReactNode }, ChunkErrorBoundaryState> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error) {
    if (error.name === 'ChunkLoadError' || error.message.includes('Failed to fetch')) {
      window.location.reload();
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-[var(--color-surface-base)]">
          <div className="text-center max-w-sm">
            <p className="text-sm text-[var(--color-danger)] font-mono mb-3">
              A new version is available. Reloading...
            </p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
