from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator, Optional

import numpy as np


class AudioFormat(Enum):
    PCM_16 = "pcm_16"
    PCM_32 = "pcm_32"
    FLOAT_32 = "float32"


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    format: AudioFormat = AudioFormat.FLOAT_32
    chunk_size: int = 512


@dataclass
class AudioChunk:
    data: np.ndarray
    sample_rate: int
    channels: int = 1
    timestamp: Optional[float] = None
    is_speech: Optional[bool] = None
    metadata: dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return len(self.data) / self.sample_rate

    @property
    def samples(self) -> int:
        return len(self.data)


class BaseAudioProcessor(ABC):
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()

    @staticmethod
    def resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        if orig_sr == target_sr:
            return audio
        import librosa

        return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)

    @staticmethod
    def to_mono(audio: np.ndarray) -> np.ndarray:
        if audio.ndim == 1:
            return audio
        return np.mean(audio, axis=0)

    @staticmethod
    def normalize(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
        rms = np.sqrt(np.mean(audio**2))
        if rms == 0:
            return audio
        target_rms = 10 ** (target_db / 20)
        return audio * (target_rms / rms)

    @staticmethod
    def pcm16_to_float(audio: np.ndarray) -> np.ndarray:
        return audio.astype(np.float32) / 32768.0

    @staticmethod
    def float_to_pcm16(audio: np.ndarray) -> np.ndarray:
        audio = np.clip(audio, -1.0, 1.0)
        return (audio * 32767).astype(np.int16)

    @staticmethod
    def bytes_to_array(data: bytes, format: AudioFormat = AudioFormat.PCM_16) -> np.ndarray:
        if format == AudioFormat.PCM_16:
            return np.frombuffer(data, dtype=np.int16)
        elif format == AudioFormat.PCM_32:
            return np.frombuffer(data, dtype=np.int32)
        elif format == AudioFormat.FLOAT_32:
            return np.frombuffer(data, dtype=np.float32)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @staticmethod
    def array_to_bytes(audio: np.ndarray, format: AudioFormat = AudioFormat.PCM_16) -> bytes:
        if format == AudioFormat.PCM_16:
            if audio.dtype != np.int16:
                audio = BaseAudioProcessor.float_to_pcm16(audio)
            return audio.tobytes()
        elif format == AudioFormat.PCM_32:
            return audio.astype(np.int32).tobytes()
        elif format == AudioFormat.FLOAT_32:
            return audio.astype(np.float32).tobytes()
        else:
            raise ValueError(f"Unsupported format: {format}")

    def prepare_audio(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        audio = self.to_mono(audio)
        audio = self.resample(audio, sample_rate, self.config.sample_rate)
        return audio.astype(np.float32)

    @abstractmethod
    async def process(self, audio: AudioChunk) -> AudioChunk:
        pass

    @abstractmethod
    async def process_stream(self, stream: AsyncIterator[AudioChunk]) -> AsyncIterator[AudioChunk]:
        pass
