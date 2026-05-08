import { useEffect, useMemo, useRef, memo } from 'react';
import {
  Sparkles, MessageSquare, Mic, Lightbulb, Zap,
  Code2, BookOpen, BrainCircuit, Compass, Map, Music, ChefHat,
  PenLine, Globe2, GraduationCap, Briefcase, HeartPulse, FlaskConical,
  Plane, DollarSign, Languages, Palette,
} from 'lucide-react';
import { AIMessage } from './AIMessage';
import { HumanMessage } from './HumanMessage';
import { ToolMessage } from './ToolMessage';
import type { Message } from '@/types';

interface ChatPanelProps {
  messages: Message[];
  /** Backed by LangGraph SDK's useStream().isLoading — true while the
   *  agent is actively producing a response (network in flight, or
   *  tokens still streaming). When true and the last message is from
   *  the user, we show a typing indicator to signal "agent is working". */
  isStreaming?: boolean;
  onEditMessage?: (messageId: string, newText: string) => void;
  onRetryMessage?: (messageId: string) => void;
  /** Optional handler to fire a suggested prompt straight into the chat input. */
  onSuggestPrompt?: (prompt: string) => void;
}

const PROMPT_POOL: { icon: typeof Lightbulb; label: string; prompt: string }[] = [
  { icon: Lightbulb,     label: 'Explain quantum entanglement',    prompt: 'Explain quantum entanglement in simple terms.' },
  { icon: BrainCircuit,  label: 'How does an LLM actually work?',  prompt: 'Explain how a transformer-based LLM actually works, step by step.' },
  { icon: Zap,           label: 'Brainstorm a startup idea',       prompt: 'Help me brainstorm a startup idea in the AI productivity space.' },
  { icon: Briefcase,     label: 'Critique my business plan',       prompt: "I'll describe a business idea — critique it honestly and find weak points." },
  { icon: MessageSquare, label: 'Summarize a long article',        prompt: "I'll paste an article — summarize the key points in a few bullets." },
  { icon: PenLine,       label: 'Help me write an email',          prompt: 'Help me write a professional email — I\'ll give you the context.' },
  { icon: Code2,         label: 'Debug my code',                   prompt: "I'll paste some code — help me find why it isn't working." },
  { icon: Code2,         label: 'Explain this regex',              prompt: 'Explain what a regex pattern does in plain English.' },
  { icon: BookOpen,      label: 'Recommend a book',                prompt: 'Recommend a book based on what I\'ve enjoyed reading recently.' },
  { icon: Compass,       label: 'Plan my weekend',                 prompt: 'Help me plan a fun weekend — give me a rough itinerary.' },
  { icon: Plane,         label: 'Plan a 5-day trip',               prompt: 'Plan a 5-day trip — I\'ll tell you the destination and budget.' },
  { icon: Map,           label: 'Explore a new hobby',             prompt: 'Suggest a new hobby I might enjoy and how to start.' },
  { icon: ChefHat,       label: 'Suggest a dinner recipe',         prompt: 'Suggest a quick dinner recipe with what I have on hand — I\'ll tell you.' },
  { icon: Music,         label: 'Build a playlist',                prompt: 'Help me build a playlist for focused work.' },
  { icon: Globe2,        label: 'Latest tech news',                prompt: 'Give me the most important tech news from this week.' },
  { icon: GraduationCap, label: 'Teach me a concept',              prompt: 'Teach me one thing I should know about a topic of your choice.' },
  { icon: HeartPulse,    label: 'Improve my sleep',                prompt: 'Suggest evidence-backed ways to improve my sleep quality.' },
  { icon: FlaskConical,  label: 'Explain a science paper',         prompt: "I'll paste an abstract — explain what the research actually means." },
  { icon: DollarSign,    label: 'Convert currencies',              prompt: 'Convert 100 USD to my local currency and explain the rate.' },
  { icon: Languages,     label: 'Translate to French',             prompt: "I'll write something — translate it to natural French." },
  { icon: Palette,       label: 'Pick brand colors',               prompt: 'Help me pick a 3-color palette for a friendly tech product.' },
  { icon: Mic,           label: 'Try voice mode',                  prompt: 'How does voice mode work and what should I try first?' },
];

const NUM_SUGGESTIONS = 6;

function pickRandom<T>(arr: T[], n: number): T[] {
  const copy = [...arr];
  const out: T[] = [];
  for (let i = 0; i < n && copy.length > 0; i++) {
    const idx = Math.floor(Math.random() * copy.length);
    out.push(copy.splice(idx, 1)[0]);
  }
  return out;
}

