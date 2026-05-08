import type { Message, AgentStatus } from './index';
import type { Voice, Language, GeneratedAudio, NarrationStatus } from '@pages/Narrate/Narrate.types';

export interface UseVoiceAgentReturn {
  status: AgentStatus;
  messages: Message[];
  isConnected: boolean;
  audioLevel: number;
  connect: () => Promise<void>;
  disconnect: () => void;
  /** True when the mic is paused — the MediaStream is fully released
   *  so the browser/OS mic indicator turns off. WS stays open. */
  isMuted: boolean;
  /** Toggle the mic pause state. Pause stops the MediaStreamTrack;
   *  resume reacquires via getUserMedia and rewires the worklet. */
  togglePause: () => Promise<void>;
}

export interface UseVoiceAgentOptions {
  wsUrl?: string;
  onError?: (error: Error) => void;
  onThreadCreated?: (threadId: string) => void;
}

export interface UseAudioPlayerReturn {
  audioRef: React.RefObject<HTMLAudioElement | null>;
  /** Callback ref. Wire into <audio ref={setAudioRef}> instead of audioRef
   *  to guarantee timeupdate listeners reattach when the element mounts. */
  setAudioRef: (node: HTMLAudioElement | null) => void;
  progress: number;
  currentTime: number;
  isPlaying: boolean;
  activeId: string | null;
  handlePlayPause: (id: string, url: string) => Promise<void>;
  handleProgressClick: (e: React.MouseEvent<HTMLDivElement>) => void;
  handleSelect: (id: string) => void;
}

export interface UseNarrateReturn {
  text: string;
  setText: (text: string) => void;
  voices: Voice[];
  selectedVoice: string;
  setSelectedVoice: (id: string) => void;
  languages: Language[];
  selectedLanguage: string;
  setSelectedLanguage: (lang: string) => void;
  speed: number;
  setSpeed: (speed: number) => void;
  status: NarrationStatus;
  error: string | null;
  generatedAudios: GeneratedAudio[];
  loadingVoices: boolean;
  progress: number;
  handleGenerate: () => Promise<void>;
  previewingVoice: string | null;
  handlePreviewVoice: (voiceId: string) => Promise<void>;
  handleCopyText: (id: string, text: string) => Promise<void>;
  copiedId: string | null;
  supportsCloning: boolean;
  supportsSpeed: boolean;
  supportsLanguage: boolean;
  handleDelete: (id: string) => Promise<void>;
}

export interface UseVoiceCloneReturn {
  showCloneModal: boolean;
  setShowCloneModal: (show: boolean) => void;
  cloneFile: File | null;
  cloneName: string;
  setCloneName: (name: string) => void;
  cloneTranscript: string;
  setCloneTranscript: (text: string) => void;
  cloneLanguage: string;
  setCloneLanguage: (lang: string) => void;
  cloningStatus: 'idle' | 'cloning' | 'success' | 'error';
  cloneError: string | null;
  handleCloneFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleCloneVoice: () => Promise<void>;
  handleDeleteClonedVoice: (id: string, voices: Voice[], selectedVoice: string, setSelectedVoice: (id: string) => void) => Promise<void>;
  resetCloneForm: () => void;
  cloneFileInputRef: React.RefObject<HTMLInputElement | null>;
}
