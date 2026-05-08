import { useRef, useState, useEffect, useCallback } from 'react';
import type { UseAudioPlayerReturn } from '@typing';

export function useAudioPlayer(): UseAudioPlayerReturn {
  const audioRef = useRef<HTMLAudioElement>(null);
  // State copy of the same node so listener effects re-run when the
  // <audio> element mounts/remounts.
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);

  const handlePlayPause = useCallback(
    async (id: string, url: string) => {
      if (!audioRef.current) return;

      // Compare by id, not src — browser resolves src to an absolute URL
      // so the original `audioRef.current.src === url` check never matched.
      if (activeId === id) {
        if (isPlaying) {
          audioRef.current.pause();
          setIsPlaying(false);
        } else {
          try {
            await audioRef.current.play();
            setIsPlaying(true);
          } catch {
            setIsPlaying(false);
          }
        }
      } else {
        setActiveId(id);
        audioRef.current.src = url;
        try {
          await audioRef.current.play();
          setIsPlaying(true);
          setProgress(0);
          setCurrentTime(0);
        } catch {
          setIsPlaying(false);
        }
      }
    },
    [activeId, isPlaying]
  );

  const handleProgressClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current?.duration) return;

    const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    audioRef.current.currentTime = percent * audioRef.current.duration;
  }, []);

  const handleSelect = useCallback((id: string) => {
    setActiveId(id);
    setIsPlaying(false);
    setProgress(0);
    setCurrentTime(0);
  }, []);

  useEffect(() => {
    if (!audioElement) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audioElement.currentTime);
      if (audioElement.duration) {
        setProgress((audioElement.currentTime / audioElement.duration) * 100);
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setProgress(0);
      setCurrentTime(0);
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    audioElement.addEventListener('timeupdate', handleTimeUpdate);
    audioElement.addEventListener('ended', handleEnded);
    audioElement.addEventListener('play', handlePlay);
    audioElement.addEventListener('pause', handlePause);

    return () => {
      audioElement.removeEventListener('timeupdate', handleTimeUpdate);
      audioElement.removeEventListener('ended', handleEnded);
      audioElement.removeEventListener('play', handlePlay);
      audioElement.removeEventListener('pause', handlePause);
    };
  }, [audioElement]);

  const setAudioRef = useCallback((node: HTMLAudioElement | null) => {
    audioRef.current = node;
    setAudioElement(node);
  }, []);

  return {
    audioRef,
    setAudioRef,
    progress,
    currentTime,
    isPlaying,
    activeId,
    handlePlayPause,
    handleProgressClick,
    handleSelect,
  };
}
