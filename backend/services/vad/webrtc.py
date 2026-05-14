from typing import Literal

import numpy as np
import webrtcvad

from utils import get_logger

logger = get_logger(__name__)

WebRTCAggressiveness = Literal[0, 1, 2, 3]
WebRTCFrameMs = Literal[10, 20, 30]


class WebRTCVAD:
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_ms: WebRTCFrameMs = 20,
        aggressiveness: WebRTCAggressiveness = 1,
    ) -> None:
        if sample_rate not in (8000, 16000, 32000, 48000):
            raise ValueError(f"WebRTC VAD requires 8/16/32/48 kHz; got {sample_rate}")
        if frame_ms not in (10, 20, 30):
            raise ValueError(f"WebRTC VAD requires 10/20/30 ms frames; got {frame_ms}")

        self._sample_rate = sample_rate
        self._frame_ms = frame_ms
        self._frame_samples = int(sample_rate * frame_ms / 1000)
        self._frame_bytes = self._frame_samples * 2  # int16
        self._vad = webrtcvad.Vad(aggressiveness)

    def is_speech(self, audio_int16: np.ndarray) -> bool:
        """Return True if ANY 20 ms sub-frame contains speech.

        Inputs of arbitrary length are split into frame_ms sub-frames and ORed.
        For the typical 100 ms client chunk this runs the detector 5 times,
        which is still under 100 microseconds total.
        """
        if audio_int16.dtype != np.int16:
            audio_int16 = audio_int16.astype(np.int16)

        n = len(audio_int16)
        if n < self._frame_samples:
            return False

        usable = (n // self._frame_samples) * self._frame_samples
        audio_int16 = audio_int16[:usable]
        raw = audio_int16.tobytes()

        for offset in range(0, usable * 2, self._frame_bytes):
            frame = raw[offset : offset + self._frame_bytes]
            if self._vad.is_speech(frame, self._sample_rate):
                return True
        return False

    def speech_frames(self, audio_int16: np.ndarray) -> int:
        """Return the count of frame_ms sub-frames in audio that are speech.

        Useful when callers want continuous-speech bookkeeping per chunk
        rather than just an any-speech bool.
        """
        if audio_int16.dtype != np.int16:
            audio_int16 = audio_int16.astype(np.int16)

        n = len(audio_int16)
        if n < self._frame_samples:
            return 0

        usable = (n // self._frame_samples) * self._frame_samples
        audio_int16 = audio_int16[:usable]
        raw = audio_int16.tobytes()

        count = 0
        for offset in range(0, usable * 2, self._frame_bytes):
            frame = raw[offset : offset + self._frame_bytes]
            if self._vad.is_speech(frame, self._sample_rate):
                count += 1
        return count

    @property
    def frame_ms(self) -> int:
        return self._frame_ms

    @property
    def sample_rate(self) -> int:
        return self._sample_rate


def create_webrtc_vad(
    sample_rate: int = 16000,
    frame_ms: WebRTCFrameMs = 20,
    aggressiveness: WebRTCAggressiveness = 1,
) -> WebRTCVAD:
    return WebRTCVAD(sample_rate=sample_rate, frame_ms=frame_ms, aggressiveness=aggressiveness)
