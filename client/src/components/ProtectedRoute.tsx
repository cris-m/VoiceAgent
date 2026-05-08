import type { ReactNode } from 'react';
import { Navigate } from 'react-router';
import { useSelector } from 'react-redux';
import { authSelectors } from '@/features/auth';
import type { RootState } from '@/store/store';

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useSelector((state: RootState) =>
    authSelectors.selectIsAuthenticated(state)
  );

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
