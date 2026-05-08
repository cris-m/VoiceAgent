import asyncio
import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch, call

from services.voice_pipeline import VoicePipeline
from services.vad.silero import VADState, VADEvent, VADConfig, SileroVAD
from services.audio.aec import AECConfig, EchoCanceller, EchoState


def _make_mock_stt():
    stt = MagicMock()
    stt.supports_streaming = False
    stt.initialize = AsyncMock()
    stt.shutdown = AsyncMock()
    stt.health_check = AsyncMock(return_value=True)
    return stt


def _make_mock_tts():
    tts = MagicMock()
    tts.name = "mock_tts"
    tts.initialize = AsyncMock()
    tts.shutdown = AsyncMock()
    tts.health_check = AsyncMock(return_value=True)
    tts.supports_speed = False
    tts.supports_language = False
    tts.supports_voice_cloning = False
    return tts


def _make_mock_vad():
    vad = MagicMock(spec=SileroVAD)
    vad.config = VADConfig()
    vad.initialize = AsyncMock()
    vad.state = VADState.SILENCE
    vad.is_speaking = MagicMock(return_value=False)
    vad.is_initialized = False
    vad.process_chunk = MagicMock(return_value=None)
    vad.get_speech_probability = MagicMock(return_value=0.0)
    vad.reset = MagicMock()
    return vad


def _make_pipeline() -> VoicePipeline:
    stt = _make_mock_stt()
    tts = _make_mock_tts()
    vad = _make_mock_vad()
    pipeline = VoicePipeline(stt=stt, tts=tts, vad=vad)
    pipeline._initialized = True  # skip the real initialize() path
    return pipeline


class TestInitialization:
    @pytest.mark.asyncio
    async def test_initialize_calls_all_sub_services(self):
        stt = _make_mock_stt()
        tts = _make_mock_tts()
        vad = _make_mock_vad()

        pipeline = VoicePipeline(stt=stt, tts=tts, vad=vad)
        await pipeline.initialize()

        stt.initialize.assert_called_once()
        tts.initialize.assert_called_once()
        vad.initialize.assert_called_once()
        assert pipeline.is_initialized is True

    @pytest.mark.asyncio
    async def test_initialize_is_idempotent(self):
        stt = _make_mock_stt()
        tts = _make_mock_tts()
        vad = _make_mock_vad()

        pipeline = VoicePipeline(stt=stt, tts=tts, vad=vad)
        await pipeline.initialize()
        await pipeline.initialize()

        stt.initialize.assert_called_once()
        tts.initialize.assert_called_once()
        vad.initialize.assert_called_once()


class TestProcessAudioChunk:
    def test_process_chunk_returns_vad_event_and_echo_flag(self):
        pipeline = _make_pipeline()
        audio = np.zeros(512, dtype=np.int16)

        expected_event = VADEvent(
            state=VADState.SPEECH_START,
            timestamp=0.0,
            speech_probability=0.8,
        )
        pipeline.vad.process_chunk = MagicMock(return_value=expected_event)

        pipeline._aec._is_playing = False

        event, is_echo = pipeline.process_audio_chunk(audio)
        assert event is expected_event
        assert is_echo is False

    def test_process_chunk_echo_flag_when_tts_playing(self):
        pipeline = _make_pipeline()
        audio = np.zeros(512, dtype=np.int16)
        pipeline.vad.process_chunk = MagicMock(return_value=None)

        pipeline._aec._is_playing = True

        _event, is_echo = pipeline.process_audio_chunk(audio)
        assert is_echo is True

    def test_vad_state_delegated_to_vad_object(self):
        pipeline = _make_pipeline()
        pipeline.vad.state = VADState.SPEAKING
        assert pipeline.get_vad_state() == VADState.SPEAKING

    def test_is_speaking_delegated_to_vad(self):
        pipeline = _make_pipeline()
        pipeline.vad.is_speaking.return_value = True
        assert pipeline.is_speaking() is True

        pipeline.vad.is_speaking.return_value = False
        assert pipeline.is_speaking() is False


class TestGetSpeechProbability:
    def test_int16_audio_normalized_before_vad(self):
        pipeline = _make_pipeline()
        audio_int16 = np.array([16384, -16384, 0], dtype=np.int16)

        def capture_float_audio(audio_f32):
            assert audio_f32.dtype == np.float32
            assert np.max(np.abs(audio_f32)) <= 1.0
            return 0.5

        pipeline.vad.get_speech_probability = capture_float_audio
        prob = pipeline.get_speech_probability(audio_int16)
        assert prob == 0.5

    def test_float32_audio_passed_as_is(self):
        pipeline = _make_pipeline()
        audio_f32 = np.array([0.1, -0.2, 0.3], dtype=np.float32)

        def capture(audio_f32_in):
            assert audio_f32_in.dtype == np.float32
            return 0.7

        pipeline.vad.get_speech_probability = capture
        prob = pipeline.get_speech_probability(audio_f32)
        assert prob == 0.7


