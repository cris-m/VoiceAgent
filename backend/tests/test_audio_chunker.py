import pytest
from unittest.mock import MagicMock, patch

from services.stt.audio_chunker import AudioChunker


def _make_segment(duration_ms: int) -> MagicMock:
    seg = MagicMock()
    seg.__len__ = lambda s: duration_ms
    # Support slice notation: audio[start:end]
    seg.__getitem__ = lambda s, key: _make_segment(key.stop - key.start)
    return seg


class TestBelowThreshold:
    def test_short_audio_returned_as_single_chunk(self):
        chunker = AudioChunker(chunk_duration_ms=30_000)
        audio = _make_segment(15_000)
        chunks = chunker.chunk_by_duration(audio)
        assert len(chunks) == 1

    def test_exactly_at_threshold_returned_as_single_chunk(self):
        chunker = AudioChunker(chunk_duration_ms=30_000)
        audio = _make_segment(30_000)
        chunks = chunker.chunk_by_duration(audio)
        assert len(chunks) == 1


class TestSilenceBasedSplitting:
    def test_long_audio_split_near_silence(self):
        chunker = AudioChunker(chunk_duration_ms=30_000, min_silence_len=500, silence_thresh=-40)
        audio = _make_segment(60_000)

        # silence at 31s lies beyond the first chunk boundary, forcing a split
        with patch("services.stt.audio_chunker.detect_silence", return_value=[(30_000, 32_000)]):
            chunks = chunker.chunk_by_duration(audio)
        assert len(chunks) >= 2

    def test_no_silence_detected_falls_back_to_fixed_intervals(self):
        chunker = AudioChunker(chunk_duration_ms=20_000)
        audio = _make_segment(60_000)

        with patch("services.stt.audio_chunker.detect_silence", return_value=[]):
            chunks = chunker.chunk_by_duration(audio)
        assert len(chunks) == 3

    def test_silence_detection_exception_falls_back_gracefully(self):
        chunker = AudioChunker(chunk_duration_ms=20_000)
        audio = _make_segment(40_000)

        with patch("services.stt.audio_chunker.detect_silence", side_effect=Exception("fail")):
            chunks = chunker.chunk_by_duration(audio)
        assert len(chunks) >= 2


class TestFixedIntervalFallback:
    def test_fixed_intervals_exact_division(self):
        chunker = AudioChunker(chunk_duration_ms=10_000)
        audio = _make_segment(30_000)
        chunks = chunker.chunk_by_fixed_intervals(audio)
        assert len(chunks) == 3

    def test_fixed_intervals_remainder_chunk(self):
        chunker = AudioChunker(chunk_duration_ms=10_000)
        audio = _make_segment(35_000)
        chunks = chunker.chunk_by_fixed_intervals(audio)
        assert len(chunks) == 4

    def test_fixed_intervals_shorter_than_chunk_size(self):
        chunker = AudioChunker(chunk_duration_ms=30_000)
        audio = _make_segment(5_000)
        chunks = chunker.chunk_by_fixed_intervals(audio)
        assert len(chunks) == 1


class TestSilenceBoundaryDetection:
    def test_midpoints_computed_correctly(self):
        chunker = AudioChunker()
        audio = MagicMock()

        # Patch at module level since that's where it's looked up
        with patch("services.stt.audio_chunker.detect_silence", return_value=[
            (1000, 2000),  # midpoint = 1500
            (5000, 7000),  # midpoint = 6000
        ]):
            points = chunker.detect_silence_boundaries(audio)

        assert points == [1500, 6000]

    def test_empty_silence_returns_empty_list(self):
        chunker = AudioChunker()
        audio = MagicMock()
        with patch("services.stt.audio_chunker.detect_silence", return_value=[]):
            points = chunker.detect_silence_boundaries(audio)
        assert points == []

    def test_detection_exception_returns_empty_list(self):
        chunker = AudioChunker()
        audio = MagicMock()
        with patch("services.stt.audio_chunker.detect_silence", side_effect=RuntimeError("boom")):
            points = chunker.detect_silence_boundaries(audio)
        assert points == []
