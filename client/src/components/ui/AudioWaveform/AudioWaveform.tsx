import { useEffect, useRef, useState } from 'react';

/* createMediaElementSource can only be called ONCE per element (browser
   constraint), so the AudioContext / source / analyser are cached on
   the element itself via a non-enumerable property — this makes
   subsequent re-mounts of this component cheap and safe. */

const NUM_BARS = 48;

interface AudioWaveformProps {
  audioRef: React.RefObject<HTMLAudioElement | null>;
  isPlaying: boolean;
  /** 0–100 progress percentage. Determines the filled/dimmed split. */
  progress: number;
  /** Click handler — wire to seek logic. Receives the click event so the
   *  caller can compute the click position from rect/clientX. */
  onSeek?: (e: React.MouseEvent<HTMLDivElement>) => void;
  /** Override container height in px. Default 28 (~h-7). */
  height?: number;
}

export function AudioWaveform({
  audioRef,
  isPlaying,
  progress,
  onSeek,
  height = 28,
}: AudioWaveformProps) {
  const [bars, setBars] = useState<number[]>(() => new Array(NUM_BARS).fill(0));
  const rafRef = useRef<number | null>(null);
  const smoothedRef = useRef<number[]>(new Array(NUM_BARS).fill(0));

  useEffect(() => {
    const audioEl = audioRef.current;
    if (!audioEl) return;

    type CachedAudio = HTMLAudioElement & {
      __waveCtx?: AudioContext;
      __waveAnalyser?: AnalyserNode;
    };
    const cached = audioEl as CachedAudio;

    if (!cached.__waveAnalyser) {
      try {
        const ctx = new AudioContext();
        const source = ctx.createMediaElementSource(audioEl);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 128;
        analyser.smoothingTimeConstant = 0.7;
        source.connect(analyser);
        analyser.connect(ctx.destination);
        cached.__waveCtx = ctx;
        cached.__waveAnalyser = analyser;
      } catch {
        return;
      }
    }

    const analyser = cached.__waveAnalyser!;
    const ctx = cached.__waveCtx!;
    if (ctx.state === 'suspended' && isPlaying) ctx.resume().catch(() => {});

    if (!isPlaying) {
      let alive = true;
      const decay = () => {
        if (!alive) return;
        let stillMoving = false;
        for (let i = 0; i < NUM_BARS; i++) {
          smoothedRef.current[i] *= 0.85;
          if (smoothedRef.current[i] > 0.01) stillMoving = true;
        }
        setBars([...smoothedRef.current]);
        if (stillMoving) rafRef.current = requestAnimationFrame(decay);
      };
      rafRef.current = requestAnimationFrame(decay);
      return () => {
        alive = false;
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
      };
    }

    const bins = new Uint8Array(analyser.frequencyBinCount);
    let alive = true;

    const tick = () => {
      if (!alive) return;
      analyser.getByteFrequencyData(bins);

      const usableBins = Math.floor(bins.length * 0.75);
      const perBar = usableBins / NUM_BARS;
      const next = new Array<number>(NUM_BARS);
      for (let i = 0; i < NUM_BARS; i++) {
        const start = Math.floor(i * perBar);
        const end = Math.floor((i + 1) * perBar);
        let sum = 0;
        for (let j = start; j < end; j++) sum += bins[j];
        const avg = end > start ? sum / (end - start) : 0;
        const norm = Math.min(1, (avg / 255) * 1.6);
        smoothedRef.current[i] = smoothedRef.current[i] * 0.55 + norm * 0.45;
        next[i] = smoothedRef.current[i];
      }
      setBars(next);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      alive = false;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [isPlaying, audioRef]);

  return (
    <div
      className="flex-1 flex items-center gap-[2px] cursor-pointer select-none"
      style={{ height }}
      onClick={onSeek}
      role="slider"
      aria-label="Seek"
      aria-valuenow={Math.round(progress)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      {bars.map((amp, i) => {
        const filled = (i / NUM_BARS) * 100 <= progress;
        const heightPct = Math.max(8, amp * 100);
        return (
          <div
            key={i}
            style={{
              flex: 1,
              height: `${heightPct}%`,
              minHeight: '2px',
              borderRadius: '1.5px',
              backgroundColor: filled
                ? 'var(--color-accent)'
                : 'var(--color-border-strong)',
              opacity: filled ? 1 : 0.6,
              transition: 'background-color 120ms, opacity 120ms',
            }}
          />
        );
      })}
    </div>
  );
}
