export type OrbState = 'idle' | 'listening' | 'thinking' | 'speaking' | 'error';
export type OrbSize = 'hero' | 'active' | 'compact';

export interface VoiceOrbProps {
  state: OrbState;
  size?: OrbSize;
  /**
   * Optional Web Audio analyser for audio-reactive scaling. When set and
   * state is 'listening' or 'speaking', the inner core scales with the
   * RMS of the current audio frame. Takes precedence over `intensity`.
   */
  analyser?: AnalyserNode | null;
  /**
   * Pre-computed normalized loudness (0–1). Used when no analyser is
   * available — e.g. when the parent already has an `audioLevel` value
   * from an AudioWorklet processor and just wants to drive the orb's
   * scale without exposing raw FFT bins.
   */
  intensity?: number;
  /** Optional status text override. Falls back to a sensible default per state. */
  statusText?: string;
  /** Hide the status text entirely (used in compact mode). */
  hideStatus?: boolean;
  onClick?: () => void;
  className?: string;
}
