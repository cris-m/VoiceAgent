import { useRef, useState, useEffect, memo } from 'react';
import { Plus, Trash2, MoreVertical, Pin, PinOff, Edit } from 'lucide-react';
import type { Thread } from '@langchain/langgraph-sdk';
import type { ThreadMetadata } from '@typing';
import { ConfirmModal, RenameModal } from './index';

interface ThreadHistorySidebarProps {
  threads: Thread[];
  currentThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onCreateThread: () => void;
  updateThreadMetadata: (threadId: string, metadata: Record<string, unknown>) => Promise<boolean>;
  deleteThread: (threadId: string) => Promise<{ success: boolean; switchedToThread: Thread | null }>;
  onPinThread: (threadId: string, currentPinned: boolean) => Promise<void>;
}

function ThreadItem({
  thread,
  isSelected,
  isHovered,
  isPinned,
  onSelect,
  onHoverChange,
  onRenameStart,
  onPin,
  onDelete,
  formatDate,
}: {
  thread: Thread;
  isSelected: boolean;
  isHovered: boolean;
  isPinned: boolean;
  onSelect: () => void;
  onHoverChange: (hovered: boolean) => void;
  onRenameStart: () => void;
  onPin: () => void;
  onDelete: () => void;
  formatDate: (date: Date) => string;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  const threadTitle = (thread.metadata as ThreadMetadata)?.name ?? 'Untitled';
  const threadDate = new Date((thread as unknown as Record<string, unknown>).updated_at as string);

  return (
    <div
      onClick={onSelect}
      onMouseEnter={() => onHoverChange(true)}
      onMouseLeave={() => onHoverChange(false)}
      className={`flex items-center gap-1.5 px-3 py-2 my-0.5 rounded transition-colors cursor-pointer ${
        isSelected ? 'bg-[var(--color-accent-muted)]' : 'bg-transparent'
      }`}
    >
      <div className="flex-1 min-w-0">
        <div
          className="text-xs font-medium overflow-hidden text-ellipsis whitespace-nowrap"
          style={{ color: isSelected ? 'var(--color-accent)' : 'var(--color-fg-primary)' }}
        >
          {String(threadTitle)}
        </div>
        <div className="text-xs mt-0.5 font-mono text-[var(--color-fg-muted)]">
          {formatDate(threadDate)}
        </div>
      </div>

      {(isSelected || isHovered) && (
        <div className="relative flex-shrink-0" ref={menuRef}>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setMenuOpen(!menuOpen);
            }}
            title="Thread options"
            className="w-5.5 h-5.5 flex items-center justify-center rounded border-none bg-[var(--color-surface-sunken)] text-[var(--color-fg-secondary)] cursor-pointer transition-colors hover:bg-[var(--color-border)]"
          >
            <MoreVertical size={12} strokeWidth={1.75} />
          </button>

          {menuOpen && (
            <div
              className="animate-fadeInFast absolute right-0 mt-1 w-32 border rounded shadow-md overflow-hidden z-50"
              style={{
                borderColor: 'var(--color-border)',
                backgroundColor: 'var(--color-surface-raised)',
                boxShadow: 'var(--shadow-md)',
              }}
            >
              {[
                {
                  label: 'Rename',
                  action: () => { onRenameStart(); setMenuOpen(false); },
                  danger: false,
                  amber: false,
                  icon: <Edit size={11} />,
                },
                {
                  label: isPinned ? 'Unpin' : 'Pin',
                  action: async () => { await onPin(); setMenuOpen(false); },
                  danger: false,
                  amber: true,
                  icon: isPinned ? <PinOff size={11} /> : <Pin size={11} />,
                },
                {
                  label: 'Delete',
                  action: async () => { await onDelete(); setMenuOpen(false); },
                  danger: true,
                  amber: false,
                  icon: <Trash2 size={11} />,
                },
              ].map((item, i) => (
                <button
                  key={item.label}
                  onClick={async (e) => {
                    e.stopPropagation();
                    await item.action();
                  }}
                  className={`w-full text-left px-3 py-1.75 text-xs font-medium border-none bg-transparent cursor-pointer flex items-center gap-1.5 transition-colors hover:bg-[var(--color-surface-overlay)] ${
                    i > 0 ? 'border-t' : ''
                  }`}
                  style={{
                    color: item.danger ? 'var(--color-danger)' : item.amber ? 'var(--color-warning)' : 'var(--color-fg-primary)',
                    borderTopColor: i > 0 ? 'var(--color-border)' : 'transparent',
                  }}
                >
                  {item.icon}
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ThreadHistorySidebarComponent({
  threads,
  currentThreadId,
  onSelectThread,
  onCreateThread,
  updateThreadMetadata,
  deleteThread,
  onPinThread,
}: ThreadHistorySidebarProps) {
  const [hoveredThreadId, setHoveredThreadId] = useState<string | null>(null);
  const [renamingThread, setRenamingThread] = useState<Thread | null>(null);
  const [deletingThread, setDeletingThread] = useState<Thread | null>(null);

  const formatDate = (date: Date): string => {
    const d = new Date(date);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;

    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const pinnedThreads = threads.filter(t => (t.metadata as ThreadMetadata)?.pinned === true);
  const regularThreads = threads.filter(t => (t.metadata as ThreadMetadata)?.pinned !== true);

  const renderThreadsList = (threadList: Thread[], isPinnedList: boolean) => {
    if (threadList.length === 0) return null;

    return (
      <div>
        {isPinnedList && threadList.length > 0 && (
          <div className="flex items-center gap-1.5 px-3 pt-2 pb-1 font-mono text-xs font-semibold uppercase tracking-tighter text-[var(--color-fg-muted)]">
            <Pin size={10} />
            Pinned
          </div>
        )}
        {threadList.map((thread) => (
          <ThreadItem
            key={thread.thread_id}
            thread={thread}
            isSelected={currentThreadId === thread.thread_id}
            isHovered={hoveredThreadId === thread.thread_id}
            isPinned={(thread.metadata as ThreadMetadata)?.pinned === true}
            onSelect={() => onSelectThread(thread.thread_id)}
            onHoverChange={(hovered) => setHoveredThreadId(hovered ? thread.thread_id : null)}
            onRenameStart={() => setRenamingThread(thread)}
            onPin={() => onPinThread(thread.thread_id, (thread.metadata as ThreadMetadata)?.pinned === true)}
            onDelete={() => setDeletingThread(thread)}
            formatDate={formatDate}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="flex flex-col w-60 h-full bg-[var(--color-surface-base)] border-r border-[var(--color-border)]">
      <div className="px-3 py-3 border-b flex-shrink-0 border-[var(--color-border)]">
        <div className="text-xs font-semibold uppercase tracking-widest text-[var(--color-fg-muted)] font-mono">
          THREADS
        </div>
      </div>

      <div className="flex-shrink-0 px-3 py-3 border-b border-[var(--color-border)]">
        <button
          onClick={onCreateThread}
          className="w-full flex items-center justify-center gap-1.5 px-3 py-2 border rounded transition-colors bg-[var(--color-surface-base)] text-[var(--color-fg-secondary)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)] font-sans text-xs font-medium cursor-pointer border-[var(--color-border)]"
        >
          <Plus size={14} strokeWidth={2} />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {threads.length === 0 ? (
          <div className="px-4 py-8 text-center font-mono text-xs text-[var(--color-fg-muted)]">
            No conversations yet
          </div>
        ) : (
          <div>
            {renderThreadsList(pinnedThreads, true)}
            {pinnedThreads.length > 0 && regularThreads.length > 0 && (
              <div className="px-3 pt-2 pb-1 font-mono text-xs font-semibold uppercase tracking-tighter text-[var(--color-fg-muted)]">
                Recent
              </div>
            )}
            {renderThreadsList(regularThreads, false)}
          </div>
        )}
      </div>

      {threads.length > 0 && (
        <div className="flex-shrink-0 px-3 py-2 border-t border-[var(--color-border)] font-mono text-xs text-[var(--color-fg-muted)] bg-[var(--color-surface-base)]">
          {threads.length} conversation{threads.length !== 1 ? 's' : ''}
        </div>
      )}

      <RenameModal
        isOpen={renamingThread !== null}
        currentName={(renamingThread?.metadata as ThreadMetadata)?.name ?? 'Untitled'}
        onClose={() => setRenamingThread(null)}
        onConfirm={async (name) => {
          if (renamingThread) {
            await updateThreadMetadata(renamingThread.thread_id, { name });
            setRenamingThread(null);
          }
        }}
      />

      <ConfirmModal
        isOpen={deletingThread !== null}
        title="Delete conversation?"
        message={`"${(deletingThread?.metadata as ThreadMetadata)?.name ?? 'Untitled'}" will be permanently deleted.`}
        confirmLabel="Delete"
        danger
        onClose={() => setDeletingThread(null)}
        onConfirm={async () => {
          if (deletingThread) {
            await deleteThread(deletingThread.thread_id);
            setDeletingThread(null);
          }
        }}
      />
    </div>
  );
}

export const ThreadHistorySidebar = memo(ThreadHistorySidebarComponent);
