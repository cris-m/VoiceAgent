import asyncio
from typing import AsyncIterator, Optional, Tuple

import numpy as np

from services.audio.aec import AECConfig, EchoCanceller
from services.stt.base import BaseSTT, StreamingSession
from services.stt.whisper import WhisperSTT
from services.tts.base import BaseTTS
from services.vad.silero import SileroVAD, VADConfig, VADEvent, VADState
from utils import get_logger

logger = get_logger(__name__)


class VoicePipeline:
    def __init__(
        self,
        stt: Optional[BaseSTT] = None,
        tts: Optional[BaseTTS] = None,
        vad: Optional[SileroVAD] = None,
        vad_config: Optional[VADConfig] = None,
        aec_config: Optional[AECConfig] = None,
    ):
        self._stt = stt or self._create_default_stt()
        self._tts = tts or self._create_default_tts()
        self._vad = vad or self._create_default_vad(vad_config)
        self._aec = EchoCanceller(aec_config or AECConfig())
        self._is_speaking = False
        self._initialized = False
        self._init_lock = asyncio.Lock()
        # Deferred AEC cleanup: keep _is_playing=True while frontend drains its
        # playback queue so TTS bleed is still flagged as echo (not treated as
        # user speech by VAD). Cancelled when the next sentence starts.
        self._pending_tts_cleanup: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        # Double-checked locking: cheap pre-check avoids lock acquisition on the
        # hot path, while the in-lock check coalesces concurrent first-callers
        # so the slow Whisper load happens exactly once.
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            logger.info("Initializing Voice Pipeline...")

            await self._stt.initialize()
            stt_name = type(self._stt).__name__
            logger.info(f"✅ STT: {stt_name}")

            await self._tts.initialize()
            tts_name = self._tts.name
            logger.info(f"✅ TTS: {tts_name}")

            await self._vad.initialize()
            logger.info("✅ VAD: Silero")

            self._initialized = True
            logger.info(f"🎙️ Voice Pipeline Ready — STT: {stt_name} | TTS: {tts_name} | VAD: Silero")

    def process_audio_chunk(self, audio_chunk: np.ndarray) -> Tuple[Optional[VADEvent], bool]:
        clean_audio, is_echo = self._aec.process(audio_chunk)

        if is_echo:
            logger.debug("Echo suppressed in audio chunk")

        vad_event = self._vad.process_chunk(clean_audio)
        return vad_event, is_echo

    def get_vad_state(self) -> VADState:
        return self._vad.state

    def is_speaking(self) -> bool:
        return self._vad.is_speaking()

    def get_speech_probability(self, audio_chunk: np.ndarray) -> float:
        if audio_chunk.dtype == np.int16:
            audio_float = audio_chunk.astype(np.float32) / 32768.0
        else:
            audio_float = audio_chunk.astype(np.float32)
        return self._vad.get_speech_probability(audio_float)

    def on_tts_complete(self) -> None:
        """Signal TTS playback completed. Clear AEC immediately.

        The browser already handles echo cancellation via getUserMedia
        echoCancellation:true. A backend cooldown on top of that causes
        double-suppression, making the next user utterance too quiet for STT.
        """
        self._aec.clear()
        self._is_speaking = False
        logger.debug("TTS playback complete, AEC cleared")

    def on_interrupt(self) -> None:
        self._aec.clear()
        self._vad.reset()
        self._is_speaking = False
        logger.info("Interrupt: AEC and VAD reset")

    def get_aec_state(self) -> str:
        return self._aec.get_state().value

    def is_ai_speaking(self) -> bool:
        return self._is_speaking

    async def open_stt_stream(
        self,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> StreamingSession:
        """Open a streaming STT session.

        Whisper buffers audio and emits a single final event on close().
        """
        if not self._initialized:
            await self.initialize()
        return await self._stt.open_stream(sample_rate=sample_rate, language=language)

    @property
    def stt_supports_streaming(self) -> bool:
        return self._stt.supports_streaming

    @property
    def supports_voice_cloning(self) -> bool:
        return self._tts.supports_voice_cloning

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[dict]:
        if not self._initialized:
            await self.initialize()

        # Cancel pending AEC cleanup so _is_playing stays True between sentences.
        if self._pending_tts_cleanup is not None and not self._pending_tts_cleanup.done():
            self._pending_tts_cleanup.cancel()
        self._pending_tts_cleanup = None

        self._is_speaking = True
        audio_info_sent = False
        total_samples = 0
        sample_rate_latest: Optional[int] = None
        chunk_duration_ms = 100
        completed_naturally = False

        try:
            async for audio_chunk in self._tts.synthesize_stream(text, voice=voice, **kwargs):
                sample_rate_latest = audio_chunk.sample_rate
                # Recompute chunk_size each iteration in case the provider
                # changes sample_rate mid-stream.
                chunk_size = max(1, int(sample_rate_latest * chunk_duration_ms / 1000))

                if not audio_info_sent:
                    yield {"type": "audio_info", "sample_rate": sample_rate_latest}
                    audio_info_sent = True

                audio_float = audio_chunk.data

                if total_samples == 0:
                    fade_samples = min(int(sample_rate_latest * 0.015), len(audio_float))
                    fade_in = np.linspace(0, 1, fade_samples, dtype=np.float32)
                    audio_float = audio_float.copy()
                    audio_float[:fade_samples] *= fade_in

                audio_int16 = (audio_float * 32767).astype(np.int16)
                total_samples += len(audio_int16)

                for i in range(0, len(audio_int16), chunk_size):
                    chunk = audio_int16[i : i + chunk_size]
                    self._aec.add_reference(chunk)
                    yield {"type": "audio", "audio": chunk}

            if not total_samples:
                logger.warning("[TTS] No audio chunks produced")
            completed_naturally = True
        finally:
            if completed_naturally and total_samples > 0 and sample_rate_latest:
                cleanup_delay_s = total_samples / sample_rate_latest + 0.15
                self._pending_tts_cleanup = asyncio.create_task(self._delayed_tts_complete(cleanup_delay_s))
            else:
                self.on_tts_complete()

    async def _delayed_tts_complete(self, delay_s: float) -> None:
        try:
            await asyncio.sleep(delay_s)
        except asyncio.CancelledError:
            return
        self.on_tts_complete()

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def stt(self) -> BaseSTT:
        return self._stt

    @property
    def tts(self) -> BaseTTS:
        return self._tts

    @property
    def vad(self) -> SileroVAD:
        return self._vad

    async def shutdown(self) -> None:
        try:
            logger.info("Shutting down Voice Pipeline...")
            if self._pending_tts_cleanup is not None and not self._pending_tts_cleanup.done():
                self._pending_tts_cleanup.cancel()
            self._pending_tts_cleanup = None

            if hasattr(self._stt, "shutdown"):
                await self._stt.shutdown()
            if hasattr(self._tts, "shutdown"):
                await self._tts.shutdown()
            if hasattr(self._vad, "shutdown"):
                await self._vad.shutdown()

            logger.info("Voice Pipeline shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down Voice Pipeline: {e}")

    def _create_default_stt(self) -> BaseSTT:
        from config.settings import settings

        logger.info(f"[Pipeline] Whisper model: {settings.WHISPER_MODEL}")
        return WhisperSTT(
            model_size=settings.WHISPER_MODEL,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
            cpu_threads=settings.WHISPER_CPU_THREADS,
        )

    def _create_default_tts(self) -> BaseTTS:
        from config.settings import settings

        provider = (settings.TTS_PROVIDER or "kokoro").lower()
        logger.info(f"[Pipeline] TTS provider: {provider}")

        if provider == "pocket_tts":
            from services.tts.pocket_tts import PocketTTS

            return PocketTTS(
                language=settings.POCKET_TTS_LANGUAGE,
                default_voice=settings.POCKET_TTS_VOICE,
            )

        from services.tts.kokoro import KokoroTTS

        return KokoroTTS(
            model_path=settings.KOKORO_MODEL_PATH,
            voices_path=settings.KOKORO_VOICES_PATH,
            default_voice=settings.KOKORO_VOICE,
            default_language=settings.KOKORO_LANGUAGE,
            speed=settings.KOKORO_SPEED,
        )

    def _create_default_vad(self, config: Optional[VADConfig]) -> SileroVAD:
        if config is None:
            config = VADConfig(
                speech_threshold=0.5,
                silence_threshold=0.35,
                min_speech_duration_ms=100.0,
                min_silence_duration_ms=300.0,
                pre_roll_ms=350.0,
            )
        return SileroVAD(config)


_pipeline: Optional[VoicePipeline] = None
_pipeline_lock = asyncio.Lock()
_pipeline_initialized = False


async def initialize_voice_pipeline() -> None:
    global _pipeline, _pipeline_initialized
    async with _pipeline_lock:
        if not _pipeline_initialized:
            _pipeline = VoicePipeline()
            _pipeline_initialized = True
    # Fire-and-forget warmup so the app accepts requests immediately.
    asyncio.create_task(_pipeline.initialize())


async def shutdown_voice_pipeline() -> None:
    global _pipeline
    async with _pipeline_lock:
        if _pipeline is not None:
            await _pipeline.shutdown()
            _pipeline = None
            _pipeline_initialized = False


def get_voice_pipeline() -> VoicePipeline:
    if _pipeline is None:
        raise RuntimeError("VoicePipeline not initialized. Call initialize_voice_pipeline() first.")
    return _pipeline


def create_voice_pipeline_for_connection() -> VoicePipeline:
    """Per-connection pipeline: fresh VAD (stateful, not thread-safe),
    shared STT/TTS (stateless after model load)."""
    from services.vad.silero import VADConfig, create_silero_vad

    vad_config = VADConfig(
        speech_threshold=0.5,
        silence_threshold=0.35,
        min_speech_duration_ms=100.0,
        min_silence_duration_ms=300.0,
        pre_roll_ms=350.0,
    )
    per_connection_vad = create_silero_vad(vad_config)

    singleton = get_voice_pipeline()
    return VoicePipeline(
        stt=singleton.stt,
        tts=singleton.tts,
        vad=per_connection_vad,
    )
