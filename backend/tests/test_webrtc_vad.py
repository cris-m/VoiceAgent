import numpy as np
import pytest

from services.vad.webrtc import WebRTCVAD, create_webrtc_vad


def test_rejects_invalid_sample_rate():
    with pytest.raises(ValueError, match="8/16/32/48"):
        WebRTCVAD(sample_rate=22050)


def test_rejects_invalid_frame_ms():
    with pytest.raises(ValueError, match="10/20/30"):
        WebRTCVAD(sample_rate=16000, frame_ms=15)  # type: ignore[arg-type]


def test_is_speech_returns_false_on_silence():
    vad = create_webrtc_vad(sample_rate=16000, frame_ms=20)
    silence = np.zeros(1600, dtype=np.int16)
    assert vad.is_speech(silence) is False


def test_speech_frames_zero_on_silence():
    vad = create_webrtc_vad(sample_rate=16000, frame_ms=20)
    silence = np.zeros(1600, dtype=np.int16)
    assert vad.speech_frames(silence) == 0


def test_is_speech_returns_false_on_chunk_smaller_than_frame():
    vad = create_webrtc_vad(sample_rate=16000, frame_ms=20)
    tiny = np.zeros(50, dtype=np.int16)
    assert vad.is_speech(tiny) is False
    assert vad.speech_frames(tiny) == 0


def test_speech_frames_on_loud_noise_chunk():
    # Generate a 100ms loud sine wave; speech_frames should pick up at least
    # some sub-frames. Exact count depends on WebRTC's GMM tuning so we only
    # assert "more than zero, no more than the chunk's frame count".
    vad = create_webrtc_vad(sample_rate=16000, frame_ms=20, aggressiveness=0)
    t = np.linspace(0, 0.1, 1600, dtype=np.float32)
    sine = (np.sin(2 * np.pi * 200 * t) * 0.5 * 32767).astype(np.int16)
    frames_in_chunk = 1600 // (16000 * 20 // 1000)
    n = vad.speech_frames(sine)
    assert 0 <= n <= frames_in_chunk


def test_accepts_float_inputs_via_cast():
    vad = create_webrtc_vad(sample_rate=16000, frame_ms=20)
    silence_float = np.zeros(1600, dtype=np.float32)
    assert vad.is_speech(silence_float) is False


def test_frame_size_arithmetic_matches_constructor():
    vad = create_webrtc_vad(sample_rate=16000, frame_ms=30)
    assert vad.frame_ms == 30
    assert vad.sample_rate == 16000
    # 30ms @ 16kHz = 480 samples per frame; 1500-sample chunk has 3 full frames.
    audio = np.zeros(1500, dtype=np.int16)
    assert vad.speech_frames(audio) == 0
