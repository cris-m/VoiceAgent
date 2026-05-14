import asyncio
from pathlib import Path
from typing import AsyncIterator, List, Optional

import numpy as np

from services.audio.base import AudioChunk
from services.tts.base import BaseTTS, Language, TTSConfig, TTSResult, Voice

DEFAULT_MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
DEFAULT_VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "voiceagent" / "kokoro"
DEFAULT_MODEL_FILENAME = "kokoro-v1.0.onnx"
DEFAULT_VOICES_FILENAME = "voices-v1.0.bin"


# Curated preset voices from Kokoro-82M. Full list has 50+ voices across
# American/British English, Japanese, Chinese, Korean, French, etc.
# Character-driven preview lines — 2 short sentences each, tuned to
# showcase the voice's actual texture and pace rather than just stating
# the name.
KOKORO_VOICES = [
    Voice(
        id="af_heart",
        name="Heart (F)",
        language="en-us",
        gender="female",
        description="Warm, expressive American",
        metadata={
            "preview_text": "I'm Heart. Warm, expressive, the voice for stories that should feel like a hand on your shoulder — close, present, never rushed."
        },
    ),
    Voice(
        id="af_bella",
        name="Bella (F)",
        language="en-us",
        gender="female",
        description="Bright, friendly American",
        metadata={
            "preview_text": "I'm Bella. Bright, friendly, a little sparkly — the voice of every brand that wants to feel like a person, not a billboard."
        },
    ),
    Voice(
        id="af_nicole",
        name="Nicole (F)",
        language="en-us",
        gender="female",
        description="Crisp, professional American",
        metadata={
            "preview_text": "I'm Nicole. Crisp and professional, the voice your training video has been waiting for — clear when it has to be, human when it counts."
        },
    ),
    Voice(
        id="af_sarah",
        name="Sarah (F)",
        language="en-us",
        gender="female",
        description="Natural, conversational American",
        metadata={
            "preview_text": "Hey, I'm Sarah. Natural, conversational, the kind of voice that turns a script into a chat over coffee — easy, real, and never overdone."
        },
    ),
    Voice(
        id="am_adam",
        name="Adam (M)",
        language="en-us",
        gender="male",
        description="Confident American",
        metadata={
            "preview_text": "I'm Adam. Confident, direct, no wasted breath — when the line needs weight without theatrics, that's where I work best."
        },
    ),
    Voice(
        id="am_michael",
        name="Michael (M)",
        language="en-us",
        gender="male",
        description="Neutral, broadcast American",
        metadata={
            "preview_text": "Michael here. Clean, neutral, broadcast-ready — when the words have to do the work and the voice has to get out of the way, that's me."
        },
    ),
    Voice(
        id="bf_emma",
        name="Emma (F, UK)",
        language="en-gb",
        gender="female",
        description="Refined British",
        metadata={
            "preview_text": "I'm Emma. A British voice with a little warmth in the vowels — proper without being prim, polished without being cold."
        },
    ),
    Voice(
        id="bm_george",
        name="George (M, UK)",
        language="en-gb",
        gender="male",
        description="Distinguished British",
        metadata={
            "preview_text": "George here. There's a bit of an old library in my voice — measured, careful with every word, and quite at home reading you something worth listening to."
        },
    ),
]

# Note: Kokoro-82M ships with 50+ voices across ja/zh/ko/fr/etc., but the
# espeak-ng phonemizer in the runtime image only supports en-us / en-gb out of
# the box. Adding non-English voices here without installing the matching
# espeak language packs would crash synthesis with "language X is not supported
# by the espeak backend". Add a voice + language only after confirming the
# espeak-ng-data-<lang> package is present in nginx/Dockerfile.
KOKORO_LANGUAGES = [
    Language(code="en-us", name="English (US)", native_name="English"),
    Language(code="en-gb", name="English (UK)", native_name="English"),
]


