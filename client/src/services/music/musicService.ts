import { createApi } from '@reduxjs/toolkit/query/react';
import { baseQueryWithReauth } from '@/services/auth/baseQuery';

export interface MusicTrackItem {
  id: string;
  prompt: string;
  url: string;
  duration: number;
  voice_name?: string;
  created_at?: string;
}

export interface GenerateMusicRequest {
  prompt: string;
  style_tags: string[];
  duration: number;
}

export const MusicAPI = createApi({
  reducerPath: 'musicAPI',
  baseQuery: baseQueryWithReauth,
  tagTypes: ['Tracks'],
  keepUnusedDataFor: 3600,
  refetchOnFocus: false,
  refetchOnReconnect: false,
  refetchOnMountOrArgChange: false,
  endpoints: (builder) => ({
    getMusicList: builder.query<MusicTrackItem[], void>({
      query: () => '/music/list',
      providesTags: ['Tracks'],
    }),

    generateMusic: builder.mutation<MusicTrackItem, GenerateMusicRequest>({
      query: (body) => ({
        url: '/music/generate',
        method: 'POST',
        body,
      }),
      invalidatesTags: ['Tracks'],
    }),

    deleteMusic: builder.mutation<void, string>({
      query: (id) => ({
        url: `/music/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Tracks'],
    }),
  }),
});

export const {
  useGetMusicListQuery,
  useGenerateMusicMutation,
  useDeleteMusicMutation,
} = MusicAPI;
