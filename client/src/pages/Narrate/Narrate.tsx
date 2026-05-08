import { useState } from 'react';
import { Loader2, Download, Play, Pause, Clock, Copy, Check, Trash2, ArrowLeft, Wand2 } from 'lucide-react';
import { useNavigate } from 'react-router';
import { useNarrate, useAudioPlayer, useVoiceClone } from '@hooks/index';
import { formatTime } from '@utils/index';
import { VoiceSettingsSidebar, VoiceCloneModal } from '@components/VoiceSettings';
import { ConfirmModal } from '@components/Chat';
import { AudioWaveform } from '@components/ui';

export function NarratePage() {
  const navigate = useNavigate();
  const narrate = useNarrate();
  const audio = useAudioPlayer();
  const clone = useVoiceClone();
  const [deletingVoiceId, setDeletingVoiceId] = useState<string | null>(null);
  const [deletingAudioId, setDeletingAudioId] = useState<string | null>(null);

  const selectedVoiceData = narrate.voices.find(v => v.id === narrate.selectedVoice);
  const wordCount = narrate.text.trim().split(/\s+/).filter(Boolean).length;
  const estimatedDuration = Math.ceil((wordCount / 150) * 60 / narrate.speed);

  const handleDownload = (audioId: string, voiceName: string) => {
    const audioData = narrate.generatedAudios.find(a => a.id === audioId);
    if (!audioData) return;
    const link = document.createElement('a');
    link.href = audioData.audioUrl;
    link.download = `narration-${voiceName}-${audioId}.mp3`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDeleteAudio = (id: string) => {
    setDeletingAudioId(id);
  };

  const deletingAudio = narrate.generatedAudios.find((a) => a.id === deletingAudioId);

  const handleDeleteClonedVoice = (id: string) => {
    if (!id.startsWith('clone_')) return;
    setDeletingVoiceId(id);
  };

  const handleCloneVoiceSubmit = async () => {
    await clone.handleCloneVoice();
  };

  return (
    <div className="flex-1 flex min-h-0 overflow-hidden">
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          <div className="max-w-3xl mx-auto px-8 py-8 w-full">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => navigate('/')}
                  className="p-1.5 hover:bg-[color:var(--color-surface-raised)] rounded-md transition-colors"
                  aria-label="Go back"
                >
                  <ArrowLeft size={18} className="text-[color:var(--color-fg-secondary)]" />
                </button>
                <h1 className="text-lg font-semibold text-[color:var(--color-fg-primary)]">Narrate</h1>
              </div>
              {selectedVoiceData && (
                <div className="flex items-center gap-2 text-sm text-[color:var(--color-fg-secondary)]">
                  <span>{selectedVoiceData.name}</span>
                  <span className="text-[color:var(--color-fg-muted)]">·</span>
                  <span>{narrate.speed}x</span>
                </div>
              )}
            </div>

            <div
              className="rounded-xl overflow-hidden transition-all"
              style={{
                backgroundColor: 'var(--color-surface-raised)',
                border: '1px solid var(--color-border)',
                boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
              }}
            >
              <textarea
                value={narrate.text}
                onChange={(e) => narrate.setText(e.target.value)}
                placeholder="Start typing or paste your text here…"
                maxLength={5000}
                rows={8}
                className="w-full px-5 pt-5 pb-3 bg-transparent border-none text-[color:var(--color-fg-primary)] text-[15px] leading-[1.6] resize-none focus:outline-none placeholder:text-[color:var(--color-fg-muted)]"
              />

              <div
                className="flex items-center justify-between px-4 py-3"
                style={{
                  borderTop: '1px solid var(--color-border)',
                  backgroundColor: 'var(--color-surface-base)',
                }}
              >
                <div className="flex items-center gap-2">
                  <StatPill label={`${narrate.text.length} ch`} />
                  <StatPill label={`${wordCount} words`} />
                  {wordCount > 0 && (
                    <StatPill
                      icon={<Clock className="w-3 h-3" strokeWidth={2} />}
                      label={`~${estimatedDuration}s`}
                    />
                  )}
                </div>

                <button
                  onClick={narrate.handleGenerate}
                  disabled={!narrate.text.trim() || narrate.status === 'generating'}
                  className="inline-flex items-center justify-center gap-2 px-5 h-10 rounded-lg text-[14px] font-medium transition-all"
                  style={{
                    backgroundColor:
                      narrate.text.trim() && narrate.status !== 'generating'
                        ? 'var(--color-accent)'
                        : 'var(--color-surface-overlay)',
                    color:
                      narrate.text.trim() && narrate.status !== 'generating'
                        ? '#ffffff'
                        : 'var(--color-fg-muted)',
                    cursor:
                      narrate.text.trim() && narrate.status !== 'generating'
                        ? 'pointer'
                        : 'not-allowed',
                    minWidth: '160px',
                    boxShadow:
                      narrate.text.trim() && narrate.status !== 'generating'
                        ? '0 1px 3px rgba(124, 58, 237, 0.25)'
                        : 'none',
                  }}
                >
                  {narrate.status === 'generating' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" strokeWidth={2.25} />
                      Generating…
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-4 h-4" strokeWidth={2} />
                      Generate
                    </>
                  )}
                </button>
              </div>
            </div>

            {narrate.error && (
              <div
                className="mt-3 flex items-start gap-2 px-3.5 py-2.5 rounded-lg text-[13px]"
                style={{
                  backgroundColor: 'var(--color-danger-muted)',
                  border: '1px solid var(--color-danger)',
                  color: 'var(--color-danger)',
                }}
              >
                <span>{narrate.error}</span>
              </div>
            )}

            {/* The audio element is rendered UNCONDITIONALLY (outside the
                generatedAudios.length check). The useAudioPlayer hook's
                useEffect attaches timeupdate/play/pause listeners on first
                mount with empty deps; if the audio element didn't exist
                yet (because the list was empty), the effect bailed and
                listeners never attached — so the time display stayed
                frozen and play state was out of sync. Always-mount fixes
                both. */}
            <audio ref={audio.setAudioRef} className="hidden" preload="none" />

            {narrate.generatedAudios.length > 0 && (
              <div className="mt-10">

                <div className="mb-3">
                  <span className="text-[11px] font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">
                    Generated ({narrate.generatedAudios.length})
                  </span>
                </div>

                <div className="border border-[color:var(--color-border)] rounded-md divide-y divide-[color:var(--color-border)] overflow-hidden">
                  {narrate.generatedAudios.map((audioData) => {
                    const isActive = audioData.id === audio.activeId;
                    const playing = isActive && audio.isPlaying;
                    const isCopied = narrate.copiedId === audioData.id;
                    return (
                      <div key={audioData.id} className={`${isActive ? 'bg-[color:var(--color-accent-muted)]' : 'bg-[color:var(--color-surface-raised)] hover:bg-[color:var(--color-surface-overlay)]'}`}>
                        <div className="flex items-center gap-3 px-4 py-2.5">
                          <button onClick={(e) => { e.stopPropagation(); audio.handlePlayPause(audioData.id, audioData.audioUrl); }} className={`w-7 h-7 rounded-md shrink-0 flex items-center justify-center transition-colors ${playing ? 'bg-[color:var(--color-accent)] text-white' : 'bg-[color:var(--color-surface-overlay)] text-[color:var(--color-fg-muted)] hover:bg-[color:var(--color-border)]'}`}>
                            {playing ? <Pause className="w-3 h-3" fill="white" /> : <Play className="w-3 h-3 ml-0.5" />}
                          </button>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-[color:var(--color-fg-primary)] truncate">{audioData.text}</p>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="text-[11px] text-[color:var(--color-fg-muted)]">{audioData.voiceName}</span>
                              <span className="text-[11px] text-[color:var(--color-fg-muted)]">{audioData.speed}x</span>
                            </div>
                          </div>
                          <span className="text-xs text-[color:var(--color-fg-muted)] tabular-nums">{formatTime(audioData.duration)}</span>
                          <div className="flex items-center gap-0.5 shrink-0">
                            <button onClick={(e) => { e.stopPropagation(); narrate.handleCopyText(audioData.id, audioData.text); }} className={`p-1.5 rounded-md transition-colors ${isCopied ? 'text-green-600' : 'text-[color:var(--color-fg-muted)] hover:text-[color:var(--color-fg-secondary)]'}`}>
                              {isCopied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                            </button>
                            <button onClick={(e) => { e.stopPropagation(); handleDownload(audioData.id, audioData.voiceName); }} className="p-1.5 rounded-md text-[color:var(--color-fg-muted)] hover:text-[color:var(--color-fg-secondary)] transition-colors">
                              <Download className="w-3.5 h-3.5" />
                            </button>
                            <button onClick={(e) => { e.stopPropagation(); handleDeleteAudio(audioData.id); }} className="p-1.5 rounded-md text-[color:var(--color-fg-muted)] hover:text-[color:var(--color-danger)] transition-colors">
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                        {isActive && (
                          <div className="px-4 pb-3">
                            <div className="flex items-center gap-2.5">
                              <span className={`text-[10px] font-mono tabular-nums ${playing ? 'text-[color:var(--color-fg-secondary)]' : 'text-[color:var(--color-fg-muted)]'}`}>{formatTime(audio.currentTime)}</span>
                              <AudioWaveform
                                audioRef={audio.audioRef}
                                isPlaying={playing}
                                progress={audio.progress}
                                onSeek={(e) => { e.stopPropagation(); audio.handleProgressClick(e); }}
                              />
                              <span className="text-[10px] font-mono tabular-nums text-[color:var(--color-fg-muted)]">{formatTime(audioData.duration)}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <VoiceSettingsSidebar
        narrate={narrate}
        clone={clone}
        selectedVoiceData={selectedVoiceData}
        onDeleteClonedVoice={handleDeleteClonedVoice}
      />

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

      <ConfirmModal
        isOpen={deletingAudioId !== null}
        title="Delete narration?"
        message={
          deletingAudio
            ? `"${deletingAudio.text.slice(0, 80)}${deletingAudio.text.length > 80 ? '…' : ''}" will be permanently deleted.`
            : 'This narration will be permanently deleted.'
        }
        confirmLabel="Delete"
        danger
        onClose={() => setDeletingAudioId(null)}
        onConfirm={async () => {
          if (deletingAudioId) {
            await narrate.handleDelete(deletingAudioId);
            setDeletingAudioId(null);
          }
        }}
      />
    </div>
  );
}

function StatPill({ icon, label }: { icon?: React.ReactNode; label: string }) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium tabular-nums"
      style={{
        backgroundColor: 'var(--color-surface-overlay)',
        color: 'var(--color-fg-muted)',
      }}
    >
      {icon}
      {label}
    </span>
  );
}
