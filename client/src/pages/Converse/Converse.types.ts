import type { AgentStatus } from '@typing';
import type { OrbState } from '../../components/ui/VoiceOrb';

export type StatusToOrbStateFunction = (
  status: AgentStatus,
  isConnected: boolean,
  error: boolean,
) => OrbState;
