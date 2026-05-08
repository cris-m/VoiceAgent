import { useState, useRef, useCallback } from 'react';
import type { Voice } from '@pages/Narrate/Narrate.types';
import type { UseVoiceCloneReturn } from '@typing';
import {
  useCloneVoiceMutation,
  useDeleteCloneVoiceMutation,
} from '@/services/voice';

export function useVoiceClone(): UseVoiceCloneReturn {
  const [showCloneModal, setShowCloneModal] = useState(false);
  const [cloneFile, setCloneFile] = useState<File | null>(null);
  const [cloneName, setCloneName] = useState('');
  const [cloneTranscript, setCloneTranscript] = useState('');
  const [cloneLanguage, setCloneLanguage] = useState('auto');
  const [cloneError, setCloneError] = useState<string | null>(null);
  const cloneFileInputRef = useRef<HTMLInputElement>(null);

  const [cloneVoiceMutation, cloneState] = useCloneVoiceMutation();
  const [deleteCloneVoiceMutation] = useDeleteCloneVoiceMutation();

  const cloningStatus: 'idle' | 'cloning' | 'success' | 'error' = cloneState.isLoading
    ? 'cloning'
    : cloneState.isError
      ? 'error'
      : cloneState.isSuccess
        ? 'success'
        : 'idle';

  const handleCloneFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) {
        setCloneFile(f);
        if (!cloneName) {
          const baseName = f.name.replace(/\.[^/.]+$/, '');
          setCloneName(baseName.charAt(0).toUpperCase() + baseName.slice(1));
        }
      }
    },
    [cloneName],
  );

  const resetCloneForm = useCallback(() => {
    setCloneFile(null);
    setCloneName('');
    setCloneTranscript('');
    setCloneLanguage('auto');
    setCloneError(null);
    if (cloneFileInputRef.current) cloneFileInputRef.current.value = '';
  }, []);

  const handleCloneVoice = useCallback(async () => {
    if (!cloneFile || !cloneName.trim()) return;
    setCloneError(null);
    try {
      const fd = new FormData();
      fd.append('file', cloneFile);
      fd.append('name', cloneName.trim());
      fd.append('language', cloneLanguage);
      if (cloneTranscript.trim()) fd.append('ref_text', cloneTranscript.trim());
      fd.append('x_vector_only', cloneTranscript.trim() ? 'false' : 'true');

      await cloneVoiceMutation(fd).unwrap();

      setTimeout(() => {
        setShowCloneModal(false);
        resetCloneForm();
      }, 1500);
    } catch (err) {
      const e = err as { error?: { message?: string } };
      setCloneError(e.error?.message ?? 'Cloning failed');
    }
  }, [cloneFile, cloneName, cloneLanguage, cloneTranscript, cloneVoiceMutation, resetCloneForm]);

  const handleDeleteClonedVoice = useCallback(
    async (
      id: string,
      voices: Voice[],
      selectedVoice: string,
      setSelectedVoice: (id: string) => void,
    ) => {
      if (!id.startsWith('clone_')) return;
      try {
        await deleteCloneVoiceMutation(id).unwrap();

        if (selectedVoice === id) {
          const remaining = voices.filter((v) => v.id !== id);
          if (remaining.length > 0) setSelectedVoice(remaining[0].id);
        }
      } catch (err) {
        console.error('[useVoiceClone] Delete failed:', err);
      }
    },
    [deleteCloneVoiceMutation],
  );

  return {
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
    handleCloneVoice,
    handleDeleteClonedVoice,
    resetCloneForm,
    cloneFileInputRef,
  };
}
