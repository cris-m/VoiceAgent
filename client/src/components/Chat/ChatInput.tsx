import { useRef, useEffect, useState } from 'react';
import { ArrowUp, AudioLines, Plus } from 'lucide-react';

interface ChatInputProps {
  onSend: (text: string) => void;
  onVoiceToggle?: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Type a message...',
  onVoiceToggle,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [input, setInput] = useState('');

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, 200);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, [input]);

  const handleSend = () => {
    const text = input.trim();
    if (text && !disabled) {
      onSend(text);
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasInput = input.trim().length > 0;

  return (
    <div className="max-w-3xl mx-auto w-full px-4">
      <input ref={fileInputRef} type="file" multiple className="hidden" />

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="border rounded-lg transition-colors bg-[var(--color-surface-raised)] border-[var(--color-border-strong)] focus-within:border-[var(--color-accent)]"
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          className="w-full px-3.5 py-3 bg-transparent border-none outline-none resize-none font-mono text-sm leading-relaxed text-[var(--color-fg-primary)] min-h-11 max-h-52 block"
          style={{ opacity: disabled ? 0.5 : 1 }}
          rows={1}
        />

        <div className="flex items-center justify-between px-2.5 py-2 border-t border-[var(--color-border)]">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            title="Attach file"
            aria-label="Attach file"
            className="w-8 h-8 flex items-center justify-center border-none rounded bg-transparent transition-colors cursor-pointer hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-fg-primary)]"
            style={{
              color: disabled ? 'var(--color-fg-muted)' : 'var(--color-fg-secondary)',
              cursor: disabled ? 'not-allowed' : 'pointer',
            }}
          >
            <Plus size={16} strokeWidth={1.75} />
          </button>

          <div className="flex items-center gap-1">
            {onVoiceToggle && (
              <button
                type="button"
                onClick={onVoiceToggle}
                disabled={disabled}
                title="Switch to voice mode"
                aria-label="Switch to voice mode"
                className="w-8 h-8 flex items-center justify-center border-none rounded bg-transparent transition-colors"
                style={{
                  color: disabled ? 'var(--color-fg-muted)' : 'var(--color-accent)',
                  cursor: disabled ? 'not-allowed' : 'pointer',
                }}
                onMouseEnter={(e) => {
                  if (!disabled) e.currentTarget.style.backgroundColor = 'var(--color-accent-muted)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <AudioLines size={16} strokeWidth={1.75} />
              </button>
            )}

            <button
              type="submit"
              disabled={disabled || !hasInput}
              title="Send (Enter)"
              aria-label="Send message"
              className="w-8 h-8 flex items-center justify-center border-none rounded transition-colors"
              style={{
                backgroundColor: hasInput && !disabled ? 'var(--color-accent)' : 'var(--color-surface-overlay)',
                color: hasInput && !disabled ? '#ffffff' : 'var(--color-fg-muted)',
                cursor: hasInput && !disabled ? 'pointer' : 'not-allowed',
              }}
              onMouseEnter={(e) => {
                if (hasInput && !disabled) {
                  e.currentTarget.style.backgroundColor = 'var(--color-accent-dim)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = hasInput && !disabled
                  ? 'var(--color-accent)'
                  : 'var(--color-surface-overlay)';
              }}
            >
              <ArrowUp size={16} strokeWidth={2.5} />
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
