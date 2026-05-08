import { createApi } from '@reduxjs/toolkit/query/react';
import { baseQueryWithReauth } from '@/services/auth/baseQuery';

export interface PersonalityOption {
  id: string;
  name: string;
  description?: string | null;
  preview_text?: string | null;
  tags?: string[] | null;
  is_default?: boolean;
}

export interface PersonalitiesResponse {
  personalities: PersonalityOption[];
  default_id: string;
}

export const PersonalityAPI = createApi({
  reducerPath: 'personalityAPI',
  baseQuery: baseQueryWithReauth,
  tagTypes: ['Personalities'],
  keepUnusedDataFor: 86400,
  refetchOnFocus: false,
  refetchOnReconnect: false,
  refetchOnMountOrArgChange: false,
  endpoints: (builder) => ({
    getPersonalities: builder.query<PersonalitiesResponse, void>({
      query: () => '/personality',
      providesTags: ['Personalities'],
      keepUnusedDataFor: 86400,
    }),
  }),
});

export const { useGetPersonalitiesQuery } = PersonalityAPI;
