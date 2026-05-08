import { AnimatePresence, motion, type Variants } from 'motion/react';
import { useEffect, useRef, useState } from 'react';
import type { OrbState, VoiceOrbProps } from './VoiceOrb.types';

const SIZE_CONFIG = {
  hero:    { container: 360, orb: 220, gap: 40, fontSize: '18px', statusGap: '32px' },
  active:  { container: 140, orb: 100, gap: 12, fontSize: '13px', statusGap: '10px' },
  compact: { container:  64, orb:  48, gap:  0, fontSize: '11px', statusGap: '0px' },
} as const;

const STATUS_LABELS: Record<OrbState, string> = {
  idle:      'Idle',
  listening: 'Listening',
  thinking:  'Thinking',
  speaking:  'Speaking',
  error:     'Disconnected',
};

function getOrbColors(state: OrbState) {
  switch (state) {
    case 'listening':
      return {
        core:  'rgba(6, 182, 212, 0.92)',    // cyan-500
        inner: 'rgba(34, 211, 238, 0.70)',   // cyan-400
        glow:  'rgba(6, 182, 212, 0.18)',
        ring:  'rgba(6, 182, 212, 0.55)',
      };
    case 'thinking':
      return {
        core:  'rgba(245, 158, 11, 0.85)',   // amber-500
        inner: 'rgba(251, 191, 36, 0.65)',   // amber-400
        glow:  'rgba(245, 158, 11, 0.14)',
        ring:  'rgba(245, 158, 11, 0.45)',
      };
    case 'speaking':
      return {
        core:  'rgba(124, 58, 237, 0.95)',   // violet-600
        inner: 'rgba(167, 139, 250, 0.75)',  // violet-400
        glow:  'rgba(124, 58, 237, 0.22)',
        ring:  'rgba(167, 139, 250, 0.60)',
      };
    case 'error':
      return {
        core:  'rgba(220, 38, 38, 0.65)',    // red-600
        inner: 'rgba(248, 113, 113, 0.40)',  // red-400
        glow:  'rgba(220, 38, 38, 0.10)',
        ring:  'rgba(220, 38, 38, 0.40)',
      };
    default:
      return {
        core:  'rgba(100, 116, 139, 0.50)',  // slate-500
        inner: 'rgba(148, 163, 184, 0.35)',  // slate-400
        glow:  'rgba(100, 116, 139, 0.08)',
        ring:  'rgba(100, 116, 139, 0.25)',
      };
  }
}

