import type { Voice } from '../../context/VoiceConfigContext';

export type NarrationStatus = 'idle' | 'generating' | 'success' | 'error';

export type { Voice };

export interface Language {
  code: string;
  name: string;
  native_name?: string;
}

export interface GeneratedAudio {
  id: string;
  text: string;
  voiceId: string;
  voiceName: string;
  speed: number;
  audioUrl: string;
  duration: number;
  createdAt: Date;
}
