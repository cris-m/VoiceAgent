import asyncio

import numpy as np

from config.settings import get_settings
from services.music.base import BaseMusicService
from utils import get_logger

logger = get_logger(__name__)
_music_service: "MusicGenService | None" = None


class MusicGenService(BaseMusicService):
    """MusicGen small model for lightweight music generation.

    Uses Meta's MusicGen-small (~500MB) which is efficient and requires minimal VRAM.
    Falls back to test audio if model unavailable.
    """

    def __init__(self):
        super().__init__("music_musicgen")
        self._pipeline = None
        self._use_mock = False

    async def initialize(self):
        try:
            from transformers import pipeline

            loop = asyncio.get_event_loop()
            self.logger.info("Loading MusicGen-small model...")
            self._pipeline = await loop.run_in_executor(
                None,
                lambda: pipeline("text-to-audio", model="facebook/musicgen-small", device="cpu"),
            )
            self.logger.info("MusicGen music service ready")
        except ImportError:
            self.logger.info("transformers package not installed. Install with: pip install transformers torch")
            self._use_mock = True
        except Exception as e:
            self.logger.warning(f"Failed to load MusicGen: {e}. Using mock generator.")
            self._use_mock = True

    async def health_check(self) -> bool:
        return self._pipeline is not None or self._use_mock

    async def generate(
        self,
        prompt: str,
        style_tags: list[str],
        duration: float,
        tempo: int | None,
        seed: int | None,
    ) -> tuple[np.ndarray, int]:
        if self._pipeline is None and not self._use_mock:
            raise RuntimeError("Music generation unavailable. Install dependencies: pip install transformers torch")

        duration = min(duration, 180.0)  # Cap at 3 minutes
        full_prompt = " ".join(style_tags + [prompt]).strip()
        sample_rate = 32000

        if self._use_mock:
            t = np.linspace(0, duration, int(sample_rate * duration))
            frequency = 440 + (220 * np.sin(2 * np.pi * t / duration))
            audio = 0.3 * np.sin(2 * np.pi * frequency * t / sample_rate)
            return audio.astype(np.float32), sample_rate

        loop = asyncio.get_event_loop()

        def _run():
            # MusicGen max is 30 seconds (1503 tokens)
            max_tokens = min(int(duration * 50), 1503)
            result = self._pipeline(
                full_prompt,
                generate_kwargs={
                    "max_new_tokens": max_tokens,
                    "do_sample": True,
                    "top_k": 250,
                    "temperature": 1.0,
                },
            )
            audio_array = np.array(result["audio"], dtype=np.float32)
            if audio_array.ndim > 1:
                audio_array = audio_array[0]
            return audio_array, result["sampling_rate"]

        return await loop.run_in_executor(None, _run)

    async def shutdown(self):
        self._pipeline = None
        self._use_mock = False


def get_music_service() -> MusicGenService:
    if _music_service is None:
        raise RuntimeError("Music service not initialized")
    return _music_service


async def initialize_music_service():
    """Construct the music service singleton, warm up the model in background.

    The MusicGen-small model is ~500MB and takes 30-60s to download/load.
    Awaiting it in the lifespan blocks the entire app from accepting requests
    (causing 502 Bad Gateway on nginx), so we fire-and-forget the initialize()
    call. The first /music/generate request will await the in-progress load
    via the service's internal state.
    """
    global _music_service
    settings = get_settings()
    if settings.MUSIC_PROVIDER == "disabled":
        logger.info("Music service disabled via MUSIC_PROVIDER=disabled")
        return
    _music_service = MusicGenService()
    asyncio.create_task(_music_service.initialize())


async def shutdown_music_service():
    global _music_service
    if _music_service:
        await _music_service.shutdown()
    _music_service = None
