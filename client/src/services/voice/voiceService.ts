import { createApi } from '@reduxjs/toolkit/query/react';
import { baseQueryWithReauth } from '@/services/auth/baseQuery';

export interface VoiceOption {
  id: string;
  name: string;
  language?: string;
  gender?: string | null;
  description?: string | null;
  preview_text?: string | null;
  tags?: string[] | null;
}

export interface VoicesResponse {
  voices: VoiceOption[];
  default_voice: string;
}

export interface LanguageOption {
  code: string;
  name: string;
  native_name?: string;
}

export interface LanguagesResponse {
  languages: LanguageOption[];
  default_language: string;
}

export interface VoiceConfigResponse {
  voice_id: string;
  language: string;
  speed: number;
  stt_model: string;
  supports_cloning: boolean;
  supports_speed: boolean;
  supports_language: boolean;
}

export interface NarrationItem {
  id: string;
  prompt: string;
  url: string;
  duration: number;
  voice_name: string;
  created_at: string;
}

export interface NarrateRequest {
  text: string;
  voice_id: string;
  speed?: number;
  language?: string;
}

export interface TranscribeResponse {
  text: string;
  language?: string | null;
  duration_seconds: number;
}

export interface CloneVoiceRequest {
  /** FormData containing file, name, language, and optional ref_text */
  formData: FormData;
}

export const VoiceAPI = createApi({
  reducerPath: 'voiceAPI',
  baseQuery: baseQueryWithReauth,
  tagTypes: ['Voices', 'Languages', 'VoiceConfig', 'Narrations', 'CloneVoices'],
  keepUnusedDataFor: 3600,
  refetchOnFocus: false,
  refetchOnReconnect: false,
  refetchOnMountOrArgChange: false,
  endpoints: (builder) => ({
    getVoices: builder.query<VoicesResponse, void>({
      query: () => '/voice/voices',
      providesTags: ['Voices'],
      keepUnusedDataFor: 86400,
    }),

    getLanguages: builder.query<LanguagesResponse, void>({
      query: () => '/voice/languages',
      providesTags: ['Languages'],
      keepUnusedDataFor: 86400,
    }),

    getVoiceConfig: builder.query<VoiceConfigResponse, void>({
      query: () => '/voice/config',
      providesTags: ['VoiceConfig'],
      keepUnusedDataFor: 86400,
    }),

    getNarrations: builder.query<NarrationItem[], void>({
      query: () => '/voice/narrations',
      providesTags: ['Narrations'],
    }),

    narrate: builder.mutation<NarrationItem, NarrateRequest>({
      query: (body) => ({
        url: '/voice/narrate',
        method: 'POST',
        body,
        // Long narrations chunk-synthesize sequentially on CPU TTS, so a
        // 5000-char text with 30+ chunks can take 2-3 minutes. nginx
        // proxy_read_timeout is 300s — match it on the client.
      }),
      invalidatesTags: ['Narrations'],
    }),

    /** Preview-only narrate: doesn't invalidate the persisted narrations list. */
    previewVoice: builder.mutation<NarrationItem, NarrateRequest>({
      query: (body) => ({
        url: '/voice/narrate',
        method: 'POST',
        body,
      }),
    }),

    deleteNarration: builder.mutation<void, string>({
      query: (id) => ({
        url: `/voice/narrations/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Narrations'],
    }),

    transcribe: builder.mutation<TranscribeResponse, FormData>({
      query: (formData) => ({
        url: '/voice/transcribe',
        method: 'POST',
        body: formData,
      }),
    }),

    cloneVoice: builder.mutation<VoiceOption, FormData>({
      query: (formData) => ({
        url: '/voice/clone',
        method: 'POST',
        body: formData,
      }),
      invalidatesTags: ['Voices'],
    }),

    deleteCloneVoice: builder.mutation<void, string>({
      query: (id) => ({
        url: `/voice/clones/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Voices'],
    }),
  }),
});

export const {
  useGetVoicesQuery,
  useGetLanguagesQuery,
  useGetVoiceConfigQuery,
  useGetNarrationsQuery,
  useNarrateMutation,
  usePreviewVoiceMutation,
  useDeleteNarrationMutation,
  useTranscribeMutation,
  useCloneVoiceMutation,
  useDeleteCloneVoiceMutation,
} = VoiceAPI;
