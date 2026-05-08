export type TranscriptionStatus = 'idle' | 'uploading' | 'success' | 'error';

export interface TranscriptionResult {
  id: string;
  text: string;
  duration: number;
  language?: string;
  fileName: string;
  fileSize: number;
  audioUrl: string;
  createdAt: Date;
}
