import { Outlet } from 'react-router';
import { AppNavigationSidebar } from '../AppNavigationSidebar';

export function MainLayout() {
  return (
    <div
      className="h-screen flex overflow-hidden font-sans"
      style={{
        backgroundColor: 'var(--color-surface-base)',
        color: 'var(--color-fg-primary)',
      }}
    >
      <AppNavigationSidebar />
      <main className="flex-1 min-w-0 flex overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
