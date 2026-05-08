import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type { Voice, Language, GeneratedAudio, NarrationStatus } from '@pages/Narrate/Narrate.types';
import type { UseNarrateReturn } from '@typing';
import {
  useGetVoicesQuery,
  useGetLanguagesQuery,
  useGetVoiceConfigQuery,
  useGetNarrationsQuery,
  useNarrateMutation,
  usePreviewVoiceMutation,
  useDeleteNarrationMutation,
} from '@/services/voice';

export function useNarrate(): UseNarrateReturn {
  const [text, setText] = useState('');
  const [selectedVoice, setSelectedVoice] = useState<string>('');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('auto');
  const [speed, setSpeed] = useState(1.0);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [previewingVoice, setPreviewingVoice] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);

  const { data: voicesData, isLoading: loadingVoices } = useGetVoicesQuery();
  const { data: languagesData } = useGetLanguagesQuery();
  const { data: configData } = useGetVoiceConfigQuery();
  const { data: narrationsData } = useGetNarrationsQuery();

  const voices: Voice[] = useMemo(() => voicesData?.voices ?? [], [voicesData]);
  const languages: Language[] = useMemo(
    () => languagesData?.languages ?? [],
    [languagesData],
  );
  const supportsCloning = configData?.supports_cloning ?? false;
  const supportsSpeed = configData?.supports_speed ?? false;
  const supportsLanguage = configData?.supports_language ?? false;

  const generatedAudios: GeneratedAudio[] = useMemo(
    () =>
      (narrationsData ?? []).map((item) => ({
        id: item.id,
        text: item.prompt,
        voiceId: item.voice_name,
        voiceName: item.voice_name,
        speed: 1.0,
        audioUrl: item.url,
        duration: item.duration,
        createdAt: new Date(item.created_at),
      })),
    [narrationsData],
  );

  useEffect(() => {
    if (voicesData && !selectedVoice) {
      setSelectedVoice(voicesData.default_voice || voicesData.voices[0]?.id || '');
    }
  }, [voicesData, selectedVoice]);

  useEffect(() => {
    if (languagesData) {
      setSelectedLanguage((prev) =>
        prev === 'auto' ? (languagesData.default_language ?? 'auto') : prev,
      );
    }
  }, [languagesData]);

  const [narrate, narrateState] = useNarrateMutation();
  const [previewVoice] = usePreviewVoiceMutation();
  const [deleteNarration] = useDeleteNarrationMutation();

  const status: NarrationStatus = narrateState.isLoading
    ? 'generating'
    : narrateState.isError
      ? 'error'
      : narrateState.isSuccess
        ? 'success'
        : 'idle';

  const handleGenerate = useCallback(async () => {
    if (!text.trim()) return;
    setError(null);
    try {
      await narrate({
        text: text.trim(),
        voice_id: selectedVoice,
        speed,
        language: selectedLanguage,
      }).unwrap();
      setProgress(0);
    } catch (err) {
      const e = err as { error?: { message?: string }; status?: number };
      setError(e.error?.message ?? 'Narration failed');
    }
  }, [text, selectedVoice, speed, selectedLanguage, narrate]);

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteNarration(id).unwrap();
      } catch (err) {
        console.error('[useNarrate] Delete failed:', err);
      }
    },
    [deleteNarration],
  );

  const handlePreviewVoice = useCallback(
    async (voiceId: string) => {
      if (previewingVoice === voiceId) {
        previewAudioRef.current?.pause();
        setPreviewingVoice(null);
        return;
      }
      setPreviewingVoice(voiceId);
      try {
        const voice = voices.find((v) => v.id === voiceId);
        const meta = await previewVoice({
          text: voice?.preview_text || `Hi! I'm ${voice?.name}.`,
          voice_id: voiceId,
          speed,
          language: voice?.language || 'auto',
        }).unwrap();
        previewAudioRef.current?.pause();
        const audio = new Audio(meta.url);
        previewAudioRef.current = audio;
        audio.onended = () => setPreviewingVoice(null);
        audio.onerror = () => setPreviewingVoice(null);
        await audio.play();
      } catch (err) {
        console.error('[useNarrate] Preview failed:', err);
        setPreviewingVoice(null);
      }
    },
    [previewingVoice, voices, previewVoice, speed],
  );

  const handleCopyText = useCallback(async (id: string, t: string) => {
    await navigator.clipboard.writeText(t);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

  useEffect(() => {
    return () => {
      previewAudioRef.current?.pause();
    };
  }, []);

  return {
    text,
    setText,
    voices,
    selectedVoice,
    setSelectedVoice,
    languages,
    selectedLanguage,
    setSelectedLanguage,
    speed,
    setSpeed,
    status,
    error,
    generatedAudios,
    loadingVoices,
    progress,
    handleGenerate,
    previewingVoice,
    handlePreviewVoice,
    handleCopyText,
    copiedId,
    supportsCloning,
    supportsSpeed,
    supportsLanguage,
    handleDelete,
  };
}