const coreVariants: Variants = {
  idle: {
    scale: [1, 1.015, 1],
    opacity: 0.65,
    transition: {
      duration: 3.2,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
  listening: {
    scale: [1, 1.07, 1],
    opacity: 0.95,
    transition: { duration: 0.85, repeat: Infinity, ease: 'easeInOut' },
  },
  thinking: {
    scale: [1, 1.03, 1, 1.03, 1],
    opacity: [0.75, 0.92, 0.78, 0.92, 0.75],
    transition: { duration: 1.6, repeat: Infinity, ease: 'easeInOut' },
  },
  speaking: {
    scale: [1, 1.06, 1.02, 1.07, 1],
    opacity: 1,
    transition: { duration: 0.55, repeat: Infinity, ease: 'easeInOut' },
  },
  error: {
    scale: [1, 1.01, 1],
    opacity: 0.4,
    transition: {
      duration: 2.8,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

const OUTER_BLOB = [
  '40% 60% 70% 30% / 40% 50% 60% 50%',
  '60% 40% 30% 70% / 50% 60% 40% 60%',
  '50% 50% 60% 40% / 60% 40% 50% 50%',
  '40% 60% 70% 30% / 40% 50% 60% 50%',
];

const INNER_BLOB = [
  '60% 40% 30% 70% / 50% 60% 40% 60%',
  '40% 60% 70% 30% / 40% 50% 60% 50%',
  '55% 45% 50% 50% / 45% 55% 50% 50%',
  '60% 40% 30% 70% / 50% 60% 40% 60%',
];

function getMotionTiming(state: OrbState) {
  switch (state) {
    case 'listening': return { outerRotate: 9, innerRotate: 6, blobMorph: 5, glowPulse: 2.2 };
    case 'thinking':  return { outerRotate: 6, innerRotate: 4, blobMorph: 4, glowPulse: 1.8 };
    case 'speaking':  return { outerRotate: 7, innerRotate: 5, blobMorph: 6, glowPulse: 1.4 };
    case 'error':     return { outerRotate: 30, innerRotate: 20, blobMorph: 10, glowPulse: 3.5 };
    default:          return { outerRotate: 18, innerRotate: 12, blobMorph: 9, glowPulse: 4.5 };
  }
}

export function VoiceOrb({
  state,
  size = 'hero',
  analyser = null,
  intensity = 0,
  statusText,
  hideStatus = false,
  onClick,
  className = '',
}: VoiceOrbProps) {
  const cfg = SIZE_CONFIG[size];
  const [audioScale, setAudioScale] = useState(1);
  const rafRef = useRef<number | null>(null);
  const colors = getOrbColors(state);
  const timing = getMotionTiming(state);

  useEffect(() => {
    if (state !== 'listening' && state !== 'speaking') {
      setAudioScale(1);
      return;
    }

    if (!analyser) {
      setAudioScale((prev) => {
        const target = 1 + Math.max(0, Math.min(1, intensity)) * 0.18;
        return prev + (target - prev) * 0.3;
      });
      return;
    }

    const bins = new Uint8Array(analyser.frequencyBinCount);
    let alive = true;

    const tick = () => {
      if (!alive) return;
      analyser.getByteFrequencyData(bins);
      let sum = 0;
      const lo = 2;
      const hi = Math.min(48, bins.length);
      for (let i = lo; i < hi; i++) sum += bins[i] * bins[i];
      const rms = Math.sqrt(sum / (hi - lo)) / 255;
      setAudioScale((prev) => {
        const target = 1 + rms * 0.18;
        return prev + (target - prev) * 0.25;
      });
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      alive = false;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      setAudioScale(1);
    };
  }, [analyser, intensity, state]);

  const label = statusText ?? STATUS_LABELS[state];

  return (
    <div
      className={className}
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: cfg.container,
      }}
    >
      {state === 'listening' && (
        <RippleRing size={cfg.orb * 1.3} color={colors.ring} />
      )}
      {state === 'thinking' && (
        <RotatingDashedRing size={cfg.orb * 1.25} color={colors.ring} />
      )}
      {state === 'speaking' && (
        <PulsingRing size={cfg.orb * 1.3} color={colors.ring} />
      )}

      <motion.div
        style={{
          position: 'absolute',
          width: cfg.orb * 1.8,
          height: cfg.orb * 1.8,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${colors.glow} 0%, transparent 65%)`,
          pointerEvents: 'none',
        }}
        animate={{
          scale: state === 'speaking' ? [1, 1.15, 1] : [1, 1.08, 1],
          opacity: state === 'idle' ? [0.6, 0.8, 0.6] : [0.85, 1, 0.85],
        }}
        transition={{
          duration: timing.glowPulse,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      <div
        style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: cfg.orb,
          height: cfg.orb,
          cursor: onClick ? 'pointer' : 'default',
        }}
        onClick={onClick}
      >
        <motion.div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: colors.core,
            borderRadius: OUTER_BLOB[0],
          }}
          animate={{ rotate: 360, borderRadius: OUTER_BLOB }}
          transition={{
            rotate: { duration: timing.outerRotate, repeat: Infinity, ease: 'linear' },
            borderRadius: { duration: timing.blobMorph, repeat: Infinity, ease: 'easeInOut' },
          }}
        />

        <motion.div
          style={{
            position: 'absolute',
            inset: cfg.orb * 0.1,
            backgroundColor: colors.inner,
            borderRadius: INNER_BLOB[0],
          }}
          animate={{ rotate: -360, borderRadius: INNER_BLOB }}
          transition={{
            rotate: { duration: timing.innerRotate, repeat: Infinity, ease: 'linear' },
            borderRadius: { duration: timing.blobMorph * 0.7, repeat: Infinity, ease: 'easeInOut' },
          }}
        />

        <motion.div
          style={{
            position: 'absolute',
            inset: cfg.orb * 0.18,
            borderRadius: '50%',
            overflow: 'hidden',
            transform: `scale(${audioScale})`,
            transition: 'transform 80ms linear',
          }}
          variants={coreVariants}
          animate={state}
        >
          <div
            style={{
              position: 'absolute',
              inset: 0,
              backgroundColor: colors.core,
              opacity: 0.92,
            }}
          />
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background:
                'linear-gradient(145deg, rgba(255,255,255,0.20) 0%, transparent 60%)',
            }}
          />
        </motion.div>

        <div
          style={{
            position: 'absolute',
            inset: cfg.orb * 0.18,
            borderRadius: '50%',
            border: '1px solid rgba(255,255,255,0.28)',
            pointerEvents: 'none',
          }}
        />

        {state === 'thinking' && size === 'hero' && (
          <ThinkingDots color="rgba(255,255,255,0.95)" />
        )}
      </div>

      {!hideStatus && (
        <div
          style={{
            marginTop: cfg.statusGap,
            height: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <AnimatePresence mode="wait">
            <motion.span
              key={`${state}-${label}`}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18 }}
              style={{
                fontFamily: 'var(--font-sans)',
                fontSize: cfg.fontSize,
                fontWeight: 500,
                color: 'var(--color-fg-secondary)',
                letterSpacing: '0.01em',
              }}
            >
              {label}
            </motion.span>
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

function RippleRing({ size, color }: { size: number; color: string }) {
  return (
    <>
      <motion.div
        style={{
          position: 'absolute',
          width: size,
          height: size,
          borderRadius: '50%',
          border: `2px solid ${color}`,
          pointerEvents: 'none',
        }}
        animate={{ scale: [1, 1.35], opacity: [0.7, 0] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: 'easeOut' }}
      />
      <motion.div
        style={{
          position: 'absolute',
          width: size,
          height: size,
          borderRadius: '50%',
          border: `2px solid ${color}`,
          pointerEvents: 'none',
        }}
        animate={{ scale: [1, 1.35], opacity: [0.7, 0] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: 'easeOut', delay: 0.8 }}
      />
    </>
  );
}

function RotatingDashedRing({ size, color }: { size: number; color: string }) {
  return (
    <motion.div
      style={{
        position: 'absolute',
        width: size,
        height: size,
        borderRadius: '50%',
        border: `2px dashed ${color}`,
        pointerEvents: 'none',
      }}
      animate={{ rotate: 360 }}
      transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
    />
  );
}

function PulsingRing({ size, color }: { size: number; color: string }) {
  return (
    <motion.div
      style={{
        position: 'absolute',
        width: size,
        height: size,
        borderRadius: '50%',
        border: `2px solid ${color}`,
        pointerEvents: 'none',
      }}
      animate={{ scale: [1, 1.08, 1], opacity: [0.55, 0.95, 0.55] }}
      transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
    />
  );
}

function ThinkingDots({ color }: { color: string }) {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        pointerEvents: 'none',
      }}
    >
      {[0, 0.18, 0.36].map((delay, i) => (
        <motion.span
          key={i}
          style={{
            display: 'inline-block',
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: color,
          }}
          animate={{ y: [0, -6, 0], opacity: [0.4, 1, 0.4] }}
          transition={{
            duration: 0.9,
            repeat: Infinity,
            ease: 'easeInOut',
            delay,
          }}
        />
      ))}
    </div>
  );
}
