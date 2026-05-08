import React from 'react';
import { AlertCircle, CheckCircle, AlertTriangle, Info, X } from 'lucide-react';
import type { AlertProps } from './types';

const alertColors = {
  error:   { bg: 'var(--color-danger-muted)',  border: 'var(--color-danger)',  fg: 'var(--color-danger)'  },
  success: { bg: 'var(--color-success-muted)', border: 'var(--color-success)', fg: 'var(--color-success)' },
  warning: { bg: 'var(--color-warning-muted)', border: 'var(--color-warning)', fg: 'var(--color-warning)' },
  info:    { bg: 'var(--color-accent-muted)',  border: 'var(--color-accent)',  fg: 'var(--color-accent)'  },
} as const;

const icons = {
  error: AlertCircle,
  success: CheckCircle,
  warning: AlertTriangle,
  info: Info,
};

export function Alert({
  type,
  message,
  onClose,
  autoClose = false,
  autoCloseDuration = 5000,
}: AlertProps) {
  const palette = alertColors[type];
  const Icon = icons[type];

  React.useEffect(() => {
    if (!autoClose || !onClose) return;
    const timer = setTimeout(onClose, autoCloseDuration);
    return () => clearTimeout(timer);
  }, [autoClose, autoCloseDuration, onClose]);

  return (
    <div
      className="flex items-start gap-3 p-4 rounded-md"
      style={{
        backgroundColor: palette.bg,
        border: `1px solid ${palette.border}`,
      }}
    >
      <Icon className="flex-shrink-0 w-5 h-5 mt-0.5" style={{ color: palette.fg }} />
      <p className="text-sm font-medium flex-1" style={{ color: palette.fg }}>
        {message}
      </p>
      {onClose && (
        <button
          onClick={onClose}
          className="flex-shrink-0 transition-colors"
          style={{ color: palette.fg }}
          aria-label="Close alert"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}
