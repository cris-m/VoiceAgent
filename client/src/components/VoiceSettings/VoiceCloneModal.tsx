import { X, Upload, Check } from 'lucide-react';
import type { UseVoiceCloneReturn } from '@typing';
import type { Language } from '@pages/Narrate/Narrate.types';

interface VoiceCloneModalProps {
  clone: UseVoiceCloneReturn;
  languages: Language[];
  onSubmit: () => Promise<void>;
}

export function VoiceCloneModal({ clone, languages, onSubmit }: VoiceCloneModalProps) {
  const {
    showCloneModal,
    setShowCloneModal,
    cloneFile,
    cloneName,
    setCloneName,
    cloneTranscript,
    setCloneTranscript,
    cloneLanguage,
    setCloneLanguage,
    cloningStatus,
    cloneError,
    handleCloneFileSelect,
    resetCloneForm,
    cloneFileInputRef,
  } = clone;

  if (!showCloneModal) return null;

  const isSubmitting = cloningStatus === 'cloning';
  const isSuccess = cloningStatus === 'success';
  const hasFile = cloneFile !== null;
  const fileName = cloneFile?.name ?? '';
  const trimmedName = cloneName.trim();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="w-full max-w-md mx-4 bg-[color:var(--color-surface-raised)] border border-[color:var(--color-border)] rounded-lg shadow-xl">
        <div className="p-5 border-b border-[color:var(--color-border)] flex items-center justify-between">
          <h2 className="text-base font-semibold text-[color:var(--color-fg-primary)]">Clone voice</h2>
          <button
            onClick={() => {
              setShowCloneModal(false);
              resetCloneForm();
            }}
            className="p-1 rounded-md hover:bg-[color:var(--color-surface-overlay)] text-[color:var(--color-fg-muted)]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="text-sm font-medium text-[color:var(--color-fg-secondary)] mb-1.5 block">
              Reference audio
            </label>
            <input
              ref={cloneFileInputRef}
              type="file"
              accept="audio/*"
              onChange={handleCloneFileSelect}
              className="hidden"
            />
            <button
              onClick={() => cloneFileInputRef.current?.click()}
              disabled={isSubmitting}
              className={`w-full p-5 rounded-md border-2 border-dashed transition-colors flex flex-col items-center gap-1.5 ${
                hasFile
                  ? 'border-slate-300 bg-[color:var(--color-accent-muted)]/50'
                  : 'border-[color:var(--color-border)] hover:border-[color:var(--color-border-strong)]'
              } ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {hasFile ? (
                <>
                  <Check className="w-5 h-5 text-slate-500" />
                  <span className="text-sm text-[color:var(--color-fg-secondary)]">{fileName}</span>
                </>
              ) : (
                <>
                  <Upload className="w-5 h-5 text-[color:var(--color-fg-muted)]" />
                  <span className="text-sm text-[color:var(--color-fg-secondary)]">Upload audio file</span>
                </>
              )}
            </button>
          </div>

          <div>
            <label className="text-sm font-medium text-[color:var(--color-fg-secondary)] mb-1.5 block">
              Name
            </label>
            <input
              type="text"
              value={cloneName}
              onChange={(e) => setCloneName(e.target.value)}
              placeholder="e.g., My Voice"
              disabled={isSubmitting}
              className="w-full px-3 py-2.5 rounded-md border border-[color:var(--color-border)] text-sm text-[color:var(--color-fg-primary)] placeholder-gray-400 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-[color:var(--color-fg-secondary)] mb-1.5 block">
              Language
            </label>
            <select
              value={cloneLanguage}
              onChange={(e) => setCloneLanguage(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-3 py-2.5 rounded-md border border-[color:var(--color-border)] text-sm text-[color:var(--color-fg-primary)] focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500/20 disabled:opacity-50 disabled:cursor-not-allowed bg-[color:var(--color-surface-raised)]"
            >
              {languages.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-[color:var(--color-fg-secondary)] mb-1.5 block">
              Transcript (optional)
            </label>
            <textarea
              value={cloneTranscript}
              onChange={(e) => setCloneTranscript(e.target.value)}
              placeholder="Leave empty to use speaker embedding only"
              disabled={isSubmitting}
              rows={3}
              className="w-full px-3 py-2.5 rounded-md border border-[color:var(--color-border)] text-sm text-[color:var(--color-fg-primary)] placeholder-gray-400 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500/20 resize-none disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>

          {cloneError && (
            <div className="px-3 py-2.5 rounded-md bg-red-50 border border-red-100">
              <p className="text-red-600 text-sm">{cloneError}</p>
            </div>
          )}

          {isSuccess && (
            <div className="px-3 py-2.5 rounded-md bg-green-50 border border-green-100">
              <p className="text-green-600 text-sm">Voice cloned successfully!</p>
            </div>
          )}
        </div>

        <div className="p-5 border-t border-[color:var(--color-border)] flex gap-2">
          <button
            onClick={() => {
              setShowCloneModal(false);
              resetCloneForm();
            }}
            disabled={isSubmitting}
            className="flex-1 px-4 py-2.5 rounded-md border border-[color:var(--color-border)] text-[color:var(--color-fg-secondary)] hover:bg-[color:var(--color-surface-overlay)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
          >
            Cancel
          </button>
          <button
            onClick={onSubmit}
            disabled={!hasFile || !trimmedName || isSubmitting}
            className="flex-1 px-4 py-2.5 rounded-md bg-[color:var(--color-accent)] text-white hover:bg-[color:var(--color-accent-dim)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
          >
            {isSubmitting ? 'Cloning...' : 'Clone voice'}
          </button>
        </div>
      </div>
    </div>
  );
}
