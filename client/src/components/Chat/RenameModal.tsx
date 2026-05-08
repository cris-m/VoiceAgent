import { useState, useEffect } from 'react';

interface RenameModalProps {
  isOpen: boolean;
  currentName: string;
  onConfirm: (newName: string) => void;
  onClose: () => void;
}

export function RenameModal({
  isOpen,
  currentName,
  onConfirm,
  onClose,
}: RenameModalProps) {
  const [newName, setNewName] = useState(currentName);

  useEffect(() => {
    if (isOpen) {
      setNewName(currentName);
    }
  }, [isOpen, currentName]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newName.trim() && newName !== currentName) {
      onConfirm(newName.trim());
    }
    onClose();
  };

  if (!isOpen) return null;

  const isDisabled = !newName.trim() || newName === currentName;

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
          className="mb-4 text-sm font-semibold"
          style={{ color: 'var(--color-fg-primary)' }}
        >
          Rename conversation
        </h2>

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Enter new name..."
            autoFocus
            className="mb-6 w-full rounded border px-3 py-2 text-xs outline-none transition-colors"
            style={{
              borderColor: 'var(--color-border)',
              backgroundColor: 'var(--color-surface-base)',
              color: 'var(--color-fg-primary)',
            }}
          />

          <div className="flex gap-3">
            <button
              type="button"
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
              type="submit"
              disabled={isDisabled}
              className="flex-1 rounded px-4 py-2 text-xs font-medium text-white transition-colors"
              style={{
                backgroundColor: isDisabled
                  ? 'var(--color-fg-muted)'
                  : 'var(--color-accent)',
                cursor: isDisabled ? 'not-allowed' : 'pointer',
              }}
            >
              Save
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
