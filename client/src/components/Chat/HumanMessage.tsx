import { useState, useRef, useEffect } from 'react';
import { Edit2, Check, Copy, X } from 'lucide-react';
import type { Message } from '@/types';

interface HumanMessageProps {
  message: Message;
  isLast?: boolean;
  onEdit?: (newText: string) => void;
  onCopy?: () => void;
}

export function HumanMessage({ message, isLast, onEdit, onCopy }: HumanMessageProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(message.content);
  const [isCopied, setIsCopied] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      const el = textareaRef.current;
      el.style.height = 'auto';
      el.style.height = `${el.scrollHeight}px`;
      el.focus();
      el.setSelectionRange(el.value.length, el.value.length);
    }
  }, [isEditing]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditText(e.target.value);
    const el = e.currentTarget;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  };

  const handleEditSubmit = () => {
    const trimmed = editText.trim();
    if (trimmed && trimmed !== message.content) {
      onEdit?.(trimmed);
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditText(message.content);
    setIsEditing(false);
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
    onCopy?.();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleEditSubmit();
    }
    if (e.key === 'Escape') {
      handleCancel();
    }
  };

  return (
    <div className="flex justify-end mb-3">
      <div className="group flex flex-col items-end max-w-[78%]">
        <div
          className="px-4 py-3 font-sans text-[15px] leading-[1.55]"
          style={{
            backgroundColor: 'var(--color-accent)',
            color: '#ffffff',
            borderRadius: '18px 18px 4px 18px',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            wordBreak: 'break-word',
          }}
        >
          {isEditing ? (
            <textarea
              ref={textareaRef}
              value={editText}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              className="w-full resize-none bg-transparent border-none outline-none font-sans text-[15px] leading-[1.55]"
              style={{
                minWidth: '240px',
                color: '#ffffff',
                caretColor: '#ffffff',
              }}
              rows={1}
            />
          ) : (
            <div className="whitespace-pre-wrap">{message.content}</div>
          )}
        </div>

        {isEditing ? (
          <div className="flex gap-2 mt-2">
            <button
              onClick={handleEditSubmit}
              title="Save (Enter)"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[13px] font-medium rounded-full text-white transition-colors"
              style={{
                backgroundColor: 'var(--color-accent)',
              }}
            >
              <Check size={14} strokeWidth={2.5} />
              Save
            </button>
            <button
              onClick={handleCancel}
              title="Cancel (Esc)"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[13px] font-medium rounded-full transition-colors hover:bg-[var(--color-surface-overlay)]"
              style={{
                backgroundColor: 'transparent',
                color: 'var(--color-fg-muted)',
              }}
            >
              <X size={14} strokeWidth={2.5} />
              Cancel
            </button>
          </div>
        ) : (
          <div
            className={`flex items-center gap-1 mt-2 transition-opacity ${
              isLast ? 'opacity-100' : 'opacity-60 group-hover:opacity-100'
            }`}
            role="toolbar"
            aria-label="Message actions"
          >
            <button
              onClick={handleCopy}
              title={isCopied ? 'Copied' : 'Copy'}
              aria-label="Copy message"
              className="inline-flex items-center justify-center w-8 h-8 rounded-md transition-colors hover:bg-[var(--color-surface-overlay)]"
              style={{ color: isCopied ? 'var(--color-accent)' : 'var(--color-fg-muted)' }}
            >
              {isCopied ? <Check size={15} strokeWidth={2.25} /> : <Copy size={15} strokeWidth={1.75} />}
            </button>

            {onEdit && (
              <button
                onClick={() => setIsEditing(true)}
                title="Edit"
                aria-label="Edit message"
                className="inline-flex items-center justify-center w-8 h-8 rounded-md transition-colors hover:bg-[var(--color-surface-overlay)]"
                style={{ color: 'var(--color-fg-muted)' }}
              >
                <Edit2 size={15} strokeWidth={1.75} />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
