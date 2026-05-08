import { useState, useCallback, useMemo } from 'react';
import {
  useGetMusicListQuery,
  useGenerateMusicMutation,
  useDeleteMusicMutation,
} from '@/services/music';

type MusicStatus = 'idle' | 'generating' | 'success' | 'error' | 'loading';

export interface GeneratedTrack {
  id: string;
  prompt: string;
  styleTags: string[];
  duration: number;
  audioUrl: string;
  voice_name?: string;
  created_at?: string;
}

export function useMusic() {
  const [prompt, setPrompt] = useState('');
  const [styleTags, setStyleTags] = useState<string[]>([]);
  const [duration, setDuration] = useState(30);
  const [error, setError] = useState<string | null>(null);

  const { data: rawTracks, isLoading: loading } = useGetMusicListQuery();
  const [generateMusic, generateState] = useGenerateMusicMutation();
  const [deleteMusic] = useDeleteMusicMutation();

  const tracks: GeneratedTrack[] = useMemo(
    () =>
      (rawTracks ?? []).map((item) => ({
        id: item.id,
        prompt: item.prompt,
        styleTags: item.voice_name
          ? item.voice_name.split(', ').filter((t) => t)
          : [],
        duration: item.duration,
        audioUrl: item.url,
        voice_name: item.voice_name,
        created_at: item.created_at,
      })),
    [rawTracks],
  );

  const status: MusicStatus = loading
    ? 'loading'
    : generateState.isLoading
      ? 'generating'
      : generateState.isError
        ? 'error'
        : generateState.isSuccess
          ? 'success'
          : 'idle';

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim() || generateState.isLoading) return;
    setError(null);
    try {
      await generateMusic({
        prompt: prompt.trim(),
        style_tags: styleTags,
        duration,
      }).unwrap();
    } catch (err) {
      const e = err as { error?: { message?: string } };
      setError(e.error?.message ?? 'Generation failed');
    }
  }, [prompt, styleTags, duration, generateMusic, generateState.isLoading]);

  const handleDelete = useCallback(
    async (id: string) => {
      try {
        await deleteMusic(id).unwrap();
      } catch (err) {
        console.error('[useMusic] Delete failed:', err);
      }
    },
    [deleteMusic],
  );

  const toggleTag = useCallback((tag: string) => {
    setStyleTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  }, []);

  return {
    prompt,
    setPrompt,
    styleTags,
    toggleTag,
    duration,
    setDuration,
    status,
    error,
    tracks,
    handleGenerate,
    handleDelete,
  };
}
