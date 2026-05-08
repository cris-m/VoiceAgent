import numpy as np
from dataclasses import dataclass
from typing import Tuple
from enum import Enum

from utils import get_logger

logger = get_logger(__name__)


class EchoState(str, Enum):
    IDLE = "idle"
    PLAYING = "playing"


@dataclass
class AECConfig:
    sample_rate: int = 16000


class EchoCanceller:
    def __init__(self, config: AECConfig | None = None):
        self.config = config or AECConfig()
        self._is_playing = False
        self._total_processed = 0
        self._echo_chunks = 0
        logger.info("EchoCanceller initialized (boolean flag mode)")

    def add_reference(self, audio: np.ndarray) -> None:
        self._is_playing = True

    def stop_playback(self) -> None:
        self._is_playing = False

    def clear(self) -> None:
        self._is_playing = False

    def process(self, mic_audio: np.ndarray) -> Tuple[np.ndarray, bool]:
        self._total_processed += 1
        is_echo = self._is_playing
        if is_echo:
            self._echo_chunks += 1
        return mic_audio, is_echo

    def get_state(self) -> EchoState:
        return EchoState.PLAYING if self._is_playing else EchoState.IDLE

    def is_active(self) -> bool:
        return self._is_playing

    def get_stats(self) -> dict:
        return {
            "state": self.get_state().value,
            "echo_chunks": self._echo_chunks,
            "total_processed": self._total_processed,
        }
