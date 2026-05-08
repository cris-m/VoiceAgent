import { useState, useRef, useEffect, memo } from 'react';
import { Copy, RotateCcw, Check, Volume2, Zap } from 'lucide-react';
import { useVoiceConfig } from '@context/VoiceConfigContext';
import { usePreviewVoiceMutation } from '@/services/voice';
import type { Message } from '@/types';

interface Segment {
  type: 'code-block' | 'text';
  content: string;
  lang?: string;
}

function tokenise(raw: string): Segment[] {
  const segments: Segment[] = [];
  const FENCE = /```([^\n`]*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = FENCE.exec(raw)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: raw.slice(lastIndex, match.index) });
    }
    segments.push({ type: 'code-block', lang: match[1].trim() || undefined, content: match[2] });
    lastIndex = FENCE.lastIndex;
  }

  if (lastIndex < raw.length) {
    segments.push({ type: 'text', content: raw.slice(lastIndex) });
  }

  return segments;
}

interface MarkdownProps {
  content: string;
  isStreaming: boolean;
}

function MarkdownContent({ content, isStreaming }: MarkdownProps) {
  const segments = tokenise(content);

  return (
    <div className="font-sans text-sm leading-relaxed text-[var(--color-fg-primary)]">
      {segments.map((seg, idx) => {
        const isLast = idx === segments.length - 1;

        if (seg.type === 'code-block') {
          return (
            <div key={idx} className="my-3 border rounded overflow-hidden border-[var(--color-border)]">
              {seg.lang && (
                <div className="px-3 py-1 text-xs font-mono uppercase tracking-widest border-b bg-[var(--color-surface-overlay)] text-[var(--color-fg-muted)] border-[var(--color-border)]">
                  {seg.lang}
                </div>
              )}
              <pre className="p-4 m-0 overflow-x-auto text-xs leading-relaxed font-mono bg-[var(--color-surface-sunken)] text-[var(--color-fg-primary)]">
                <code>{seg.content}</code>
                {isLast && isStreaming && (
                  <span className="animate-caretBlink ml-0.5">|</span>
                )}
              </pre>
            </div>
          );
        }

        const lines = seg.content.split('\n');
        return (
          <span key={idx}>
            {lines.map((line, li) => (
              <span key={li}>{line}{li < lines.length - 1 && <br />}</span>
            ))}
            {isLast && isStreaming && (
              <span className="animate-caretBlink">|</span>
            )}
          </span>
        );
      })}

      {segments.length === 0 && isStreaming && (
        <span className="animate-caretBlink">|</span>
      )}
    </div>
  );
}

interface AIMessageProps {
  message: Message;
  isLast?: boolean;
  onCopy?: () => void;
  onRetry?: () => void;
}

function AIMessageComponent({ message, isLast, onCopy, onRetry }: AIMessageProps) {
  const [isCopied, setIsCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [speakError, setSpeakError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const errorTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { selectedVoiceId } = useVoiceConfig();
  const [previewVoice] = usePreviewVoiceMutation();

  useEffect(() => {
    return () => {
      if (errorTimeoutRef.current) clearTimeout(errorTimeoutRef.current);
    };
  }, []);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
    onCopy?.();
  };

  const handleSpeak = async () => {
    if (isSpeaking) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      setIsSpeaking(false);
      return;
    }

    setIsLoadingAudio(true);
    setIsSpeaking(true);

    try {
      const meta = await previewVoice({
        text: message.content,
        voice_id: selectedVoiceId || '',
        language: 'auto',
        speed: 1.0,
      }).unwrap();

      audioRef.current?.pause();
      const audio = new Audio(meta.url);
      audioRef.current = audio;

      audio.onended = () => setIsSpeaking(false);
      audio.onerror = () => {
        setIsSpeaking(false);
        setIsLoadingAudio(false);
        setSpeakError('Failed to play audio');
        if (errorTimeoutRef.current) clearTimeout(errorTimeoutRef.current);
        errorTimeoutRef.current = setTimeout(() => setSpeakError(null), 4000);
      };

      setIsLoadingAudio(false);
      await audio.play();
    } catch (error) {
      setIsSpeaking(false);
      setIsLoadingAudio(false);
      const msg = error instanceof Error ? error.message : String(error);
      setSpeakError(`Speech API failed: ${msg}`);
      if (errorTimeoutRef.current) clearTimeout(errorTimeoutRef.current);
      errorTimeoutRef.current = setTimeout(() => setSpeakError(null), 4000);
    }
  };

  return (
    <div className="flex gap-3 mb-2 group justify-start w-full">
      <div className="flex-1 flex flex-col">
        <MarkdownContent content={message.content} isStreaming={!!message.isStreaming} />

        {!message.isStreaming && (
          <div
            className={`flex items-center justify-between gap-3 mt-2.5 transition-opacity ${
              isLast ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
            }`}
            role="toolbar"
            aria-label="Message actions"
          >
            <div className="flex items-center gap-3.5">
              <button
                onClick={handleCopy}
                title={isCopied ? 'Copied!' : 'Copy message'}
                className="inline-flex items-center justify-center transition-colors cursor-pointer hover:opacity-70"
                style={{ color: isCopied ? 'var(--color-accent)' : 'var(--color-fg-muted)' }}
              >
                {isCopied ? <Check size={16} /> : <Copy size={16} />}
              </button>

              {isLoadingAudio ? (
                <span className="inline-flex items-center justify-center text-[var(--color-fg-muted)]">
                  <span
                    className="w-3 h-3 rounded-full border border-solid inline-block animate-spin"
                    style={{
                      borderColor: 'var(--color-border-strong)',
                      borderTopColor: 'var(--color-accent)',
                    }}
                  />
                </span>
              ) : (
                <button
                  onClick={handleSpeak}
                  disabled={!message.content}
                  title={isSpeaking ? 'Stop speaking' : 'Read aloud'}
                  className="inline-flex items-center justify-center transition-colors cursor-pointer hover:opacity-70 disabled:opacity-40 disabled:cursor-default"
                  style={{ color: isSpeaking ? 'var(--color-danger)' : 'var(--color-fg-muted)' }}
                >
                  <Volume2 size={16} />
                </button>
              )}

              {onRetry && (
                <button
                  onClick={onRetry}
                  title="Retry"
                  className="inline-flex items-center justify-center text-[var(--color-fg-muted)] transition-colors cursor-pointer hover:opacity-70"
                >
                  <RotateCcw size={16} />
                </button>
              )}
            </div>

            <div className="flex items-center gap-3 text-xs text-[var(--color-fg-muted)] ml-auto">
              {message.tokenCount !== undefined && (
                <div className="flex items-center gap-1.5" title="Token count for this message">
                  <Zap size={12} />
                  <span>{message.tokenCount} tokens</span>
                </div>
              )}
              {message.elapsedMs !== undefined && (
                <span title="Time to generate this message">
                  {(message.elapsedMs / 1000).toFixed(2)}s
                </span>
              )}
            </div>
          </div>
        )}

        {speakError && (
          <div className="mt-2 px-2.5 py-1.5 rounded text-xs font-medium bg-[var(--color-danger)]/10 text-[var(--color-danger)] border border-[var(--color-danger)]/30">
            {speakError}
          </div>
        )}
      </div>
    </div>
  );
}

export const AIMessage = memo(AIMessageComponent);
