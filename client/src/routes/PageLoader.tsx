
export function PageLoader() {
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