class KokoroTTS(BaseTTS):
    @property
    def supports_voice_cloning(self) -> bool:
        return False

    @property
    def supports_speed(self) -> bool:
        return True

    @property
    def supports_language(self) -> bool:
        return True

    def __init__(
        self,
        model_path: Optional[str] = None,
        voices_path: Optional[str] = None,
        default_voice: str = "af_heart",
        default_language: str = "en-us",
        speed: float = 1.0,
        config: Optional[TTSConfig] = None,
    ) -> None:
        super().__init__("kokoro_tts", config)
        self._model_path = model_path or str(DEFAULT_CACHE_DIR / DEFAULT_MODEL_FILENAME)
        self._voices_path = voices_path or str(DEFAULT_CACHE_DIR / DEFAULT_VOICES_FILENAME)
        self._default_voice = default_voice
        self._default_language = default_language
        self._speed = speed
        self._kokoro = None
        self.config.voice = default_voice

    async def initialize(self) -> None:
        # Idempotent — see services/tts/pocket_tts.py for the same pattern.
        if self._kokoro is not None:
            return

        try:
            from kokoro_onnx import Kokoro  # type: ignore
        except ImportError:
            raise RuntimeError(
                "kokoro-onnx package not installed. Add to pyproject.toml:\n    kokoro-onnx>=0.4.0\nThen run: uv sync"
            )

        await self._ensure_model_files()

        loop = asyncio.get_running_loop()
        self.logger.info(
            f"Loading Kokoro-82M ONNX from {self._model_path} "
            f"(voice={self._default_voice}, lang={self._default_language})"
        )

        self._kokoro = await loop.run_in_executor(
            None,
            lambda: Kokoro(self._model_path, self._voices_path),
        )
        self.logger.info(f"Kokoro-82M ready with {len(KOKORO_VOICES)} preset voices")

    async def _ensure_model_files(self) -> None:
        DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        model_file = Path(self._model_path)
        voices_file = Path(self._voices_path)

        if model_file.exists() and voices_file.exists():
            return

        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx required to download Kokoro model files")

        async def download(url: str, dest: Path) -> None:
            self.logger.info(f"Downloading Kokoro model file: {url}")
            async with httpx.AsyncClient(follow_redirects=True, timeout=300.0) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    with open(dest, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                            f.write(chunk)
            self.logger.info(f"Saved to {dest} ({dest.stat().st_size // (1024 * 1024)} MB)")

        if not model_file.exists():
            await download(DEFAULT_MODEL_URL, model_file)
        if not voices_file.exists():
            await download(DEFAULT_VOICES_URL, voices_file)

    async def shutdown(self) -> None:
        self._kokoro = None
        self.logger.info("Kokoro-82M unloaded")

    async def health_check(self) -> bool:
        return self._kokoro is not None

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs,
    ) -> TTSResult:
        if self._kokoro is None:
            raise RuntimeError("Kokoro not initialized")
        if not text or not text.strip():
            raise ValueError("Empty text provided to synthesize()")

        voice_id = voice or self._default_voice
        # Guard against cross-provider stale IDs (e.g. a Pocket TTS voice like
        # "alba" left in user config after switching to Kokoro). Fall back to
        # the configured default rather than passing an unknown ID to the
        # underlying engine — the kokoro-onnx behavior on unknown voices isn't
        # documented and the failure mode (silent garbage audio vs error) varies.
        valid_ids = {v.id for v in KOKORO_VOICES}
        if voice_id not in valid_ids:
            self.logger.warning(
                f"Unknown Kokoro voice '{voice_id}' (likely stale config); "
                f"falling back to default '{self._default_voice}'"
            )
            voice_id = self._default_voice
        language = kwargs.get("lang") or kwargs.get("language") or self._default_language
        speed = float(kwargs.get("speed") or self._speed)

        loop = asyncio.get_running_loop()

        def _synthesize():
            try:
                samples, sample_rate = self._kokoro.create(
                    text=text,
                    voice=voice_id,
                    speed=speed,
                    lang=language,
                )
                # Newer kokoro-onnx returns a numpy array; older returns a list.
                # `not samples` on a numpy array raises ambiguous-truth error, so
                # handle both shapes explicitly.
                if samples is None or len(samples) == 0:
                    raise ValueError(f"Kokoro returned empty audio for: {text[:50]}")
                return np.asarray(samples, dtype=np.float32), int(sample_rate)
            except Exception as e:
                self.logger.error(f"Kokoro ONNX inference failed: {e}")
                raise

        try:
            samples, sample_rate = await loop.run_in_executor(None, _synthesize)
        except Exception as e:
            self.logger.error(f"Kokoro synthesis failed for '{text[:50]}': {e}")
            raise
        duration = len(samples) / sample_rate

        self.logger.debug(f"[Kokoro] synth '{text[:50]}...' → {duration:.2f}s audio @{sample_rate}Hz, voice={voice_id}")

        return TTSResult(
            audio=samples,
            sample_rate=sample_rate,
            duration=duration,
            text=text,
            voice=voice_id,
            metadata={"provider": "kokoro", "language": language, "speed": speed},
        )

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[AudioChunk]:
        """Stream audio chunks.

        Kokoro-onnx generates in one shot (no native token-level streaming),
        but because inference is fast (~300ms for a sentence), we synthesize
        the full clip and yield it in ~100ms chunks for smooth playback.
        """
        result = await self.synthesize(text, voice=voice, **kwargs)
        chunk_samples = max(1, int(result.sample_rate * 0.1))  # 100ms chunks

        for i in range(0, len(result.audio), chunk_samples):
            chunk_data = result.audio[i : i + chunk_samples]
            yield AudioChunk(
                data=chunk_data,
                sample_rate=result.sample_rate,
                metadata={"voice": result.voice, "text": text},
            )

    async def get_voices(self) -> List[Voice]:
        return list(KOKORO_VOICES)

    async def get_languages(self) -> List[Language]:
        return list(KOKORO_LANGUAGES)
