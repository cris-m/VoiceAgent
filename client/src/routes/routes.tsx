import { lazy, Suspense } from 'react';
import type { RouteObject } from 'react-router';
import { MainLayout, ConverseLayout } from '@components/layouts';
import { ConversePage } from '@/pages';
import { Login } from '@/pages/Login';
import { Register } from '@/pages/Register';
import { ProtectedRoute } from '@components/ProtectedRoute';
import { ChunkErrorBoundary } from './ChunkErrorBoundary';
import { PageLoader } from './PageLoader';

const TranscribePage = lazy(() =>
  import('@/pages/Transcribe').then(mod => ({ default: mod.TranscribePage }))
);
const NarratePage = lazy(() =>
  import('@/pages/Narrate').then(mod => ({ default: mod.NarratePage }))
);
const MusicPage = lazy(() =>
  import('@/pages/Music').then(mod => ({ default: mod.MusicPage }))
);

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
