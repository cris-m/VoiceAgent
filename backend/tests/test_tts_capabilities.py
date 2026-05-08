import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from services.tts.base import BaseTTS, TTSConfig, Voice, Language
from services.tts.kokoro import KokoroTTS
from services.tts.pocket_tts import PocketTTS


class StubTTS(BaseTTS):
    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    async def synthesize(self, text, voice=None, **kwargs):
        pass

    async def synthesize_stream(self, text, voice=None, **kwargs):
        return
        yield  # makes it an async generator

    async def get_voices(self):
        return []

    async def get_languages(self):
        return []


class TestBaseTTSDefaults:
    def test_supports_voice_cloning_is_false(self):
        tts = StubTTS("stub")
        assert tts.supports_voice_cloning is False

    def test_supports_speed_is_false(self):
        tts = StubTTS("stub")
        assert tts.supports_speed is False

    def test_supports_language_is_false(self):
        tts = StubTTS("stub")
        assert tts.supports_language is False

    def test_default_voice_from_config(self):
        config = TTSConfig(voice="my_voice")
        tts = StubTTS("stub", config=config)
        assert tts.default_voice == "my_voice"

    def test_default_voice_setter(self):
        tts = StubTTS("stub")
        tts.default_voice = "new_voice"
        assert tts.default_voice == "new_voice"

    def test_resolve_voice_raises_without_default_or_arg(self):
        tts = StubTTS("stub")
        with pytest.raises(ValueError, match="No voice specified"):
            tts._resolve_voice(None)

    def test_resolve_voice_returns_arg_over_default(self):
        config = TTSConfig(voice="default_v")
        tts = StubTTS("stub", config=config)
        assert tts._resolve_voice("explicit_v") == "explicit_v"

    def test_resolve_voice_falls_back_to_default(self):
        config = TTSConfig(voice="default_v")
        tts = StubTTS("stub", config=config)
        assert tts._resolve_voice(None) == "default_v"


class TestKokoroTTSCapabilities:
    def _make_kokoro(self) -> KokoroTTS:
        # Pass dummy paths — initialize() is never called so no files are read.
        return KokoroTTS(
            model_path="/dev/null",
            voices_path="/dev/null",
            default_voice="af_heart",
            default_language="en-us",
        )

    def test_supports_speed(self):
        assert self._make_kokoro().supports_speed is True

    def test_supports_language(self):
        assert self._make_kokoro().supports_language is True

    def test_does_not_support_voice_cloning(self):
        assert self._make_kokoro().supports_voice_cloning is False

    def test_default_voice_set_from_constructor(self):
        k = self._make_kokoro()
        assert k.default_voice == "af_heart"

    def test_name_is_kokoro(self):
        k = self._make_kokoro()
        assert "kokoro" in k.name.lower()


class TestPocketTTSCapabilities:
    def _make_pocket(self) -> PocketTTS:
        return PocketTTS(language="english", default_voice="alba")

    def test_supports_voice_cloning(self):
        assert self._make_pocket().supports_voice_cloning is True

    def test_name_is_pocket_tts(self):
        p = self._make_pocket()
        assert "pocket" in p.name.lower()

    def test_default_voice_set_from_constructor(self):
        p = self._make_pocket()
        assert p.default_voice == "alba"


class TestVoicePipelineSynthKwargsGating:
    @pytest.mark.asyncio
    async def test_pipeline_passes_kwargs_through_to_tts(self):
        # Pipeline is a thin pass-through; gating speed/language by capability
        # is the route's responsibility (tts_streamer in voice.py), not pipeline's.
        from services.voice_pipeline import VoicePipeline
        from services.vad.silero import SileroVAD, VADConfig

        tts = StubTTS("stub")
        captured_kwargs = {}

        async def fake_synthesize_stream(text, voice=None, **kwargs):
            captured_kwargs.update(kwargs)
            from services.audio.base import AudioChunk
            import numpy as np
            yield AudioChunk(data=np.zeros(100, dtype=np.float32), sample_rate=16000)

        tts.synthesize_stream = fake_synthesize_stream

        mock_stt = MagicMock()
        mock_vad = MagicMock(spec=SileroVAD)
        mock_vad.config = VADConfig()

        pipeline = VoicePipeline(stt=mock_stt, tts=tts, vad=mock_vad)
        pipeline._initialized = True

        async for _ in pipeline.synthesize_stream("hello", voice="stub_v", speed=1.5):
            pass

        assert "speed" in captured_kwargs
        assert captured_kwargs["speed"] == 1.5

    @pytest.mark.asyncio
    async def test_route_skips_speed_kwarg_when_tts_lacks_support(self):
        tts = StubTTS("stub")
        assert tts.supports_speed is False

        # Mirrors the route's conditional logic in voice.py tts_streamer
        synth_kwargs: dict = {"voice": "af_heart"}
        speed = 1.5
        if tts.supports_speed and speed:
            synth_kwargs["speed"] = float(speed)

        assert "speed" not in synth_kwargs

    @pytest.mark.asyncio
    async def test_synthesize_stream_yields_audio_info_then_audio(self):
        from services.voice_pipeline import VoicePipeline
        from services.vad.silero import SileroVAD, VADConfig
        from services.audio.base import AudioChunk
        import numpy as np

        tts = StubTTS("stub")

        async def fake_synthesize_stream(text, voice=None, **kwargs):
            yield AudioChunk(data=np.zeros(200, dtype=np.float32), sample_rate=22050)

        tts.synthesize_stream = fake_synthesize_stream

        mock_stt = MagicMock()
        mock_vad = MagicMock(spec=SileroVAD)
        mock_vad.config = VADConfig()

        pipeline = VoicePipeline(stt=mock_stt, tts=tts, vad=mock_vad)
        pipeline._initialized = True

        events = []
        async for event in pipeline.synthesize_stream("test", voice="v"):
            events.append(event)

        types = [e["type"] for e in events]
        assert types[0] == "audio_info"
        assert "audio" in types


class TestVoiceCloningSupportFlag:
    def test_pipeline_delegates_supports_voice_cloning_to_tts(self):
        from services.voice_pipeline import VoicePipeline
        from unittest.mock import MagicMock

        tts_with_cloning = MagicMock()
        tts_with_cloning.supports_voice_cloning = True

        tts_without_cloning = MagicMock()
        tts_without_cloning.supports_voice_cloning = False

        mock_stt = MagicMock()
        mock_vad = MagicMock()

        p1 = VoicePipeline(stt=mock_stt, tts=tts_with_cloning, vad=mock_vad)
        assert p1.supports_voice_cloning is True

        p2 = VoicePipeline(stt=mock_stt, tts=tts_without_cloning, vad=mock_vad)
        assert p2.supports_voice_cloning is False
