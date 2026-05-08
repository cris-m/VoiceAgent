import { Loader2, Volume2, Globe, UserPlus, Play, Pause, Trash2 } from 'lucide-react';
import type { UseNarrateReturn, UseVoiceCloneReturn } from '@typing';
import type { Voice } from '@pages/Narrate/Narrate.types';

interface VoiceSettingsSidebarProps {
  narrate: UseNarrateReturn;
  clone: UseVoiceCloneReturn;
  selectedVoiceData?: Voice;
  onDeleteClonedVoice: (id: string) => void;
}

export function VoiceSettingsSidebar({
  narrate,
  clone,
  selectedVoiceData,
  onDeleteClonedVoice,
}: VoiceSettingsSidebarProps) {
  return (
    <div className="w-68 flex-shrink-0 flex flex-col border-l border-[var(--color-border)] bg-[var(--color-surface-raised)]">
      <div className="flex-1 overflow-y-auto">

        {narrate.supportsCloning && (
          <div className="px-4 pt-3 pb-0">
            <button
              onClick={() => clone.setShowCloneModal(true)}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 border rounded-md text-sm font-medium bg-[var(--color-surface-base)] border-[var(--color-border)] text-[var(--color-fg-secondary)] cursor-pointer transition-all hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
            >
              <UserPlus size={14} />
              Clone a voice
            </button>
          </div>
        )}

        <div className="flex items-center gap-1.5 px-4 pt-4 pb-1.5 font-mono text-xs font-semibold uppercase tracking-widest text-[var(--color-fg-muted)]">
          Voices
        </div>

        {narrate.loadingVoices ? (
          <div className="flex justify-center py-10">
            <Loader2 size={18} className="animate-spin text-[var(--color-fg-muted)]" />
          </div>
        ) : (
          <div>
            {narrate.voices.map((voice) => {
              const isSelected = voice.id === narrate.selectedVoice;
              const isPreviewing = narrate.previewingVoice === voice.id;
              const isCloned = voice.id.startsWith('clone_') || voice.tags?.includes('Cloned');

              return (
                <div
                  key={voice.id}
                  onClick={() => narrate.setSelectedVoice(voice.id)}
                  className={`group flex items-center gap-2 px-4 py-2 cursor-pointer border-l-2 transition-colors ${
                    isSelected
                      ? 'border-[var(--color-accent)] bg-[var(--color-accent-muted)]'
                      : 'border-transparent hover:bg-[var(--color-surface-overlay)]'
                  }`}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      narrate.handlePreviewVoice(voice.id);
                    }}
                    className={`w-6 h-6 flex-shrink-0 flex items-center justify-center rounded border transition-all ${
                      isPreviewing
                        ? 'bg-[var(--color-accent)] border-[var(--color-accent)] text-white'
                        : 'bg-[var(--color-surface-overlay)] border-[var(--color-border)] text-[var(--color-fg-muted)] hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]'
                    }`}
                  >
                    {isPreviewing
                      ? <Pause size={10} fill="white" />
                      : <Play size={10} className="ml-0.5" />
                    }
                  </button>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`font-sans text-sm truncate ${
                          isSelected
                            ? 'font-medium text-[var(--color-fg-primary)]'
                            : 'font-normal text-[var(--color-fg-secondary)]'
                        }`}
                      >
                        {voice.name}
                      </span>
                      {narrate.supportsCloning && isCloned && (
                        <span className="text-xs px-1.5 py-0.5 rounded border border-[var(--color-border)] text-[var(--color-fg-muted)] flex-shrink-0">
                          cloned
                        </span>
                      )}
                    </div>
                    {voice.description && (
                      <p className="font-sans text-xs text-[var(--color-fg-muted)] truncate mt-0.5">
                        {voice.description}
                      </p>
                    )}
                  </div>

                  {narrate.supportsCloning && isCloned && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteClonedVoice(voice.id);
                      }}
                      aria-label={`Delete cloned voice ${voice.name}`}
                      title="Delete cloned voice"
                      className="w-7 h-7 flex-shrink-0 flex items-center justify-center rounded-md bg-transparent text-[var(--color-fg-muted)] cursor-pointer transition-colors hover:bg-[var(--color-surface-overlay)] hover:text-[var(--color-danger)]"
                    >
                      <Trash2 size={14} strokeWidth={1.75} />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {narrate.supportsSpeed && (
          <>
            <div className="border-t border-[var(--color-border)] mt-2" />
            <div className="flex items-center gap-1.5 px-4 pt-4 pb-1.5 font-mono text-xs font-semibold uppercase tracking-widest text-[var(--color-fg-muted)]">
              Speed
            </div>
            <div className="px-4 pb-3">
              <div className="flex gap-1 mb-2.5">
                {[0.75, 1.0, 1.25, 1.5, 1.75, 2.0].map((v) => (
                  <button
                    key={v}
                    onClick={() => narrate.setSpeed(v)}
                    className={`flex-1 py-1.25 rounded border text-xs font-mono font-medium cursor-pointer transition-all ${
                      narrate.speed === v
                        ? 'bg-[var(--color-accent-muted)] border-[var(--color-accent)] text-[var(--color-accent)]'
                        : 'bg-[var(--color-surface-raised)] border-[var(--color-border)] text-[var(--color-fg-secondary)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-fg-primary)]'
                    }`}
                  >
                    {v === 1.0 ? '1x' : `${v}x`}
                  </button>
                ))}
              </div>
              <input
                type="range"
                min="0.5"
                max="2.0"
                step="0.1"
                value={narrate.speed}
                onChange={(e) => narrate.setSpeed(parseFloat(e.target.value))}
                className="w-full h-1.5 rounded-full appearance-none cursor-pointer bg-[var(--color-border)] [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:h-3.5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[var(--color-accent)] [&::-webkit-slider-thumb]:cursor-pointer"
              />
              <div className="flex justify-between mt-1 font-mono text-xs text-[var(--color-fg-muted)]">
                <span>0.5x</span>
                <span>{narrate.speed.toFixed(1)}x</span>
                <span>2.0x</span>
              </div>
            </div>
          </>
        )}

        {narrate.supportsLanguage && (
          <>
            <div className="border-t border-[var(--color-border)]" />
            <div className="flex items-center gap-1.5 px-4 pt-4 pb-1.5 font-mono text-xs font-semibold uppercase tracking-widest text-[var(--color-fg-muted)]">
              <Globe size={11} /> Language
            </div>
            <div className="px-4 pb-4">
              <div className="grid grid-cols-2 gap-1">
                {narrate.languages.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => narrate.setSelectedLanguage(lang.code)}
                    className={`px-2.5 py-1.5 rounded border text-xs text-left cursor-pointer font-sans transition-all ${
                      narrate.selectedLanguage === lang.code
                        ? 'bg-[var(--color-accent-muted)] border-[var(--color-accent)] text-[var(--color-accent)]'
                        : 'bg-[var(--color-surface-raised)] border-[var(--color-border)] text-[var(--color-fg-secondary)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-fg-primary)]'
                    }`}
                  >
                    {lang.name}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

      </div>

      {selectedVoiceData && (
        <div className="flex-shrink-0 flex items-center gap-2 px-3 py-2.5 border-t border-[var(--color-border)] bg-[var(--color-surface-base)]">
          <div className="w-6 h-6 flex-shrink-0 flex items-center justify-center rounded border border-[var(--color-border)] bg-[var(--color-surface-overlay)]">
            <Volume2 size={12} className="text-[var(--color-fg-secondary)]" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-sans text-xs font-medium text-[var(--color-fg-primary)] truncate">
              {selectedVoiceData.name}
            </p>
          </div>
          <span className="font-mono text-xs text-[var(--color-fg-muted)] flex-shrink-0">
            {narrate.speed}x
          </span>
        </div>
      )}
    </div>
  );
}
