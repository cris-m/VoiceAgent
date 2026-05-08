import { lazy, Suspense, Component } from 'react';
import type { ReactNode } from 'react';
import type { RouteObject } from 'react-router';
import { MainLayout, ConverseLayout } from '@components/layouts';
import { ConversePage } from '@/pages';
import { Login } from '@/pages/Login';
import { Register } from '@/pages/Register';
import { ProtectedRoute } from '@components/ProtectedRoute';

const TranscribePage = lazy(() =>
  import('@/pages/Transcribe').then(mod => ({ default: mod.TranscribePage }))
);
const NarratePage = lazy(() =>
  import('@/pages/Narrate').then(mod => ({ default: mod.NarratePage }))
);
const MusicPage = lazy(() =>
  import('@/pages/Music').then(mod => ({ default: mod.MusicPage }))
);

function PageLoader() {
  // The route Outlet is rendered inside MainLayout's `<main>` which is a
  // horizontal flexbox. Without `flex-1` the spinner has no width and
  // hugs the left edge; without `self-stretch` (or h-full) it has no
  // height and the centering math collapses. Belt and suspenders: also
  // set min-h-screen so it fills the viewport even if the parent ever
  // gets reorganized.
  return (
    <div
      className="flex-1 self-stretch flex items-center justify-center min-h-screen bg-[var(--color-surface-base)]"
      role="status"
      aria-live="polite"
    >
      <div className="text-center">
        <div
          className="animate-spin rounded-full h-8 w-8 border-2 border-[var(--color-border)] border-t-[var(--color-accent)] mx-auto mb-4"
          aria-hidden="true"
        />
        <p className="text-sm text-[var(--color-fg-muted)] font-mono">Loading page…</p>
      </div>
    </div>
  );
}

interface ChunkErrorBoundaryState {
  hasError: boolean;
}

class ChunkErrorBoundary extends Component<{ children: ReactNode }, ChunkErrorBoundaryState> {
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

export const routes: RouteObject[] = [
  {
    path: 'login',
    element: <Login />,
  },
  {
    path: 'register',
    element: <Register />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        element: <ConverseLayout />,
        children: [
          {
            index: true,
            element: <ConversePage />,
          },
          {
            path: 'thread/:threadId',
            element: <ConversePage />,
          },
        ],
      },
      {
        path: 'transcribe',
        element: (
          <ChunkErrorBoundary>
            <Suspense fallback={<PageLoader />}>
              <TranscribePage />
            </Suspense>
          </ChunkErrorBoundary>
        ),
      },
      {
        path: 'narrate',
        element: (
          <ChunkErrorBoundary>
            <Suspense fallback={<PageLoader />}>
              <NarratePage />
            </Suspense>
          </ChunkErrorBoundary>
        ),
      },
      {
        path: 'music',
        element: (
          <ChunkErrorBoundary>
            <Suspense fallback={<PageLoader />}>
              <MusicPage />
            </Suspense>
          </ChunkErrorBoundary>
        ),
      },
    ],
  },
];
