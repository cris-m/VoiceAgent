from typing import AsyncIterator, List, Optional
import asyncio

import numpy as np
from faster_whisper import WhisperModel

from services.stt.base import (
    BaseSTT,
    STTConfig,
    STTResult,
    PartialResult,
    TranscriptionSegment,
    WordTiming,
)
from services.audio.base import AudioChunk


class WhisperSTT(BaseSTT):
    """Faster-Whisper STT service using CTranslate2-optimized inference."""

    MODELS = ["tiny", "base", "small", "medium", "large-v2", "large-v3"]

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        cpu_threads: int = 4,
        config: Optional[STTConfig] = None,
    ):
        super().__init__("whisper_stt", config)
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self._model: Optional[WhisperModel] = None

    async def initialize(self) -> None:
        # Idempotent — see services/tts/pocket_tts.py for the same pattern.
        if self._model is not None:
            return

        self.logger.info(
            f"Loading Whisper model: {self.model_size} "
            f"(device={self.device}, compute={self.compute_type}, threads={self.cpu_threads})"
        )

        loop = asyncio.get_event_loop()
        self._model = await loop.run_in_executor(
            None,
            lambda: WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
            ),
        )

        self.logger.info(f"Whisper model loaded: {self.model_size}")

        # Warm-up: the first transcribe() pays a 500-1000ms JIT/kernel cost
        # that subsequent calls don't. Run a dummy transcription on 1s of
        # silence at startup so the user's first turn isn't slower than
        # subsequent ones. Failures are non-fatal — the user just pays the
        # cold-start cost on the first real call.
        try:
            dummy = np.zeros(16000, dtype=np.float32)
            await loop.run_in_executor(
                None,
                lambda: list(self._model.transcribe(
                    dummy,
                    beam_size=1,
                    best_of=1,
                    word_timestamps=False,
                    condition_on_previous_text=False,
                    vad_filter=False,
                )[0]),
            )
            self.logger.info("Whisper warm-up complete")
        except Exception as e:
            self.logger.warning(f"Whisper warm-up failed (non-fatal): {e}")

    async def shutdown(self) -> None:
        self._model = None
        self.logger.info("Whisper model unloaded")

    async def health_check(self) -> bool:
        return self._model is not None

    async def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None,
        **kwargs,
    ) -> STTResult:
        if self._model is None:
            raise RuntimeError("Model not initialized")

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        if sample_rate != 16000:
            import librosa
            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=16000)

        language = self._resolve_language(language) if language else None
        loop = asyncio.get_event_loop()

        def _transcribe():
            # Voice-optimized decoding: greedy (beam=1, best_of=1) is ~5×
            # faster than the default beam_size=5 / best_of=5, and word-
            # timestamp alignment costs ~30-50% extra. None of those help
            # for short conversational turns. condition_on_previous_text
            # is also off — each voice turn is independent, and conditioning
            # adds prompt-stuffing latency on every call.
            segments, info = self._model.transcribe(
                audio,
                language=language,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                vad_filter=False,
                word_timestamps=False,
                hallucination_silence_threshold=0.3,
                repetition_penalty=1.05,
                no_repeat_ngram_size=4,
                no_speech_threshold=0.4,
                compression_ratio_threshold=2.4,
                log_prob_threshold=-0.8,
                condition_on_previous_text=False,
                suppress_blank=True,
                **kwargs,
            )
            return list(segments), info

        segments, info = await loop.run_in_executor(None, _transcribe)

        result_segments = []
        full_text = ""

        for seg in segments:
            words = None
            if self.config.word_timestamps and hasattr(seg, "words") and seg.words:
                words = [
                    WordTiming(
                        word=w.word,
                        start=w.start,
                        end=w.end,
                        confidence=w.probability if hasattr(w, "probability") else None,
                    )
                    for w in seg.words
                ]

            result_segments.append(
                TranscriptionSegment(
                    text=seg.text,
                    start=seg.start,
                    end=seg.end,
                    confidence=seg.avg_logprob if hasattr(seg, "avg_logprob") else None,
                    words=words,
                    language=info.language,
                )
            )
            full_text += seg.text

        return STTResult(
            text=full_text.strip(),
            segments=result_segments,
            language=info.language,
            duration=info.duration,
            confidence=info.language_probability if hasattr(info, "language_probability") else None,
            metadata={
                "model": self.model_size,
                "duration_after_vad": getattr(info, "duration_after_vad", None),
            },
        )

    async def transcribe_stream(
        self,
        stream: AsyncIterator[AudioChunk],
        language: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[PartialResult]:
        """Stream transcription results. Whisper accumulates audio and transcribes in chunks."""
        buffer = []
        buffer_duration = 0.0
        chunk_duration = 2.0  # Transcribe every 2 seconds

        async for chunk in stream:
            buffer.append(chunk.data)
            buffer_duration += chunk.duration

            if buffer_duration >= chunk_duration:
                audio = np.concatenate(buffer)
                result = await self.transcribe(
                    audio=audio,
                    sample_rate=chunk.sample_rate,
                    language=language,
                    **kwargs,
                )

                yield PartialResult(
                    text=result.text,
                    is_final=False,
                    confidence=result.confidence,
                )

                buffer = []
                buffer_duration = 0.0

        if buffer:
            audio = np.concatenate(buffer)
            result = await self.transcribe(
                audio=audio,
                sample_rate=16000,
                language=language,
                **kwargs,
            )

            yield PartialResult(
                text=result.text,
                is_final=True,
                confidence=result.confidence,
            )

    async def get_supported_languages(self) -> List[str]:
        return [
            "en", "zh", "de", "es", "ru", "ko", "fr", "ja", "pt", "tr",
            "pl", "ca", "nl", "ar", "sv", "it", "id", "hi", "fi", "vi",
            "he", "uk", "el", "ms", "cs", "ro", "da", "hu", "ta", "no",
            "th", "ur", "hr", "bg", "lt", "la", "mi", "ml", "cy", "sk",
            "te", "fa", "lv", "bn", "sr", "az", "sl", "kn", "et", "mk",
            "br", "eu", "is", "hy", "ne", "mn", "bs", "kk", "sq", "sw",
            "gl", "mr", "pa", "si", "km", "sn", "yo", "so", "af", "oc",
            "ka", "be", "tg", "sd", "gu", "am", "yi", "lo", "uz", "fo",
            "ht", "ps", "tk", "nn", "mt", "sa", "lb", "my", "bo", "tl",
            "mg", "as", "tt", "haw", "ln", "ha", "ba", "jw", "su",
        ]
