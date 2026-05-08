import { configureStore, createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { AgentStatus, Message } from '@typing';
import { authReducer } from '@/features/auth';
import { AuthAPI } from '@/services/auth';
import { VoiceAPI } from '@/services/voice';
import { MusicAPI } from '@/services/music';
import { PersonalityAPI } from '@/services/personality';

export interface Thread {
  id: string;
  title: string;
  createdAt: string; // ISO 8601 string — kept as string for Redux serialization
  updatedAt: string; // ISO 8601 string — kept as string for Redux serialization
  messageCount: number;
  pinned?: boolean;
}

interface VoiceAgentState {
  status: AgentStatus;
  isConnected: boolean;
  audioLevel: number;
  /** Mic pause state. When true, the mic-capture worklet stops sending
   *  frames to the server, but the WebSocket and audio pipeline stay
   *  alive. Resume is instant — no reconnect penalty. */
  isMuted: boolean;
  messages: Message[];
  currentThreadId: string | null;
  currentAiMessageId: string | null;
  currentPartialId: string | null;
  isPlaying: boolean;
  currentSampleRate: number;
  threads: Thread[];
  titleSetForThreads: string[];
}

const initialState: VoiceAgentState = {
  status: 'idle',
  isConnected: false,
  audioLevel: 0,
  isMuted: false,
  messages: [],
  currentThreadId: null,
  currentAiMessageId: null,
  currentPartialId: null,
  isPlaying: false,
  currentSampleRate: 0,  // MUST be set by audio_info event before playback; 0 = not yet received
  threads: [],
  titleSetForThreads: [],
};

const voiceAgentSlice = createSlice({
  name: 'voiceAgent',
  initialState,
  reducers: {
    setStatus: (state, action: PayloadAction<AgentStatus>) => {
      state.status = action.payload;
    },
    setIsConnected: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
    },
    setAudioLevel: (state, action: PayloadAction<number>) => {
      state.audioLevel = action.payload;
    },
    setIsPlaying: (state, action: PayloadAction<boolean>) => {
      state.isPlaying = action.payload;
    },
    setIsMuted: (state, action: PayloadAction<boolean>) => {
      state.isMuted = action.payload;
    },
    setSampleRate: (state, action: PayloadAction<number>) => {
      state.currentSampleRate = action.payload;
    },
    addMessage: (state, action: PayloadAction<Message>) => {
      state.messages.push(action.payload);
    },
    updateMessage: (state, action: PayloadAction<{ id: string; updates: Partial<Message> }>) => {
      const msg = state.messages.find(m => m.id === action.payload.id);
      if (msg) {
        Object.assign(msg, action.payload.updates);
      }
    },
    appendToMessage: (state, action: PayloadAction<{ id: string; text: string }>) => {
      const msg = state.messages.find(m => m.id === action.payload.id);
      if (msg) {
        msg.content += action.payload.text;
      }
    },
    setCurrentAiMessageId: (state, action: PayloadAction<string | null>) => {
      state.currentAiMessageId = action.payload;
    },
    setCurrentPartialId: (state, action: PayloadAction<string | null>) => {
      state.currentPartialId = action.payload;
    },
    setMessages: (state, action: PayloadAction<{ messages: Message[]; clearTracking?: boolean }>) => {
      state.messages = action.payload.messages;
      if (action.payload.clearTracking) {
        state.currentAiMessageId = null;
        state.currentPartialId = null;
      }
    },
    setCurrentThreadId: (state, action: PayloadAction<string | null>) => {
      state.currentThreadId = action.payload;
    },
    addThread: (state, action: PayloadAction<Thread>) => {
      state.threads.unshift(action.payload);
    },
    renameThread: (state, action: PayloadAction<{ id: string; title: string }>) => {
      const thread = state.threads.find(t => t.id === action.payload.id);
      if (thread) {
        thread.title = action.payload.title;
      }
    },
    markTitleSet: (state, action: PayloadAction<string>) => {
      state.titleSetForThreads.push(action.payload);
    },
    reset: (state) => {
      Object.assign(state, initialState);
    },
  },
});

export const store = configureStore({
  reducer: {
    voiceAgent: voiceAgentSlice.reducer,
    auth: authReducer,
    [AuthAPI.reducerPath]: AuthAPI.reducer,
    [VoiceAPI.reducerPath]: VoiceAPI.reducer,
    [MusicAPI.reducerPath]: MusicAPI.reducer,
    [PersonalityAPI.reducerPath]: PersonalityAPI.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(
      AuthAPI.middleware,
      VoiceAPI.middleware,
      MusicAPI.middleware,
      PersonalityAPI.middleware,
    ),
});

export const {
  setStatus,
  setIsConnected,
  setAudioLevel,
  setIsPlaying,
  setIsMuted,
  setSampleRate,
  addMessage,
  updateMessage,
  appendToMessage,
  setMessages,
  setCurrentAiMessageId,
  setCurrentPartialId,
  setCurrentThreadId,
  addThread,
  renameThread,
  markTitleSet,
  reset,
} = voiceAgentSlice.actions;

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
