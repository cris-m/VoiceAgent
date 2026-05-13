import { useState, useRef, useCallback, useEffect } from 'react';
import { Upload, FileAudio, Loader2, X, Check, Copy, Mic2, Clock, Languages, Trash2, Play, Pause, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router';
import { formatTime, formatFileSize } from '@utils/index';
import { useTranscribeMutation } from '@/services/voice';
import { AudioWaveform } from '@components/ui';
import { ConfirmModal } from '@components/Chat';
import type { TranscriptionStatus, TranscriptionResult } from './Transcribe.types';

const ACCEPTED_FORMATS = ['audio/wav', 'audio/mpeg', 'audio/ogg', 'audio/flac', 'audio/mp3'];
const ACCEPTED_EXTENSIONS = '.wav,.mp3,.ogg,.flac';

export function TranscribePage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<TranscriptionStatus>('idle');
  const [transcriptions, setTranscriptions] = useState<TranscriptionResult[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmClearAll, setConfirmClearAll] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  const [transcribe] = useTranscribeMutation();

  const selectedTranscription = transcriptions.find(t => t.id === selectedId);

  useEffect(() => {
    return () => {
      transcriptions.forEach(t => URL.revokeObjectURL(t.audioUrl));
    };
  }, [transcriptions]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onTime = () => {
      setCurrentTime(audio.currentTime);
      if (audio.duration) setProgress((audio.currentTime / audio.duration) * 100);
    };
    const onEnded = () => {
      setPlayingId(null);
      setProgress(0);
      setCurrentTime(0);
    };
    audio.addEventListener('timeupdate', onTime);
    audio.addEventListener('ended', onEnded);
    return () => {
      audio.removeEventListener('timeupdate', onTime);
      audio.removeEventListener('ended', onEnded);
    };
  }, [selectedId]);

  const handleFileSelect = useCallback((selectedFile: File) => {
    if (!ACCEPTED_FORMATS.includes(selectedFile.type) &&
        !selectedFile.name.match(/\.(wav|mp3|ogg|flac)$/i)) {
      setError('Please select a valid audio file (WAV, MP3, OGG, or FLAC)');
      return;
    }
    const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
    if (selectedFile.size > MAX_FILE_SIZE) {
      setError(`File size exceeds 50MB limit (${(selectedFile.size / 1024 / 1024).toFixed(1)}MB)`);
      return;
    }
    setFile(selectedFile);
    setError(null);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) handleFileSelect(droppedFile);
  }, [handleFileSelect]);

  const handleSubmit = async () => {
    if (!file) return;
    setStatus('uploading');
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const data = await transcribe(formData).unwrap();
      const audioUrl = URL.createObjectURL(file);
      const newTranscription: TranscriptionResult = {
        id: `transcription-${Date.now()}`,
        text: data.text || '',
        duration: data.duration_seconds || 0,
        language: data.language ?? undefined,
        fileName: file.name,
        fileSize: file.size,
        audioUrl,
        createdAt: new Date(),
      };
      setTranscriptions(prev => [newTranscription, ...prev]);
      setSelectedId(newTranscription.id);
      setStatus('success');
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      const e = err as { error?: { message?: string } };
      setError(e.error?.message ?? 'Transcription failed');
      setStatus('error');
    }
  };

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleDelete = (id: string) => {
    const toDelete = transcriptions.find(t => t.id === id);
    if (toDelete) URL.revokeObjectURL(toDelete.audioUrl);
    setTranscriptions(prev => prev.filter(t => t.id !== id));
    if (selectedId === id) { setSelectedId(null); setPlayingId(null); }
  };

  const handlePlayPause = (id: string) => {
    if (playingId === id) {
      audioRef.current?.pause();
      setPlayingId(null);
    } else {
      if (selectedId !== id) {
        setSelectedId(id);
        setProgress(0);
        setCurrentTime(0);
      }
      setTimeout(() => { audioRef.current?.play(); setPlayingId(id); }, 100);
    }
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current?.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    audioRef.current.currentTime = ((e.clientX - rect.left) / rect.width) * audioRef.current.duration;
  };

  return (
    <div className="flex-1 flex min-h-0 overflow-hidden">
      {/* Always-mount the audio element so the timeupdate / ended listeners
          attach immediately on first render. Conditionally rendering it
          tied to `selectedTranscription` made the listeners attach late
          (or never) and the time display stayed frozen. */}
      <audio
        ref={audioRef}
        src={selectedTranscription?.audioUrl}
        className="hidden"
      />

      <div className="w-[400px] border-r border-[color:var(--color-border)] bg-[color:var(--color-surface-raised)] flex flex-col shrink-0">
        <div className="p-5 border-b border-[color:var(--color-border)]">
          <div className="flex items-center gap-2 mb-2">
            <button
              onClick={() => navigate('/')}
              className="p-1 hover:bg-[color:var(--color-surface-base)] rounded-md transition-colors"
              aria-label="Go back"
            >
              <ArrowLeft size={18} className="text-[color:var(--color-fg-secondary)]" />
            </button>
            <h1 className="text-lg font-semibold text-[color:var(--color-fg-primary)]">Transcribe</h1>
          </div>
          <p className="text-sm text-[color:var(--color-fg-muted)] ml-8">Upload audio to convert speech to text</p>
        </div>

        <div className="p-4">
          <div
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={(e) => { e.preventDefault(); setIsDragOver(false); }}
            className={`
              border-2 border-dashed rounded-md cursor-pointer transition-all py-6 px-4
              flex flex-col items-center justify-center text-center
              ${isDragOver
                ? 'border-[color:var(--color-accent)] bg-[color:var(--color-accent-muted)]'
                : file
                  ? 'border-[color:var(--color-accent-dim)] bg-[color:var(--color-accent-muted)]/50'
                  : 'border-[color:var(--color-border)] hover:border-[color:var(--color-border-strong)] hover:bg-[color:var(--color-surface-overlay)]'
              }
            `}
          >
            <input ref={fileInputRef} type="file" accept={ACCEPTED_EXTENSIONS}
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFileSelect(f); }}
              className="hidden" />

            {file ? (
              <>
                <FileAudio className="w-8 h-8 text-[color:var(--color-accent)] mb-2" />
                <p
                  className="text-sm font-medium text-[color:var(--color-fg-primary)] max-w-full truncate px-4"
                  title={file.name}
                >
                  {file.name}
                </p>
                <p className="text-xs text-[color:var(--color-fg-muted)] mt-0.5">{formatFileSize(file.size)}</p>
                <button
                  onClick={(e) => { e.stopPropagation(); setFile(null); setError(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                  className="mt-2 text-xs text-[color:var(--color-fg-muted)] hover:text-[color:var(--color-danger)] flex items-center gap-1 transition-colors"
                >
                  <X className="w-3.5 h-3.5" /> Remove
                </button>
              </>
            ) : (
              <>
                <Upload className={`w-8 h-8 mb-2 ${isDragOver ? 'text-[color:var(--color-accent)]' : 'text-[color:var(--color-fg-muted)]'}`} />
                <p className="text-sm font-medium text-[color:var(--color-fg-secondary)]">
                  {isDragOver ? 'Drop here' : 'Drop audio file or click to browse'}
                </p>
                <div className="flex gap-1.5 mt-2">
                  {['WAV', 'MP3', 'OGG', 'FLAC'].map(f => (
                    <span key={f} className="text-[10px] px-1.5 py-0.5 rounded bg-[color:var(--color-surface-overlay)] text-[color:var(--color-fg-muted)] font-medium">{f}</span>
                  ))}
                </div>
              </>
            )}
          </div>

          {error && (
            <div className="mt-3 px-3 py-2.5 rounded-md bg-[color:var(--color-danger-muted)] border border-[color:var(--color-danger)]">
              <p className="text-[color:var(--color-danger)] text-sm">{error}</p>
            </div>
          )}

          <div className="flex justify-end mt-3">
            <button
              onClick={handleSubmit}
              disabled={!file || status === 'uploading'}
              className={`px-4 py-2 rounded-md text-sm font-medium flex items-center gap-2 transition-colors ${
                file && status !== 'uploading'
                  ? 'bg-[color:var(--color-accent)] hover:bg-[color:var(--color-accent-dim)] text-white'
                  : 'bg-[color:var(--color-surface-overlay)] text-[color:var(--color-fg-muted)] cursor-not-allowed'
              }`}
            >
              {status === 'uploading' ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Transcribing...</>
              ) : (
                <><Mic2 className="w-4 h-4" /> Transcribe</>
              )}
            </button>
          </div>
        </div>

        {transcriptions.length > 0 && (
          <div className="flex-1 overflow-y-auto scrollbar-thin border-t border-[color:var(--color-border)]">
            <div className="flex items-center justify-between px-4 py-3">
              <span className="text-[11px] font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">
                History ({transcriptions.length})
              </span>
              <button
                onClick={() => setConfirmClearAll(true)}
                className="text-xs text-[color:var(--color-fg-muted)] hover:text-[color:var(--color-danger)] transition-colors"
              >
                Clear all
              </button>
            </div>

            <div>
              {transcriptions.map((t) => {
                const isSelected = t.id === selectedId;
                const isPlaying = t.id === playingId;
                return (
                  <div
                    key={t.id}
                    onClick={() => { setSelectedId(t.id); setProgress(0); setCurrentTime(0); }}
                    className={`group flex items-center gap-2.5 px-4 py-2.5 cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-[color:var(--color-accent-muted)]'
                        : 'hover:bg-[color:var(--color-surface-overlay)]'
                    }`}
                  >
                    <button
                      onClick={(e) => { e.stopPropagation(); handlePlayPause(t.id); }}
                      className={`w-7 h-7 rounded-md shrink-0 flex items-center justify-center transition-colors ${
                        isPlaying ? 'bg-[color:var(--color-accent)] text-white' : 'bg-[color:var(--color-surface-overlay)] text-[color:var(--color-fg-muted)] hover:bg-[color:var(--color-border)]'
                      }`}
                    >
                      {isPlaying ? <Pause className="w-3 h-3" fill="white" /> : <Play className="w-3 h-3 ml-0.5" />}
                    </button>

                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-[color:var(--color-fg-primary)] font-medium truncate block">{t.fileName}</span>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-xs text-[color:var(--color-fg-muted)] tabular-nums">{formatTime(t.duration)}</span>
                        <span className="text-xs text-[color:var(--color-fg-muted)]">{formatFileSize(t.fileSize)}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleCopy(t.text, t.id); }}
                        className={`p-1.5 rounded-md transition-colors ${
                          copied === t.id ? 'text-[color:var(--color-success)]' : 'text-[color:var(--color-fg-muted)] hover:text-[color:var(--color-fg-secondary)]'
                        }`}
                      >
                        {copied === t.id ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); setDeletingId(t.id); }}
                        className="p-1.5 rounded-md text-[color:var(--color-fg-muted)] hover:text-[color:var(--color-danger)] transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 bg-[color:var(--color-surface-base)] flex flex-col">
        {selectedTranscription ? (
          <>
            <div className="bg-[color:var(--color-surface-raised)] border-b border-[color:var(--color-border)] px-6 py-3">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => handlePlayPause(selectedTranscription.id)}
                  className={`w-8 h-8 rounded-md shrink-0 flex items-center justify-center transition-colors ${
                    playingId === selectedTranscription.id ? 'bg-[color:var(--color-accent)] text-white' : 'bg-[color:var(--color-surface-overlay)] text-[color:var(--color-fg-secondary)] hover:bg-[color:var(--color-border)]'
                  }`}
                >
                  {playingId === selectedTranscription.id
                    ? <Pause className="w-3.5 h-3.5" fill="white" />
                    : <Play className="w-3.5 h-3.5 ml-0.5" />}
                </button>
                <span
                  className={`text-[11px] font-mono tabular-nums ${
                    playingId === selectedTranscription.id
                      ? 'text-[color:var(--color-fg-secondary)]'
                      : 'text-[color:var(--color-fg-muted)]'
                  }`}
                >
                  {formatTime(currentTime)}
                </span>
                <AudioWaveform
                  audioRef={audioRef}
                  isPlaying={playingId === selectedTranscription.id}
                  progress={progress}
                  onSeek={handleProgressClick}
                />
                <span className="text-[11px] font-mono tabular-nums text-[color:var(--color-fg-muted)]">
                  {formatTime(selectedTranscription.duration)}
                </span>
              </div>
              <p
                className="text-sm font-medium text-[color:var(--color-fg-primary)] mt-2 truncate"
                title={selectedTranscription.fileName}
              >
                {selectedTranscription.fileName}
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin">
              <div className="bg-[color:var(--color-surface-raised)] border border-[color:var(--color-border)] rounded-md p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">Transcript</span>
                  <button
                    onClick={() => handleCopy(selectedTranscription.text, selectedTranscription.id)}
                    className={`p-1.5 rounded-md text-sm transition-colors ${
                      copied === selectedTranscription.id ? 'text-[color:var(--color-success)]' : 'text-[color:var(--color-fg-muted)] hover:text-[color:var(--color-fg-secondary)]'
                    }`}
                  >
                    {copied === selectedTranscription.id ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <p className="text-[14px] leading-relaxed text-[color:var(--color-fg-primary)] whitespace-pre-wrap">
                  {selectedTranscription.text || 'No speech detected in the audio.'}
                </p>
              </div>

              <div className="flex items-center gap-4 mt-4">
                {selectedTranscription.language && (
                  <span className="inline-flex items-center gap-1 text-xs text-[color:var(--color-fg-muted)]">
                    <Languages className="w-3 h-3" /> {selectedTranscription.language}
                  </span>
                )}
                <span className="inline-flex items-center gap-1 text-xs text-[color:var(--color-fg-muted)]">
                  <Clock className="w-3 h-3" /> {formatTime(selectedTranscription.duration)}
                </span>
                <span className="text-xs text-[color:var(--color-fg-muted)]">{formatFileSize(selectedTranscription.fileSize)}</span>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <FileAudio className="w-10 h-10 text-[color:var(--color-fg-muted)] mx-auto mb-3" />
              <p className="text-sm text-[color:var(--color-fg-muted)]">Select a transcription to view details</p>
            </div>
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={deletingId !== null}
        title="Delete transcription?"
        message={(() => {
          const t = transcriptions.find((x) => x.id === deletingId);
          return t
            ? `"${t.fileName}" and its transcript will be permanently deleted.`
            : 'This transcription will be permanently deleted.';
        })()}
        confirmLabel="Delete"
        danger
        onClose={() => setDeletingId(null)}
        onConfirm={() => {
          if (deletingId) {
            handleDelete(deletingId);
            setDeletingId(null);
          }
        }}
      />

      <ConfirmModal
        isOpen={confirmClearAll}
        title="Clear all transcriptions?"
        message={`All ${transcriptions.length} transcription${transcriptions.length === 1 ? '' : 's'} will be permanently deleted.`}
        confirmLabel="Clear all"
        danger
        onClose={() => setConfirmClearAll(false)}
        onConfirm={() => {
          transcriptions.forEach((t) => URL.revokeObjectURL(t.audioUrl));
          setTranscriptions([]);
          setSelectedId(null);
          setPlayingId(null);
          setConfirmClearAll(false);
        }}
      />
    </div>
  );
}