function ChatPanelComponent({
  messages,
  isStreaming = false,
  onEditMessage,
  onRetryMessage,
  onSuggestPrompt,
}: ChatPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const suggestions = useMemo(
    () => pickRandom(PROMPT_POOL, NUM_SUGGESTIONS),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [messages.length === 0],
  );

  const lastMessage = messages[messages.length - 1];
  const showWorkingIndicator =
    isStreaming &&
    (!lastMessage || lastMessage.role === 'user' || (lastMessage.role === 'assistant' && !lastMessage.content));

  return (
    <main
      className="flex-1 overflow-y-auto w-full bg-[var(--color-surface-base)]"
      role="main"
      aria-label="Chat conversation"
    >
      <section className="px-4 py-6 max-w-3xl mx-auto h-full">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center font-sans">
            <div
              className="relative flex items-center justify-center mb-6"
              style={{ width: 72, height: 72 }}
            >
              <div
                className="absolute inset-0 rounded-full"
                style={{
                  backgroundColor: 'var(--color-accent-muted)',
                  opacity: 0.5,
                }}
              />
              <div
                className="absolute rounded-full"
                style={{
                  inset: 8,
                  backgroundColor: 'var(--color-accent-muted)',
                }}
              />
              <Sparkles
                size={28}
                strokeWidth={1.75}
                style={{ color: 'var(--color-accent)', position: 'relative' }}
              />
            </div>

            <h2
              className="text-[22px] font-semibold tracking-[-0.01em] mb-2"
              style={{ color: 'var(--color-fg-primary)' }}
            >
              How can I help?
            </h2>
            <p
              className="text-[14px] mb-8 max-w-md text-center"
              style={{ color: 'var(--color-fg-muted)' }}
            >
              Ask me anything — type below or tap voice to talk it out.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 w-full max-w-2xl">
              {suggestions.map(({ icon: Icon, label, prompt }) => (
                <button
                  key={label}
                  onClick={() => onSuggestPrompt?.(prompt)}
                  disabled={!onSuggestPrompt}
                  className="group flex items-center gap-2.5 px-3.5 py-3 rounded-xl text-left text-[13px] font-medium transition-all"
                  style={{
                    backgroundColor: 'var(--color-surface-raised)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-fg-secondary)',
                    cursor: onSuggestPrompt ? 'pointer' : 'default',
                  }}
                  onMouseEnter={(e) => {
                    if (!onSuggestPrompt) return;
                    e.currentTarget.style.backgroundColor = 'var(--color-surface-overlay)';
                    e.currentTarget.style.borderColor = 'var(--color-border-strong)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--color-surface-raised)';
                    e.currentTarget.style.borderColor = 'var(--color-border)';
                  }}
                >
                  <Icon
                    size={15}
                    strokeWidth={1.75}
                    style={{ color: 'var(--color-accent)', flexShrink: 0 }}
                  />
                  <span className="truncate">{label}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, idx) => {
              const isLastMessage = idx === messages.length - 1;
              const toolCalls = message.toolCalls || [];

              return (
                <article key={message.id} role="article">
                  {message.role === 'user' ? (
                    <HumanMessage
                      message={message}
                      isLast={isLastMessage}
                      onEdit={
                        onEditMessage
                          ? (newText) => onEditMessage(message.id, newText)
                          : undefined
                      }
                    />
                  ) : (
                    <AIMessage
                      message={message}
                      isLast={isLastMessage}
                      onRetry={
                        onRetryMessage ? () => onRetryMessage(message.id) : undefined
                      }
                    />
                  )}

                  {toolCalls.length > 0 && message.role === 'assistant' && (
                    <section className="my-2" aria-label={`Tool calls for message ${message.id}`}>
                      <div className="mb-2">
                        <h4 className="text-xs font-semibold uppercase tracking-wider font-mono text-[var(--color-fg-muted)]">
                          Tool Calls ({toolCalls.length})
                        </h4>
                      </div>
                      <div className="flex flex-col gap-2">
                        {toolCalls.map((tool, toolIdx) => (
                          <ToolMessage
                            key={tool.id}
                            toolCall={tool}
                            isLast={toolIdx === toolCalls.length - 1}
                          />
                        ))}
                      </div>
                    </section>
                  )}
                </article>
              );
            })}

            {showWorkingIndicator && <WorkingIndicator />}

            <div ref={messagesEndRef} />
          </>
        )}
      </section>
    </main>
  );
}

function WorkingIndicator() {
  return (
    <div className="flex justify-start mb-3 mt-1" aria-live="polite" aria-label="Agent is working">
      <div
        className="flex items-center gap-1.5 px-4 py-3 rounded-2xl"
        style={{
          backgroundColor: 'var(--color-surface-raised)',
          border: '1px solid var(--color-border)',
        }}
      >
        {[0, 0.18, 0.36].map((delay, i) => (
          <span
            key={i}
            className="inline-block w-1.5 h-1.5 rounded-full"
            style={{
              backgroundColor: 'var(--color-fg-muted)',
              animation: `chatPanelDotBounce 1.05s ${delay}s infinite ease-in-out`,
            }}
          />
        ))}
      </div>
      <style>{`
        @keyframes chatPanelDotBounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.45; }
          30% { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}

export const ChatPanel = memo(ChatPanelComponent);
