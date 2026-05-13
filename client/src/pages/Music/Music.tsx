import { useState } from 'react';
import { Loader2, Download, Play, Pause, ArrowLeft, Wand2, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router';
import { useMusic } from '@hooks/index';
import { useAudioPlayer } from '@hooks/index';
import { formatTime } from '@utils/index';
import { AudioWaveform } from '@components/ui';
import { ConfirmModal } from '@components/Chat';

const EXAMPLE_PROMPTS = [
  'Hard-hitting trap beat with 808 sub-bass, crisp hi-hats, and dark melodic loop at 140 BPM',
  'Lo-fi hip hop beat with vinyl crackle, mellow piano chords, and laid-back drums',
  'Aggressive drill beat with sliding 808s, sharp snares, and ominous string sample',
  'Chill boom-bap beat with dusty drums, soulful jazz sample chops, and head-nod groove',
  'Modern R&B beat with warm Rhodes piano, finger snaps, and smooth bass at 90 BPM',
  'Phonk beat with cowbells, distorted 808s, and pitched-down vocal chops, high energy',
];

const STYLE_TAGS = [
  'trap',
  'hip-hop',
  'lo-fi',
  'boom-bap',
  'drill',
  'phonk',
  'r&b',
  'house',
  'techno',
  'jersey-club',
  'dark',
  'mellow',
  'aggressive',
  'dreamy',
  'jazzy',
  'hard-hitting',
];

export function MusicPage() {
  const navigate = useNavigate();
  const music = useMusic();
  const {
    audioRef,
    setAudioRef,
    progress,
    currentTime,
    isPlaying,
    activeId,
    handlePlayPause,
    handleProgressClick,
  } = useAudioPlayer();
  const [deletingTrackId, setDeletingTrackId] = useState<string | null>(null);
  const deletingTrack = music.tracks.find((t) => t.id === deletingTrackId);

  return (
    <div className="flex-1 flex min-h-0 overflow-hidden">
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          <div className="max-w-3xl mx-auto px-8 py-8 w-full">
            <div className="flex items-center gap-3 mb-6">
              <button
                onClick={() => navigate('/')}
                className="p-1.5 hover:bg-[color:var(--color-surface-raised)] rounded-md transition-colors"
                aria-label="Go back"
              >
                <ArrowLeft size={18} className="text-[color:var(--color-fg-secondary)]" />
              </button>
              <h1 className="text-lg font-semibold text-[color:var(--color-fg-primary)]">
                Beat Generation
              </h1>
            </div>

            <textarea
              value={music.prompt}
              onChange={(e) => music.setPrompt(e.target.value)}
              placeholder="Describe the beat you want — genre, BPM, drums, bass, mood…"
              maxLength={500}
              rows={4}
              className="w-full p-5 bg-[color:var(--color-surface-raised)] border border-[color:var(--color-border)] rounded-md text-[color:var(--color-fg-primary)] text-[15px] leading-relaxed resize-none focus:outline-none focus:border-[color:var(--color-accent)] transition-colors"
            />

            <div className="flex items-center justify-between mt-3">
              <span className="text-xs text-[color:var(--color-fg-muted)]">
                {music.prompt.length} / 500 characters
              </span>
              <button
                onClick={music.handleGenerate}
                disabled={!music.prompt.trim() || music.status === 'generating'}
                className={`w-40 py-2 rounded-md text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
                  music.prompt.trim() && music.status !== 'generating'
                    ? 'bg-[color:var(--color-accent)] hover:bg-[color:var(--color-accent-dim)] text-white'
                    : 'bg-[color:var(--color-surface-overlay)] text-[color:var(--color-fg-muted)] cursor-not-allowed'
                }`}
              >
                {music.status === 'generating' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Generating...
                  </>
                ) : (
                  <>
                    <Wand2 className="w-4 h-4" /> Generate
                  </>
                )}
              </button>
            </div>

            <div className="mt-6">
              <label className="text-xs font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)] mb-2 block">
                Example Prompts
              </label>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_PROMPTS.map((ex, idx) => (
                  <button
                    key={idx}
                    onClick={() => music.setPrompt(ex)}
                    className="px-3 py-1.5 text-xs bg-[color:var(--color-surface-raised)] hover:bg-[color:var(--color-accent-muted)] border border-[color:var(--color-border)] rounded-md text-[color:var(--color-fg-primary)] hover:text-[color:var(--color-accent)] transition-colors"
                  >
                    {ex.substring(0, 40)}...
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-6">
              <label className="text-xs font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)] mb-2 block">
                Style Tags (Optional)
              </label>
              <div className="flex flex-wrap gap-2">
                {STYLE_TAGS.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => music.toggleTag(tag)}
                    className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                      music.styleTags.includes(tag)
                        ? 'bg-[color:var(--color-accent-muted)] border-[color:var(--color-accent)] text-[color:var(--color-accent)]'
                        : 'bg-[color:var(--color-surface-raised)] border-[color:var(--color-border)] text-[color:var(--color-fg-primary)] hover:border-[color:var(--color-accent)]'
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-6">
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">
                  Duration
                </label>
                <span className="text-sm text-[color:var(--color-fg-primary)] font-mono">
                  {music.duration}s
                </span>
              </div>
              <input
                type="range"
                min="5"
                max="180"
                step="5"
                value={music.duration}
                onChange={(e) => music.setDuration(Number(e.target.value))}
                className="w-full h-2 bg-[color:var(--color-border)] rounded-lg appearance-none cursor-pointer accent-[color:var(--color-accent)]"
              />
              <div className="flex items-center justify-between mt-1 text-xs text-[color:var(--color-fg-muted)]">
                <span>5s</span>
                <span>180s</span>
              </div>
            </div>

            {music.error && (
              <div className="mt-3 px-3 py-2.5 rounded-md bg-[color:var(--color-danger-muted)] border border-[color:var(--color-danger)]">
                <p className="text-[color:var(--color-danger)] text-sm">{music.error}</p>
              </div>
            )}

            {music.status === 'loading' && (
              <div className="mt-10 text-center text-sm text-[color:var(--color-fg-muted)]">
                Loading your beats…
              </div>
            )}

            {/* The audio element is always-mounted (outside the
                tracks.length check). The useAudioPlayer hook attaches
                timeupdate/play/pause listeners on first mount with empty
                deps; if the element didn't exist yet because the list
                was empty, listeners never attached → time display stayed
                frozen and play state was out of sync. */}
            <audio ref={setAudioRef} className="hidden" preload="none" />

            {music.tracks.length > 0 && (
              <div className="mt-10">

                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">
                    Generated Beats ({music.tracks.length})
                  </span>
                </div>

                <div className="border border-[color:var(--color-border)] rounded-md divide-y divide-[color:var(--color-border)] overflow-hidden">
                  {music.tracks.map((track) => {
                    const isActive = track.id === activeId;
                    const playing = isActive && isPlaying;
                    return (
                      <div
                        key={track.id}
                        className={
                          isActive
                            ? 'bg-[color:var(--color-accent-muted)]'
                            : 'bg-[color:var(--color-surface-raised)] hover:bg-[color:var(--color-surface-overlay)]'
                        }
                      >
                        <div className="flex items-center gap-3 px-4 py-2.5">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handlePlayPause(track.id, track.audioUrl);
                            }}
                            className={`w-7 h-7 rounded-md shrink-0 flex items-center justify-center transition-colors ${
                              playing
                                ? 'bg-[color:var(--color-accent)] text-white'
                                : 'bg-[color:var(--color-surface-overlay)] text-[color:var(--color-fg-muted)] hover:bg-[color:var(--color-border)]'
                            }`}
                          >
                            {playing ? (
                              <Pause className="w-3 h-3" fill="white" />
                            ) : (
                              <Play className="w-3 h-3 ml-0.5" />
                            )}
                          </button>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-[color:var(--color-fg-primary)] truncate">
                              {track.prompt}
                            </p>
                            {track.styleTags.length > 0 && (
                              <div className="flex items-center gap-1 mt-0.5 flex-wrap">
                                {track.styleTags.slice(0, 2).map((tag) => (
                                  <span
                                    key={tag}
                                    className="text-[10px] text-[color:var(--color-fg-muted)] bg-[color:var(--color-surface-overlay)] px-1.5 py-0.5 rounded"
                                  >
                                    {tag}
                                  </span>
                                ))}
                                {track.styleTags.length > 2 && (
                                  <span className="text-[10px] text-[color:var(--color-fg-muted)]">
                                    +{track.styleTags.length - 2}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                          <span className="text-xs text-[color:var(--color-fg-muted)] tabular-nums">
                            {formatTime(track.duration)}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              const link = document.createElement('a');
                              link.href = track.audioUrl;
                              link.download = `music-${track.id.slice(0, 8)}.wav`;
                              document.body.appendChild(link);
                              link.click();
                              document.body.removeChild(link);
                            }}
                            className="p-1.5 rounded-md text-[color:var(--color-fg-muted)] hover:text-[color:var(--color-fg-secondary)] transition-colors"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeletingTrackId(track.id);
                            }}
                            className="p-1.5 rounded-md text-[color:var(--color-fg-muted)] hover:text-[color:var(--color-danger)] transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        {isActive && (
                          <div className="px-4 pb-3">
                            <div className="flex items-center gap-2.5">
                              <span
                                className={`text-[10px] font-mono tabular-nums ${
                                  playing
                                    ? 'text-[color:var(--color-fg-secondary)]'
                                    : 'text-[color:var(--color-fg-muted)]'
                                }`}
                              >
                                {formatTime(currentTime)}
                              </span>
                              <AudioWaveform
                                audioRef={audioRef}
                                isPlaying={playing}
                                progress={progress}
                                onSeek={(e) => {
                                  e.stopPropagation();
                                  handleProgressClick(e);
                                }}
                              />
                              <span className="text-[10px] font-mono tabular-nums text-[color:var(--color-fg-muted)]">
                                {formatTime(track.duration)}
                              </span>
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

      <ConfirmModal
        isOpen={deletingTrackId !== null}
        title="Delete beat?"
        message={
          deletingTrack
            ? `"${deletingTrack.prompt.slice(0, 80)}${deletingTrack.prompt.length > 80 ? '…' : ''}" will be permanently deleted.`
            : 'This beat will be permanently deleted.'
        }
        confirmLabel="Delete"
        danger
        onClose={() => setDeletingTrackId(null)}
        onConfirm={async () => {
          if (deletingTrackId) {
            await music.handleDelete(deletingTrackId);
            setDeletingTrackId(null);
          }
        }}
      />
    </div>
  );
}
