import { useCallback, useEffect, useState } from 'react';
import { Mic, MicOff, Settings } from 'lucide-react';
import { VoiceOrb } from '@components/ui';
import { ChatPanel, ChatInput, ConfirmModal } from '@components/Chat';
import { useVoiceConfig } from '@context/VoiceConfigContext';
import { useVoiceAgent, useNarrate, useVoiceClone } from '@hooks/index';
import { useConverseContext } from '@components/layouts';
import { VoiceSettingsSidebar, VoiceCloneModal } from '@components/VoiceSettings';
import type { AgentStatus } from '@typing';
import type { StatusToOrbStateFunction } from './Converse.types';

const STATUS_LABELS: Record<AgentStatus, string> = {
  idle: 'Idle',
  listening: 'Listening',
  processing: 'Thinking',
  speaking: 'Speaking',
};

const statusToOrbState: StatusToOrbStateFunction = (
  status,
  isConnected,
  error,
) => {
  if (error) return 'error';
  if (!isConnected) return 'idle';
  if (status === 'processing') return 'thinking';
  return status;
};

type PageMode = 'chat' | 'voice';

export function ConversePage() {
  const {
    voices,
    personalities,
    selectedVoiceId,
    selectedPersonalityId,
    setVoiceId,
    isLoadingVoices,
    speed: voiceSpeed,
    language: voiceLanguage,
    setSpeed: setVoiceSpeed,
    setLanguage: setVoiceLanguage,
  } = useVoiceConfig();
  const narrate = useNarrate();
  const clone = useVoiceClone();
  const { chat, setMode } = useConverseContext();

  const [mode, setLocalMode] = useState<PageMode>('chat');

  const handleSetMode = useCallback((newMode: PageMode) => {
    setLocalMode(newMode);
    setMode?.(newMode);
  }, [setMode]);
  const [showSettings, setShowSettings] = useState(true);
  const [deletingVoiceId, setDeletingVoiceId] = useState<string | null>(null);

  const voice = useVoiceAgent({});

  const messages = chat.messages;

  const isLoading = mode === 'chat' ? chat.isLoading : false;
  const status = voice.status;
  const isConnected = voice.isConnected;
  const audioLevel = voice.audioLevel;
  const error = mode === 'chat' ? (typeof chat.error === 'string' ? chat.error : null) : null;

  useEffect(() => {
    if (mode === 'voice' && !isConnected) {
      voice.connect().catch(() => {});
    } else if (mode === 'chat' && isConnected) {
      voice.disconnect();
    }
  }, [mode, isConnected, voice]);

  useEffect(() => {
    if (voices.length > 0 && !selectedVoiceId) {
      const defaultVoice = voices[0];
      setVoiceId(defaultVoice.id);
    }
  }, [voices, selectedVoiceId, setVoiceId]);

  const selectedVoice = voices.find((v) => v.id === selectedVoiceId);

  const handleDeleteClonedVoice = (id: string) => {
    if (!id.startsWith('clone_')) return;
    setDeletingVoiceId(id);
  };

  const handleCloneVoiceSubmit = async () => {
    await clone.handleCloneVoice();
  };

  const conversationNarrateProxy = {
    ...narrate,
    voices,
    selectedVoice: selectedVoiceId || '',
    setSelectedVoice: setVoiceId,
    loadingVoices: isLoadingVoices,
    speed: voiceSpeed,
    setSpeed: setVoiceSpeed,
    selectedLanguage: voiceLanguage,
    setSelectedLanguage: setVoiceLanguage,
  };

  const orbState = voice.isMuted && isConnected
    ? 'idle'
    : statusToOrbState(status, isConnected, !!error);
  const selectedPersonality = personalities.find((p) => p.id === selectedPersonalityId);

  const handleToggleVoice = useCallback(async () => {
    if (mode === 'voice' && isConnected) {
      voice.togglePause();
      return;
    }

    if (mode === 'chat') {
      handleSetMode('voice');
      try {
        await voice.connect();
      } catch {
        handleSetMode('chat');
      }
    }
  }, [mode, isConnected, voice, handleSetMode]);

  const handleSendText = useCallback((text: string) => {
    if (mode === 'chat') {
      chat.sendMessage(text);
    }
  }, [mode, chat]);

  const handleEditMessage = useCallback((messageId: string, newText: string) => {
    if (mode === 'chat') {
      chat.editMessage(messageId, newText);
    }
  }, [mode, chat]);

  const handleRetryMessage = useCallback((messageId: string) => {
    if (mode === 'chat') {
      chat.retryMessage(messageId);
    }
  }, [mode, chat]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code !== 'Space' || mode !== 'voice') return;
      const tag = (document.activeElement as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;
      e.preventDefault();
      handleToggleVoice();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [handleToggleVoice, mode]);

  if (mode === 'chat') {
    return (
      <div className="flex-1 flex flex-col min-h-0">
        <div
          className="px-4 py-3 flex justify-end items-center gap-3"
          style={{ borderBottom: '1px solid var(--color-border)' }}
        >
          <ModeToggle mode={mode} onModeChange={handleSetMode} />
        </div>

        <ChatPanel
          messages={messages}
          isStreaming={chat.isStreaming}
          onEditMessage={handleEditMessage}
          onRetryMessage={handleRetryMessage}
          onSuggestPrompt={handleSendText}
        />

        <div className="flex-none px-0 py-4" style={{ backgroundColor: 'var(--color-surface-base)' }}>
          <ChatInput
            onSend={handleSendText}
            onVoiceToggle={() => handleSetMode('voice')}
            disabled={isLoading}
            placeholder="Type a message... (or press Mic to use voice)"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex min-h-0 overflow-hidden">
      <div className="flex-1 flex flex-col items-center justify-center px-8 relative overflow-hidden">
        <div className="absolute top-4 right-4">
          <ModeToggle mode={mode} onModeChange={handleSetMode} />
        </div>

        <VoiceOrb
          state={orbState}
          size="hero"
          intensity={isConnected ? audioLevel : 0}
          hideStatus
        />

        <div
          className="mt-2 font-mono text-[13px] tracking-wide"
          style={{
            color: isConnected
              ? 'var(--color-fg-primary)'
              : 'var(--color-fg-secondary)',
          }}
        >
          {error
            ? 'Disconnected'
            : voice.isMuted && isConnected
              ? 'Paused'
              : STATUS_LABELS[isConnected ? status : 'idle']}
        </div>

        <div className="mt-3 flex items-center gap-3 font-mono text-[11px]">
          <span style={{ color: 'var(--color-fg-secondary)' }}>
            {selectedVoice?.name ?? '—'}
          </span>
          <span style={{ color: 'var(--color-border-strong)' }}>·</span>
          <span style={{ color: 'var(--color-fg-secondary)' }}>
            {selectedPersonality?.name ?? '—'}
          </span>
        </div>

        {error && typeof error === 'string' && (
          <div
            className="mt-4 max-w-md text-center font-mono text-[12px] px-3 py-2 rounded-md border"
            style={{
              backgroundColor: 'var(--color-danger-muted)',
              borderColor: 'var(--color-danger)',
              color: 'var(--color-danger)',
            }}
          >
            {error}
          </div>
        )}

        <div className="absolute bottom-10 left-0 right-0 flex flex-col items-center gap-3">
          <div className="flex items-center gap-3">
            <MicControl
              isConnected={isConnected}
              isMuted={voice.isMuted}
              onClick={handleToggleVoice}
            />
            <button
              onClick={() => setShowSettings(!showSettings)}
              aria-label="Toggle voice settings"
              aria-pressed={showSettings}
              className={`w-16 h-16 rounded-full flex items-center justify-center transition-colors duration-150 ${
                showSettings
                  ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent)] hover:bg-[var(--color-accent-muted)]'
                  : 'bg-[var(--color-surface-raised)] text-[var(--color-fg-secondary)] hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-fg-primary)]'
              }`}
            >
              <Settings size={22} strokeWidth={1.75} />
            </button>
          </div>

          {!isConnected && (
            <div className="font-mono text-xs text-[var(--color-fg-muted)]">
              or press{' '}
              <kbd className="px-1.5 py-0.5 rounded border text-[10px] font-mono bg-[var(--color-surface-raised)] border-[var(--color-border-strong)] text-[var(--color-fg-secondary)]">
                Space
              </kbd>
            </div>
          )}
        </div>
      </div>

      {showSettings && (
        <VoiceSettingsSidebar
          narrate={conversationNarrateProxy}
          clone={clone}
          selectedVoiceData={selectedVoice}
          onDeleteClonedVoice={handleDeleteClonedVoice}
        />
      )}

      <VoiceCloneModal
        clone={clone}
        languages={narrate.languages}
        onSubmit={handleCloneVoiceSubmit}
      />

      <ConfirmModal
        isOpen={deletingVoiceId !== null}
        title="Delete voice?"
        message={`"${narrate.voices.find(v => v.id === deletingVoiceId)?.name || 'Untitled'}" will be permanently deleted.`}
        confirmLabel="Delete"
        danger
        onClose={() => setDeletingVoiceId(null)}
        onConfirm={async () => {
          if (deletingVoiceId) {
            await clone.handleDeleteClonedVoice(deletingVoiceId, narrate.voices, narrate.selectedVoice, narrate.setSelectedVoice);
            setDeletingVoiceId(null);
          }
        }}
      />
    </div>
  );
}

function MicControl({
  isConnected,
  isMuted,
  onClick,
}: {
  isConnected: boolean;
  isMuted: boolean;
  onClick: () => void;
}) {
  const ariaLabel = !isConnected
    ? 'Start conversation'
    : isMuted
      ? 'Resume listening'
      : 'Pause listening';

  const buttonClasses = !isConnected
    ? 'bg-[var(--color-surface-raised)] text-[var(--color-fg-secondary)] hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-fg-primary)]'
    : isMuted
      ? 'bg-[var(--color-surface-raised)] text-[var(--color-fg-primary)] border border-[var(--color-border-strong)] hover:bg-[var(--color-surface-overlay)]'
      : 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-dim)]';

  return (
    <button
      onClick={onClick}
      aria-label={ariaLabel}
      title={ariaLabel}
      aria-pressed={isConnected && !isMuted}
      className={`group relative w-16 h-16 rounded-full flex items-center justify-center transition-all duration-200 ${buttonClasses}`}
    >
      {isConnected && !isMuted && (
        <span
          className="absolute inset-0 rounded-full pointer-events-none border border-[var(--color-accent)] opacity-35"
          style={{ transform: 'scale(1.16)' }}
        />
      )}

      {isConnected && isMuted ? (
        <MicOff size={22} strokeWidth={1.75} />
      ) : (
        <Mic size={22} strokeWidth={1.75} />
      )}
    </button>
  );
}

function ModeToggle({ mode, onModeChange }: { mode: PageMode; onModeChange: (mode: PageMode) => void }) {
  const segBtn = (thisMode: PageMode, label: string) => {
    const isActive = mode === thisMode;
    return (
      <button
        onClick={() => onModeChange(thisMode)}
        style={{
          padding: '5px 12px',
          border: 'none',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: isActive ? 'var(--color-accent-muted)' : 'transparent',
          color: isActive ? 'var(--color-accent)' : 'var(--color-fg-muted)',
          fontFamily: 'var(--font-sans)',
          fontSize: '12px',
          fontWeight: 500,
          cursor: 'pointer',
          transition: 'background-color 150ms, color 150ms',
        }}
        onMouseEnter={(e) => {
          if (!isActive) e.currentTarget.style.color = 'var(--color-fg-secondary)';
        }}
        onMouseLeave={(e) => {
          if (!isActive) e.currentTarget.style.color = 'var(--color-fg-muted)';
        }}
      >
        {label}
      </button>
    );
  };

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '2px',
        padding: '3px',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-md)',
        backgroundColor: 'var(--color-surface-raised)',
      }}
    >
      {segBtn('chat', 'Chat')}
      {segBtn('voice', 'Voice')}
    </div>
  );
}
