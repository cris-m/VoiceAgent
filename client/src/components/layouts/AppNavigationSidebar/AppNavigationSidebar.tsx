import { MessageSquareMore, AudioLines, Captions, Music2 } from 'lucide-react';
import { NavLink } from 'react-router';

interface NavItem {
  label: string;
  path: string;
  Icon: React.ComponentType<{ size: number; strokeWidth: number }>;
}

const navItems: NavItem[] = [
  { label: 'Converse', path: '/', Icon: MessageSquareMore },
  { label: 'Narrate', path: '/narrate', Icon: AudioLines },
  { label: 'Transcribe', path: '/transcribe', Icon: Captions },
  { label: 'Beats', path: '/music', Icon: Music2 },
];

export function AppNavigationSidebar() {
  return (
    <div
      style={{
        width: '60px',
        backgroundColor: 'var(--color-surface-raised)',
        borderRight: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        overflow: 'hidden',
      }}
    >
      <nav style={{ flex: 1, padding: '8px 0', display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'center' }}>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            title={item.label}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '44px',
              height: '44px',
              borderRadius: 'var(--radius-md)',
              textDecoration: 'none',
              backgroundColor: isActive ? 'var(--color-accent-muted)' : 'transparent',
              color: isActive ? 'var(--color-accent)' : 'var(--color-fg-secondary)',
              transition: 'background-color 150ms, color 150ms',
              cursor: 'pointer',
              border: 'none',
            })}
            onMouseEnter={(e) => {
              const target = e.currentTarget as HTMLElement;
              const isActive = target.style.backgroundColor === 'var(--color-accent-muted)';
              if (!isActive) {
                target.style.backgroundColor = 'var(--color-surface-overlay)';
                target.style.color = 'var(--color-fg-primary)';
              }
            }}
            onMouseLeave={(e) => {
              const target = e.currentTarget as HTMLElement;
              const isActive = target.style.backgroundColor === 'var(--color-accent-muted)';
              if (!isActive) {
                target.style.backgroundColor = 'transparent';
                target.style.color = 'var(--color-fg-secondary)';
              }
            }}
          >
            <item.Icon size={20} strokeWidth={1.5} />
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
