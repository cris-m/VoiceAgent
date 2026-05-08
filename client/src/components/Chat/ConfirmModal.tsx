import { useEffect } from 'react';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmModal({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  danger = false,
  onConfirm,
  onClose,
}: ConfirmModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div
        className="max-w-sm rounded-lg p-6 border"
        style={{
          backgroundColor: 'var(--color-surface-raised)',
          borderColor: 'var(--color-border)',
        }}
      >
        <h2
          className="mb-2 text-sm font-semibold"
          style={{ color: 'var(--color-fg-primary)' }}
        >
          {title}
        </h2>
        <p
          className="mb-6 text-xs"
          style={{ color: 'var(--color-fg-secondary)' }}
        >
          {message}
        </p>

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 rounded px-4 py-2 text-xs font-medium border transition-colors"
            style={{
              borderColor: 'var(--color-border)',
              color: 'var(--color-fg-secondary)',
              backgroundColor: 'var(--color-surface-base)',
            }}
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className="flex-1 rounded px-4 py-2 text-xs font-medium text-white transition-colors"
            style={{
              backgroundColor: danger
                ? 'var(--color-danger)'
                : 'var(--color-accent)',
            }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
