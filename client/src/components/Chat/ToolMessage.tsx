import { useState } from 'react';
import { ChevronDown, Zap } from 'lucide-react';

interface ToolCall {
  id: string;
  name: string;
  args?: Record<string, unknown>;
  result?: string | Record<string, unknown>;
}

interface ToolMessageProps {
  toolCall: ToolCall;
  isLast?: boolean;
}

export function ToolMessage({ toolCall, isLast }: ToolMessageProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const hasResult = !!toolCall.result;

  return (
    <div className="flex gap-3 mb-3">
      <div className="flex flex-col items-center flex-shrink-0">
        <div
          className={`w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-semibold ${
            hasResult ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-border-strong)]'
          }`}
        >
          <Zap size={12} strokeWidth={2} />
        </div>
        {!isLast && (
          <div className="w-px h-6 mt-1 bg-[var(--color-border)]" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className="border rounded overflow-hidden border-[var(--color-border)] bg-[var(--color-surface-overlay)]">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center justify-between gap-2 px-3 py-2.5 border-none bg-transparent cursor-pointer text-left transition-colors hover:bg-[var(--color-surface-raised)]"
          >
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold uppercase flex-shrink-0 font-mono bg-[var(--color-accent-muted)] text-[var(--color-accent)]">
                Tool
              </span>
              <span className="text-xs font-medium overflow-hidden text-ellipsis whitespace-nowrap text-[var(--color-fg-primary)]">
                {toolCall.name}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span
                className="text-xs font-medium"
                style={{ color: hasResult ? 'var(--color-accent)' : 'var(--color-fg-muted)' }}
              >
                {hasResult ? 'Done' : 'Running'}
              </span>
              <ChevronDown
                size={16}
                className="text-[var(--color-fg-muted)] transition-transform"
                style={{
                  transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                }}
              />
            </div>
          </button>

          {isExpanded && (
            <div className="p-3 border-t border-[var(--color-border)] bg-[var(--color-surface-base)]">
              {toolCall.args && Object.keys(toolCall.args).length > 0 && (
                <div className="mb-3">
                  <div className="text-xs font-semibold uppercase mb-1.5 font-mono text-[var(--color-fg-muted)]">
                    Input
                  </div>
                  <pre className="text-xs p-2 rounded overflow-auto font-mono m-0 bg-[var(--color-surface-sunken)] text-[var(--color-fg-secondary)]">
                    {JSON.stringify(toolCall.args, null, 2)}
                  </pre>
                </div>
              )}

              {toolCall.result && (
                <div>
                  <div className="text-xs font-semibold uppercase mb-1.5 font-mono text-[var(--color-fg-muted)]">
                    Output
                  </div>
                  <div className="text-xs p-2 rounded overflow-auto font-mono max-h-80 bg-[var(--color-surface-sunken)] text-[var(--color-fg-secondary)]">
                    {typeof toolCall.result === 'string' ? (
                      toolCall.result
                    ) : (
                      <pre style={{ margin: 0 }}>
                        {JSON.stringify(toolCall.result, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