class TestAECState:
    def test_on_interrupt_clears_aec_and_resets_vad(self):
        pipeline = _make_pipeline()
        pipeline._aec._is_playing = True
        pipeline._is_speaking = True

        pipeline.on_interrupt()

        assert pipeline._aec._is_playing is False
        assert pipeline._is_speaking is False
        pipeline.vad.reset.assert_called_once()

    def test_get_aec_state_returns_string(self):
        pipeline = _make_pipeline()
        pipeline._aec._is_playing = False
        assert pipeline.get_aec_state() == EchoState.IDLE.value

        pipeline._aec._is_playing = True
        assert pipeline.get_aec_state() == EchoState.PLAYING.value

    def test_is_ai_speaking_reflects_internal_flag(self):
        pipeline = _make_pipeline()
        pipeline._is_speaking = False
        assert pipeline.is_ai_speaking() is False

        pipeline._is_speaking = True
        assert pipeline.is_ai_speaking() is True

    def test_on_tts_complete_clears_aec_and_speaking_flag(self):
        pipeline = _make_pipeline()
        pipeline._aec._is_playing = True
        pipeline._is_speaking = True

        pipeline.on_tts_complete()

        assert pipeline._aec._is_playing is False
        assert pipeline._is_speaking is False


class TestSynthesizeStream:
    @pytest.mark.asyncio
    async def test_synthesize_stream_sets_is_speaking_true(self):
        from services.audio.base import AudioChunk

        pipeline = _make_pipeline()
        speaking_flag_during_yield = []

        async def fake_synth(text, voice=None, **kwargs):
            yield AudioChunk(data=np.zeros(100, dtype=np.float32), sample_rate=16000)

        pipeline.tts.synthesize_stream = fake_synth

        async for chunk in pipeline.synthesize_stream("hello", voice="v"):
            if chunk["type"] == "audio":
                speaking_flag_during_yield.append(pipeline._is_speaking)

        assert any(speaking_flag_during_yield)

    @pytest.mark.asyncio
    async def test_synthesize_stream_yields_audio_info_first(self):
        from services.audio.base import AudioChunk

        pipeline = _make_pipeline()

        async def fake_synth(text, voice=None, **kwargs):
            yield AudioChunk(data=np.zeros(200, dtype=np.float32), sample_rate=22050)

        pipeline.tts.synthesize_stream = fake_synth

        events = []
        async for event in pipeline.synthesize_stream("hi", voice="v"):
            events.append(event["type"])

        assert events[0] == "audio_info", f"Expected audio_info first, got {events}"
        assert "audio" in events

    @pytest.mark.asyncio
    async def test_synthesize_stream_audio_info_sample_rate(self):
        from services.audio.base import AudioChunk

        pipeline = _make_pipeline()

        async def fake_synth(text, voice=None, **kwargs):
            yield AudioChunk(data=np.zeros(200, dtype=np.float32), sample_rate=24000)

        pipeline.tts.synthesize_stream = fake_synth

        audio_info_events = []
        async for event in pipeline.synthesize_stream("hello", voice="v"):
            if event["type"] == "audio_info":
                audio_info_events.append(event)

        assert len(audio_info_events) == 1
        assert audio_info_events[0]["sample_rate"] == 24000

    @pytest.mark.asyncio
    async def test_synthesize_stream_adds_reference_to_aec(self):
        from services.audio.base import AudioChunk

        pipeline = _make_pipeline()
        aec_reference_calls = []
        original_add_ref = pipeline._aec.add_reference
        pipeline._aec.add_reference = lambda chunk: aec_reference_calls.append(len(chunk))

        async def fake_synth(text, voice=None, **kwargs):
            yield AudioChunk(data=np.zeros(1600, dtype=np.float32), sample_rate=16000)

        pipeline.tts.synthesize_stream = fake_synth

        async for _ in pipeline.synthesize_stream("test", voice="v"):
            pass

        assert len(aec_reference_calls) >= 1


class TestShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_calls_all_sub_services(self):
        pipeline = _make_pipeline()
        await pipeline.shutdown()

        pipeline.stt.shutdown.assert_called_once()
        pipeline.tts.shutdown.assert_called_once()
        pipeline.vad.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_cancels_pending_tts_cleanup(self):
        pipeline = _make_pipeline()
        mock_task = MagicMock()
        mock_task.done = MagicMock(return_value=False)
        mock_task.cancel = MagicMock()
        pipeline._pending_tts_cleanup = mock_task

        await pipeline.shutdown()

        mock_task.cancel.assert_called_once()
