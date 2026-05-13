import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional

import numpy as np
import torch

from utils import get_logger

logger = get_logger(__name__)


def _get_device() -> torch.device:
    if torch.cuda.is_available():
        device = torch.device("cuda")
        logger.info(f"[VAD] Using CUDA device: {torch.cuda.get_device_name(0)}")
        return device
    logger.info("[VAD] CUDA not available, using CPU")
    return torch.device("cpu")


class VADState(Enum):
    SILENCE = "silence"
    SPEECH_START = "speech_start"
    SPEAKING = "speaking"
    SPEECH_END = "speech_end"


@dataclass
class VADEvent:
    state: VADState
    timestamp: float
    speech_probability: float
    audio_buffer: Optional[np.ndarray] = None
    duration_ms: float = 0.0


@dataclass
class VADConfig:
    speech_threshold: float = 0.5
    silence_threshold: float = 0.35
    min_speech_duration_ms: float = 250.0
    min_silence_duration_ms: float = 500.0
    max_speech_duration_ms: float = 30000.0
    pre_roll_ms: float = 300.0
    sample_rate: int = 16000
    chunk_samples: int = 512


class SileroVAD:
    def __init__(self, config: Optional[VADConfig] = None, device: Optional[torch.device] = None):
        self.config = config or VADConfig()
        self._device = device or _get_device()
        self._model = None
        self._initialized = False

        self._state = VADState.SILENCE
        self._state_start_time: float = 0.0
        self._speech_start_time: float = 0.0

        self._audio_buffer: List[np.ndarray] = []
        self._max_buffer_chunks = (
            int(self.config.max_speech_duration_ms / 1000 * self.config.sample_rate / self.config.chunk_samples) + 10
        )

        pre_roll_samples = int(self.config.pre_roll_ms * self.config.sample_rate / 1000)
        self._pre_roll_buffer: deque = deque(maxlen=pre_roll_samples // self.config.chunk_samples + 1)

        self._prob_history: deque = deque(maxlen=5)

        self._on_speech_start: Optional[Callable[[VADEvent], None]] = None
        self._on_speech_end: Optional[Callable[[VADEvent], None]] = None
        self._on_vad_update: Optional[Callable[[VADEvent], None]] = None

        self._total_chunks_processed = 0
        self._speech_chunks = 0

    async def initialize(self) -> None:
        if self._initialized:
            return

        logger.info("Loading Silero VAD model...")

        try:
            from silero_vad import load_silero_vad

            self._model = load_silero_vad()
            logger.info("Silero VAD model loaded (silero-vad package)")
        except ImportError:
            self._model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad", model="silero_vad", force_reload=False, trust_repo=True
            )
            logger.info("Silero VAD model loaded (torch.hub)")

        self._initialized = True
        self._state_start_time = time.time()
        self._reset_model_states()
        logger.info(f"Silero VAD initialized (threshold={self.config.speech_threshold})")

    def _reset_model_states(self) -> None:
        if self._model is not None:
            try:
                self._model.reset_states()
            except AttributeError:
                logger.warning("VAD model does not support reset_states()")

    def get_speech_probability(self, audio_chunk: np.ndarray) -> float:
        if not self._initialized or self._model is None:
            return 0.0

        if audio_chunk.dtype != np.float32:
            audio_chunk = audio_chunk.astype(np.float32)

        if np.abs(audio_chunk).max() > 1.0:
            audio_chunk = audio_chunk / 32768.0

        window_size = self.config.chunk_samples

        if len(audio_chunk) < window_size:
            audio_chunk = np.pad(audio_chunk, (0, window_size - len(audio_chunk)))

        max_prob = 0.0
        for i in range(0, len(audio_chunk) - window_size + 1, window_size):
            window = audio_chunk[i : i + window_size]
            tensor = torch.from_numpy(window).to(self._device)

            with torch.no_grad():
                prob = self._model(tensor, self.config.sample_rate).item()
                max_prob = max(max_prob, prob)

        return max_prob

    def process_chunk(self, audio_chunk: np.ndarray) -> Optional[VADEvent]:
        if not self._initialized:
            return None

        self._total_chunks_processed += 1
        current_time = time.time()

        if len(audio_chunk) == 0:
            logger.warning("VAD received empty audio chunk")
            return None

        if audio_chunk.dtype == np.int16:
            audio_float = audio_chunk.astype(np.float32) / 32768.0
        else:
            audio_float = audio_chunk.astype(np.float32)

        audio_max = np.abs(audio_float).max()
        if audio_max < 0.001:
            if self._total_chunks_processed % 100 == 0:
                logger.debug(f"VAD: Audio very quiet (max={audio_max:.4f})")

        prob = self.get_speech_probability(audio_float)
        self._prob_history.append(prob)
        smoothed_prob = np.mean(list(self._prob_history))

        is_speech = smoothed_prob > self.config.speech_threshold
        is_silence = smoothed_prob < self.config.silence_threshold

        if is_speech:
            self._speech_chunks += 1

        event = None
        state_duration_ms = (current_time - self._state_start_time) * 1000

        if self._state == VADState.SILENCE:
            self._pre_roll_buffer.append(audio_chunk.copy())

            if is_speech:
                self._state = VADState.SPEECH_START
                self._state_start_time = current_time
                self._speech_start_time = current_time

                pre_roll_chunks = list(self._pre_roll_buffer)
                if pre_roll_chunks:
                    first_chunk = pre_roll_chunks[0].copy().astype(np.float32)
                    fade_samples = min(len(first_chunk), 160)
                    fade_in = np.linspace(0, 1, fade_samples)
                    first_chunk[:fade_samples] *= fade_in
                    pre_roll_chunks[0] = first_chunk.astype(np.int16)

                self._audio_buffer = pre_roll_chunks
                self._audio_buffer.append(audio_chunk.copy())
                logger.debug(f"Speech start detected (prob={smoothed_prob:.2f})")

        elif self._state == VADState.SPEECH_START:
            if len(self._audio_buffer) < self._max_buffer_chunks:
                self._audio_buffer.append(audio_chunk.copy())
            else:
                logger.warning("[VAD] Audio buffer full, dropping chunk (prevent OOM)")

            if is_silence:
                self._state = VADState.SILENCE
                self._state_start_time = current_time
                self._audio_buffer = []
                logger.debug("Speech too short, returning to silence")
            elif state_duration_ms >= self.config.min_speech_duration_ms:
                self._state = VADState.SPEAKING
                self._state_start_time = current_time
                event = VADEvent(
                    state=VADState.SPEECH_START,
                    timestamp=self._speech_start_time,
                    speech_probability=smoothed_prob,
                )

                if self._on_speech_start:
                    self._on_speech_start(event)
                logger.info(f"Speech confirmed (duration={state_duration_ms:.0f}ms)")

        elif self._state == VADState.SPEAKING:
            if len(self._audio_buffer) < self._max_buffer_chunks:
                self._audio_buffer.append(audio_chunk.copy())
            else:
                logger.warning("[VAD] Audio buffer full, dropping chunk (prevent OOM)")
            speech_duration_ms = (current_time - self._speech_start_time) * 1000

            if speech_duration_ms >= self.config.max_speech_duration_ms:
                logger.warning(f"Max speech duration reached ({speech_duration_ms:.0f}ms)")
                event = self._end_speech(current_time, smoothed_prob)
            elif is_silence:
                self._state = VADState.SPEECH_END
                self._state_start_time = current_time

        elif self._state == VADState.SPEECH_END:
            if len(self._audio_buffer) < self._max_buffer_chunks:
                self._audio_buffer.append(audio_chunk.copy())

            if is_speech:
                self._state = VADState.SPEAKING
                self._state_start_time = current_time
                logger.debug("Speech resumed")
            elif state_duration_ms >= self.config.min_silence_duration_ms:
                event = self._end_speech(current_time, smoothed_prob)

        if self._on_vad_update:
            update_event = VADEvent(
                state=self._state,
                timestamp=current_time,
                speech_probability=smoothed_prob,
            )
            self._on_vad_update(update_event)

        return event

    def _end_speech(self, current_time: float, prob: float) -> VADEvent:
        speech_duration_ms = (current_time - self._speech_start_time) * 1000

        if self._audio_buffer:
            full_audio = np.concatenate(self._audio_buffer)
        else:
            full_audio = np.array([], dtype=np.int16)

        event = VADEvent(
            state=VADState.SPEECH_END,
            timestamp=current_time,
            speech_probability=prob,
            audio_buffer=full_audio,
            duration_ms=speech_duration_ms,
        )

        if self._on_speech_end:
            self._on_speech_end(event)

        logger.info(f"Speech ended (duration={speech_duration_ms:.0f}ms, samples={len(full_audio)})")

        self._state = VADState.SILENCE
        self._state_start_time = current_time
        self._audio_buffer = []
        self._pre_roll_buffer.clear()

        return event

    def force_end_speech(self) -> Optional[VADEvent]:
        if self._state not in (VADState.SPEAKING, VADState.SPEECH_END, VADState.SPEECH_START):
            return None
        logger.info("Forcing speech end (interrupt)")
        return self._end_speech(time.time(), 0.0)

    def reset(self) -> None:
        self._state = VADState.SILENCE
        self._state_start_time = time.time()
        self._speech_start_time = 0.0
        self._audio_buffer = []
        self._pre_roll_buffer.clear()
        self._prob_history.clear()
        self._reset_model_states()
        logger.debug("VAD state reset (including model states)")

    async def shutdown(self) -> None:
        try:
            logger.info("[VAD] Shutting down VAD service")
            self._audio_buffer.clear()
            self._pre_roll_buffer.clear()
            self._prob_history.clear()
            if self._model is not None:
                del self._model
                self._model = None
            if self._device.type == "cuda":
                torch.cuda.empty_cache()

            self._initialized = False
            logger.info("[VAD] Shutdown complete")
        except Exception as e:
            logger.error(f"[VAD] Shutdown error: {e}")

    def is_speaking(self) -> bool:
        return self._state in (VADState.SPEAKING, VADState.SPEECH_END)

    def is_speech_starting(self) -> bool:
        return self._state == VADState.SPEECH_START

    @property
    def state(self) -> VADState:
        return self._state

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def on_speech_start(self, callback: Callable[[VADEvent], None]) -> None:
        self._on_speech_start = callback

    def on_speech_end(self, callback: Callable[[VADEvent], None]) -> None:
        self._on_speech_end = callback

    def on_vad_update(self, callback: Callable[[VADEvent], None]) -> None:
        self._on_vad_update = callback

    def get_stats(self) -> dict:
        return {
            "total_chunks": self._total_chunks_processed,
            "speech_chunks": self._speech_chunks,
            "speech_ratio": self._speech_chunks / max(1, self._total_chunks_processed),
            "current_state": self._state.value,
        }


def create_silero_vad(config: Optional[VADConfig] = None, device: Optional[torch.device] = None) -> SileroVAD:
    return SileroVAD(config, device)


async def initialize_vad(config: Optional[VADConfig] = None, device: Optional[torch.device] = None) -> SileroVAD:
    vad = create_silero_vad(config, device)
    await vad.initialize()
    return vad
