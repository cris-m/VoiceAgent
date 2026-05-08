export type {
  UseVoiceAgentReturn,
  UseVoiceAgentOptions,
  UseAudioPlayerReturn,
  UseNarrateReturn,
  UseVoiceCloneReturn,
} from './hooks';

export type AgentStatus = 'idle' | 'listening' | 'processing' | 'speaking';

export interface ToolCall {
  id: string;
  name: string;
  args?: Record<string, unknown>;
  result?: string | Record<string, unknown>;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string; // ISO 8601 string — kept as string for Redux serialization
  isStreaming?: boolean;
  toolCalls?: ToolCall[];
  tokenCount?: number;
  elapsedMs?: number;
}

export interface ThreadMessage {
  type: 'thread';
  thread_id: string;
}

export interface ThreadTitleMessage {
  type: 'thread_title';
  thread_id: string;
  title: string;
}

export interface PartialTranscriptMessage {
  type: 'partial_transcript';
  text: string;
  is_final: boolean;
}

export interface SpokenTextMessage {
  type: 'spoken_text';
  text: string;
}

export interface TextStreamMessage {
  type: 'text_stream';
  text: string;
  done: boolean;
}

export interface AudioInfoMessage {
  type: 'audio_info';
  sample_rate: number;
}

export interface VadMessage {
  type: 'vad';
  is_speaking: boolean;
}

export interface InterruptMessage {
  type: 'interrupt';
}

export interface ErrorMessage {
  type: 'error';
  message: string;
}

export type ServerMessage =
  | ThreadMessage
  | ThreadTitleMessage
  | PartialTranscriptMessage
  | SpokenTextMessage
  | TextStreamMessage
  | AudioInfoMessage
  | VadMessage
  | InterruptMessage
  | ErrorMessage;

export interface ThreadMetadata {
  name?: string;
  pinned?: boolean;
  createdAt?: string;
  updatedAt?: string;
  [key: string]: unknown;
}

export interface LangGraphMessage {
  id?: string;
  type: 'human' | 'ai' | 'tool' | string;
  content: string | unknown;
  timestamp?: Date | string | number;
  tool_call_id?: string;
  tool_calls?: ToolCall[];
}
