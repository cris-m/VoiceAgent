from typing import List

from pydub import AudioSegment
from pydub.silence import detect_silence

from utils import get_logger

logger = get_logger(__name__)


class AudioChunker:
    """Splits audio at silence boundaries for STT processing."""

    def __init__(
        self,
        chunk_duration_ms: int = 30000,
        min_silence_len: int = 500,
        silence_thresh: int = -40,
    ):
        self.chunk_duration_ms = chunk_duration_ms
        self.min_silence_len = min_silence_len
        self.silence_thresh = silence_thresh

    def detect_silence_boundaries(self, audio: AudioSegment) -> List[int]:
        """Detect silence points in audio. Returns timestamps (ms) of silence midpoints."""
        try:
            silent_ranges = detect_silence(
                audio,
                min_silence_len=self.min_silence_len,
                silence_thresh=self.silence_thresh,
            )

            silence_points = [(start + end) // 2 for start, end in silent_ranges]
            logger.debug(f"Detected {len(silence_points)} silence points")
            return silence_points

        except Exception as e:
            logger.warning(f"Failed to detect silence: {e}, using fixed intervals")
            return []

    def chunk_by_duration(self, audio: AudioSegment) -> List[AudioSegment]:
        """Split audio into chunks at silence boundaries."""
        audio_length = len(audio)

        if audio_length <= self.chunk_duration_ms:
            logger.info(f"Audio length ({audio_length}ms) under threshold, no chunking needed")
            return [audio]

        logger.info(f"Chunking audio ({audio_length}ms) into ~{self.chunk_duration_ms}ms segments")

        silence_points = self.detect_silence_boundaries(audio)

        chunks = []
        start = 0

        while start < audio_length:
            end = start + self.chunk_duration_ms

            if end < audio_length and silence_points:
                search_window = 5000  # ms
                candidates = [
                    sp for sp in silence_points
                    if start < sp < end + search_window
                ]

                if candidates:
                    end = min(candidates, key=lambda sp: abs(sp - end))
            else:
                end = min(end, audio_length)

            chunk = audio[start:end]
            chunks.append(chunk)

            start = end

        logger.info(f"Created {len(chunks)} audio chunks")
        return chunks

    def chunk_by_fixed_intervals(self, audio: AudioSegment) -> List[AudioSegment]:
        """Fallback: split by fixed intervals when silence detection fails."""
        audio_length = len(audio)
        chunks = []
        start = 0

        while start < audio_length:
            end = min(start + self.chunk_duration_ms, audio_length)
            chunks.append(audio[start:end])
            start = end

        return chunks
