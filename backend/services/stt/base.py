import asyncio
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, List, Optional

import numpy as np

from services.audio.base import AudioChunk, AudioConfig
from services.base import BaseService


@dataclass
class TranscriptionSegment:
    text: str
    start: float
    end: float
    confidence: Optional[float] = None
    words: Optional[List["WordTiming"]] = None
    language: Optional[str] = None


@dataclass
class WordTiming:
    word: str
    start: float
    end: float
    confidence: Optional[float] = None


@dataclass
class STTConfig:
    language: str = "en"
    model: Optional[str] = None
    task: str = "transcribe"
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0
    word_timestamps: bool = False
    vad_filter: bool = True
    audio: AudioConfig = field(default_factory=AudioConfig)


@dataclass
class STTResult:
    text: str
    segments: List[TranscriptionSegment]
    language: str
    duration: float
    confidence: Optional[float] = None
    metadata: dict = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()


@dataclass
class PartialResult:
    text: str
    is_final: bool = False
    confidence: Optional[float] = None
    timestamp: Optional[float] = None


@dataclass
class TranscriptEvent:
    """A single event from a streaming STT session.

    - is_final=False: interim/partial transcript that may change
    - is_final=True: committed transcript, will not change
    """

    text: str
    is_final: bool
    confidence: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    language: Optional[str] = None


class StreamingSession:
    """Base class for a live STT streaming session.

    Usage:
        async with stt.open_stream(sample_rate=16000) as session:
            # Producer task: feed audio chunks
            await session.send_audio(chunk)

            # Consumer task: read transcript events
            async for event in session:
                if event.is_final:
                    handle(event.text)
    """

    def __init__(self) -> None:
        self._events: asyncio.Queue[Optional[TranscriptEvent]] = asyncio.Queue()
        self._closed = False

    async def send_audio(self, audio: np.ndarray) -> None:
        """Push an audio chunk into the session. Subclass must implement."""
        raise NotImplementedError

    async def close(self) -> None:
        """Finish the session and release resources. Idempotent."""
        if not self._closed:
            self._closed = True
            await self._events.put(None)  # sentinel

    def __aiter__(self) -> "StreamingSession":
        return self

    async def __anext__(self) -> TranscriptEvent:
        event = await self._events.get()
        if event is None:
            raise StopAsyncIteration
        return event

    async def __aenter__(self) -> "StreamingSession":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()


class BaseSTT(BaseService):
    def __init__(self, name: str, config: Optional[STTConfig] = None):
        super().__init__(name)
        self.config = config or STTConfig()

    @abstractmethod
    async def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        language: Optional[str] = None,
        **kwargs,
    ) -> STTResult:
        pass

    @abstractmethod
    async def transcribe_stream(
        self,
        stream: AsyncIterator[AudioChunk],
        language: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[PartialResult]:
        pass

    @abstractmethod
    async def get_supported_languages(self) -> List[str]:
        pass

    async def transcribe_chunk(
        self,
        chunk: AudioChunk,
        language: Optional[str] = None,
        **kwargs,
    ) -> STTResult:
        return await self.transcribe(
            audio=chunk.data,
            sample_rate=chunk.sample_rate,
            language=language,
            **kwargs,
        )

    @property
    def supports_streaming(self) -> bool:
        """Whether this provider supports true streaming (partials during speech).

        Batch providers (Whisper) return False — the BufferedBatchSession fallback
        emits one final event per turn.
        """
        return False

    async def open_stream(
        self,
        sample_rate: int = 16000,
        language: Optional[str] = None,
        **kwargs,
    ) -> StreamingSession:
        """Open a streaming session.

        Default implementation: BufferedBatchSession wraps the batch transcribe()
        method so the caller code can be identical for streaming and batch providers.
        Override in subclasses that support true streaming.
        """
        return BufferedBatchSession(
            stt=self,
            sample_rate=sample_rate,
            language=language,
            **kwargs,
        )

    def _resolve_language(self, language: Optional[str]) -> str:
        return language or self.config.language


class BufferedBatchSession(StreamingSession):
    """Fake streaming session for batch STT providers.

    Buffers all audio sent via send_audio() and transcribes once close() is called.
    Emits a single final TranscriptEvent. This lets the route code use the same
    pattern for batch and streaming providers — the route just won't see partials.

    For VAD-driven routes, prefer transcribe_audio(audio_buffer) to skip
    transcribing leading silence: pass the VAD-trimmed speech buffer at
    SPEECH_END instead of feeding every chunk through send_audio.
    """

    def __init__(
        self,
        stt: "BaseSTT",
        sample_rate: int,
        language: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__()
        self._stt = stt
        self._sample_rate = sample_rate
        self._language = language
        self._kwargs = kwargs
        self._buffer: List[np.ndarray] = []

    async def send_audio(self, audio: np.ndarray) -> None:
        if self._closed:
            return
        self._buffer.append(audio)

    async def transcribe_audio(self, audio: np.ndarray) -> None:
        """Transcribe an explicit audio buffer and close the session."""
        if self._closed:
            return
        if audio.dtype != np.float32:
            audio_float = audio.astype(np.float32)
            if np.max(np.abs(audio_float)) > 1.0:
                audio_float = audio_float / 32768.0
        else:
            audio_float = audio
        self._buffer = [audio_float]
        await self.close()

    async def close(self) -> None:
        if self._closed:
            return
        try:
            if self._buffer:
                full_audio = np.concatenate(self._buffer)
                if full_audio.dtype != np.float32:
                    full_audio = full_audio.astype(np.float32)
                    if np.max(np.abs(full_audio)) > 1.0:
                        full_audio = full_audio / 32768.0

                result = await self._stt.transcribe(
                    full_audio,
                    sample_rate=self._sample_rate,
                    language=self._language,
                    **self._kwargs,
                )
                await self._events.put(
                    TranscriptEvent(
                        text=result.text,
                        is_final=True,
                        confidence=result.confidence or 0.0,
                        start_time=0.0,
                        end_time=result.duration,
                        language=result.language,
                    )
                )
        except Exception:
            # Still need to terminate the stream even on failure
            pass
        finally:
            await super().close()
