import asyncio
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

import numpy as np

from services.audio.base import AudioChunk
from services.tts.base import BaseTTS, Language, TTSConfig, TTSResult, Voice, VoiceCloningMixin

POCKET_VOICES = [
    Voice(
        id="alba",
        name="Alba (F)",
        language="en",
        gender="female",
        description="Warm, conversational English",
        metadata={
            "preview_text": "Hey, I'm Alba. I tell stories the way a good friend does — slow enough to land, lively enough to pull you in."
        },
    ),
    Voice(
        id="anna",
        name="Anna (F)",
        language="en",
        gender="female",
        description="Clear, articulate English",
        metadata={
            "preview_text": "Hi, I'm Anna. Crisp, clear, and easy to follow — the kind of voice that turns a complicated idea into something you actually remember."
        },
    ),
    Voice(
        id="azelma",
        name="Azelma (F)",
        language="en",
        gender="female",
        description="Expressive, theatrical English",
        metadata={
            "preview_text": "I'm Azelma — and I never let a sentence land the same way twice. If your script needs feeling, drama, a little fire, that's where I shine."
        },
    ),
    Voice(
        id="bill_boerst",
        name="Bill (M)",
        language="en",
        gender="male",
        description="Steady, trustworthy English",
        metadata={
            "preview_text": "I'm Bill. Steady, grounded, and the kind of narrator who makes a long audiobook feel like a Sunday drive — easy, unhurried, dependable."
        },
    ),
    Voice(
        id="caro_davy",
        name="Caro (F)",
        language="en",
        gender="female",
        description="Bright, friendly English",
        metadata={
            "preview_text": "I'm Caro. Bright, friendly, a little curious about everything — perfect for explainers, podcasts, or anything that should feel approachable."
        },
    ),
    Voice(
        id="charles",
        name="Charles (M)",
        language="en",
        gender="male",
        description="Refined British English",
        metadata={
            "preview_text": "Charles here. There's a bit of London in every syllable — refined, considered, and quite at home reading you the news, a novel, or a particularly elegant footnote."
        },
    ),
    Voice(
        id="cosette",
        name="Cosette (F)",
        language="en",
        gender="female",
        description="Light, casual English",
        metadata={
            "preview_text": "Hey, I'm Cosette. Casual, light on its feet — like texting your friend, but out loud."
        },
    ),
    Voice(
        id="eponine",
        name="Eponine (F)",
        language="en",
        gender="female",
        description="Soft, melancholic English",
        metadata={
            "preview_text": "I'm Eponine. Soft-spoken, a little wistful — the voice you reach for when the story has weight and you want every word to feel it."
        },
    ),
    Voice(
        id="eve",
        name="Eve (F)",
        language="en",
        gender="female",
        description="Calm, measured English",
        metadata={
            "preview_text": "I'm Eve. Calm, measured, never in a hurry — the kind of voice that makes meditation apps work and bedtime stories actually do their job."
        },
    ),
    Voice(
        id="fantine",
        name="Fantine (F)",
        language="en",
        gender="female",
        description="Earnest, emotional English",
        metadata={
            "preview_text": "Fantine speaking. I bring honesty — the kind of voice that doesn't perform, it just tells the truth and lets you sit with it."
        },
    ),
    Voice(
        id="george",
        name="George (M)",
        language="en",
        gender="male",
        description="Confident, polished English",
        metadata={
            "preview_text": "I'm George. Confident, well-paced, polished without being plastic — you'll hear me on a corporate explainer, and you won't reach for the skip button."
        },
    ),
    Voice(
        id="jane",
        name="Jane (F)",
        language="en",
        gender="female",
        description="Crisp, professional English",
        metadata={
            "preview_text": "I'm Jane. Crisp, professional, the kind of voice that makes a tutorial sound like advice from someone who's done it a thousand times."
        },
    ),
    Voice(
        id="javert",
        name="Javert (M)",
        language="en",
        gender="male",
        description="Stern, commanding English",
        metadata={
            "preview_text": "Javert. I read with weight and certainty — when a script demands authority, gravity, the gravelly assurance of a man who never wavers, that's me."
        },
    ),
    Voice(
        id="jean",
        name="Jean (M)",
        language="en",
        gender="male",
        description="Warm, fatherly English",
        metadata={
            "preview_text": "I'm Jean. Warm, weathered, a little like the uncle who knows how every story ends but tells it anyway because the telling is the point."
        },
    ),
    Voice(
        id="marius",
        name="Marius (M)",
        language="en",
        gender="male",
        description="Earnest, youthful English",
        metadata={
            "preview_text": "Marius — earnest, a touch romantic, and very good at meaning what I say. If your line needs heart, hand it to me."
        },
    ),
    Voice(
        id="mary",
        name="Mary (F)",
        language="en",
        gender="female",
        description="Gentle, classic English",
        metadata={
            "preview_text": "I'm Mary. Gentle, classic, the voice you hear on the audiobooks your grandmother kept on her nightstand — patient, lovely, never rushed."
        },
    ),
    Voice(
        id="michael",
        name="Michael (M)",
        language="en",
        gender="male",
        description="Neutral, broadcast English",
        metadata={
            "preview_text": "Michael here. Clean, neutral, broadcast-ready — when the words have to do the work and the voice has to get out of the way, that's me."
        },
    ),
    Voice(
        id="paul",
        name="Paul (M)",
        language="en",
        gender="male",
        description="Easy-going, conversational",
        metadata={
            "preview_text": "Hey, I'm Paul. Easy-going, conversational — the voice you'd cast for a coffee-shop advertisement or a podcast that should feel like a conversation."
        },
    ),
    Voice(
        id="peter_yearsley",
        name="Peter (M)",
        language="en",
        gender="male",
        description="Cultured, literary English",
        metadata={
            "preview_text": "I'm Peter. There's a library in my voice — slow turns of phrase, careful emphasis, the patience of a man who would rather be understood than be quick."
        },
    ),
    Voice(
        id="stuart_bell",
        name="Stuart (M)",
        language="en",
        gender="male",
        description="Wry, dry English",
        metadata={
            "preview_text": "Stuart, here. Dry, a touch wry, the kind of delivery that lands a punchline without ever announcing it."
        },
    ),
    Voice(
        id="vera",
        name="Vera (F)",
        language="en",
        gender="female",
        description="Bold, declarative English",
        metadata={
            "preview_text": "I'm Vera. Bold, declarative, a voice that fills the room when it needs to. If your line is meant to be heard, I'll make sure of it."
        },
    ),
    Voice(
        id="estelle",
        name="Estelle (F, FR)",
        language="fr",
        gender="female",
        description="Élégante, française",
        metadata={
            "preview_text": "Je suis Estelle. Une voix française, posée et élégante — celle d'un soir de pluie à Paris, d'un livre qu'on lit à voix basse."
        },
    ),
    Voice(
        id="giovanni",
        name="Giovanni (M, IT)",
        language="it",
        gender="male",
        description="Caloroso, italiano",
        metadata={
            "preview_text": "Sono Giovanni. Una voce italiana, calda e piena di musica — fatta per le storie che meritano di essere raccontate piano."
        },
    ),
    Voice(
        id="juergen",
        name="Jürgen (M, DE)",
        language="de",
        gender="male",
        description="Klar, deutsch",
        metadata={
            "preview_text": "Ich bin Jürgen. Klar, präzise, und doch nicht steif — eine deutsche Stimme, die erklärt und dabei nicht belehrt."
        },
    ),
    Voice(
        id="lola",
        name="Lola (F, ES)",
        language="es",
        gender="female",
        description="Cálida, española",
        metadata={
            "preview_text": "Soy Lola. Una voz española con luz y calidez — para las historias que se sienten como un café en una tarde sin prisa."
        },
    ),
    Voice(
        id="rafael",
        name="Rafael (M, PT)",
        language="pt",
        gender="male",
        description="Tranquilo, português",
        metadata={
            "preview_text": "Eu sou o Rafael. Uma voz portuguesa, calma e clara — feita para as histórias que se contam devagar, sem pressa."
        },
    ),
]

POCKET_LANGUAGES = [
    Language(code="en", name="English", native_name="English"),
    Language(code="fr", name="French", native_name="Français"),
    Language(code="de", name="German", native_name="Deutsch"),
    Language(code="es", name="Spanish", native_name="Español"),
    Language(code="it", name="Italian", native_name="Italiano"),
    Language(code="pt", name="Portuguese", native_name="Português"),
]


class PocketTTS(BaseTTS, VoiceCloningMixin):
    """Kyutai Pocket TTS — 100M-parameter local TTS with voice cloning."""

    @property
    def supports_voice_cloning(self) -> bool:
        return True

    def __init__(
        self,
        language: str = "english",
        default_voice: str = "alba",
        config: Optional[TTSConfig] = None,
    ) -> None:
        super().__init__("pocket_tts", config)
        self._language = language
        self._default_voice = default_voice
        self._model = None
        # Voice states (KV-cache embeddings) keyed by voice_id — expensive to recompute.
        self._voice_states: Dict[str, object] = {}
        self.config.voice = default_voice

    async def initialize(self) -> None:
        # Idempotent: this provider may be shared across per-connection
        # pipelines (see voice_pipeline.create_voice_pipeline_for_connection).
        # Without this guard, each connection's pipeline.initialize() would
        # reload the ~2GB model.
        if self._model is not None:
            return

        try:
            from pocket_tts import TTSModel  # type: ignore
        except ImportError:
            raise RuntimeError("pocket-tts package not installed. Run:\n    uv add pocket-tts")

        loop = asyncio.get_running_loop()
        self.logger.info(f"Loading Pocket TTS model (language={self._language})...")
        self._model = await loop.run_in_executor(
            None,
            lambda: TTSModel.load_model(language=self._language),
        )
        # Pre-load the default voice so the first request has no extra latency.
        await self._get_voice_state(self._default_voice)

        # Warm-up: synthesize a short phrase so the first user turn doesn't
        # pay the cold-start cost (kernel/JIT warmup, KV-cache allocation).
        try:
            await self.synthesize("ok", voice=self._default_voice)
            self.logger.info("Pocket TTS warm-up complete")
        except Exception as e:
            self.logger.warning(f"Pocket TTS warm-up failed (non-fatal): {e}")

        self.logger.info(
            f"Pocket TTS ready — sample_rate={self._model.sample_rate}Hz, default_voice={self._default_voice}"
        )

    async def shutdown(self) -> None:
        self._model = None
        self._voice_states.clear()
        self.logger.info("Pocket TTS unloaded")

    async def health_check(self) -> bool:
        return self._model is not None

    async def _get_voice_state(self, voice_id: str) -> object:
        """Return cached voice state, computing it on first access.

        If `voice_id` isn't a Pocket TTS catalog voice (e.g. a leftover Kokoro
        ID like `af_heart` from a prior session), fall back to the default voice
        instead of triggering Pocket TTS's voice-cloning path — which fails
        without HF auth and accepting the kyutai/pocket-tts terms.
        """
        if voice_id not in self._voice_states:
            if self._model is None:
                raise RuntimeError("Pocket TTS not initialized")

            # Validate against the catalog. Unknown IDs would otherwise be
            # interpreted as voice-clone audio prompts.
            from pocket_tts.models.tts_model import _ORIGINS_OF_PREDEFINED_VOICES

            if voice_id not in _ORIGINS_OF_PREDEFINED_VOICES:
                self.logger.warning(
                    f"Unknown Pocket TTS voice '{voice_id}' (likely stale config); "
                    f"falling back to default '{self._default_voice}'"
                )
                voice_id = self._default_voice

            if voice_id in self._voice_states:
                return self._voice_states[voice_id]

            loop = asyncio.get_running_loop()
            self._voice_states[voice_id] = await loop.run_in_executor(
                None,
                lambda: self._model.get_state_for_audio_prompt(voice_id),
            )
        return self._voice_states[voice_id]

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs,
    ) -> TTSResult:
        if self._model is None:
            raise RuntimeError("Pocket TTS not initialized")
        if not text or not text.strip():
            raise ValueError("Empty text provided to synthesize()")

        voice_id = voice or self._default_voice
        voice_state = await self._get_voice_state(voice_id)
        loop = asyncio.get_running_loop()

        def _synth():
            audio_tensor = self._model.generate_audio(voice_state, text)
            return audio_tensor.numpy().astype(np.float32)

        try:
            samples = await loop.run_in_executor(None, _synth)
        except Exception as e:
            self.logger.error(f"Pocket TTS synthesis failed for '{text[:50]}': {e}")
            raise

        sr = self._model.sample_rate
        duration = len(samples) / sr
        self.logger.debug(f"[PocketTTS] synth '{text[:50]}' → {duration:.2f}s @{sr}Hz voice={voice_id}")
        return TTSResult(
            audio=samples,
            sample_rate=sr,
            duration=duration,
            text=text,
            voice=voice_id,
            metadata={"provider": "pocket_tts"},
        )

    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[AudioChunk]:
        """Truly streaming synthesis — yields audio chunks as they are generated.

        Pocket TTS's generate_audio_stream() is a synchronous generator, so we
        run it in a thread and bridge chunks into this async generator via a
        Queue.  run_coroutine_threadsafe(queue.put(...)).result() gives us
        thread-safe enqueue with implicit backpressure (put blocks thread until
        the coroutine completes, preventing unbounded memory growth).
        """
        if self._model is None:
            raise RuntimeError("Pocket TTS not initialized")
        if not text or not text.strip():
            raise ValueError("Empty text provided to synthesize_stream()")

        voice_id = voice or self._default_voice
        voice_state = await self._get_voice_state(voice_id)
        sr = self._model.sample_rate
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def _produce() -> None:
            try:
                for chunk_tensor in self._model.generate_audio_stream(voice_state, text):
                    chunk_np = chunk_tensor.numpy().astype(np.float32)
                    asyncio.run_coroutine_threadsafe(queue.put(chunk_np), loop).result()
            except Exception as exc:
                asyncio.run_coroutine_threadsafe(queue.put(exc), loop).result()
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

        producer = loop.run_in_executor(None, _produce)
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield AudioChunk(
                    data=item,
                    sample_rate=sr,
                    metadata={"voice": voice_id, "text": text},
                )
        finally:
            await producer

    async def get_voices(self) -> List[Voice]:
        return list(POCKET_VOICES)

    async def get_languages(self) -> List[Language]:
        return list(POCKET_LANGUAGES)

    async def clone_voice(
        self,
        audio_path: str,
        name: str,
        language: str = "auto",
        description: Optional[str] = None,
    ) -> Voice:
        """Clone a voice from a WAV/MP3 file by computing its KV-cache embedding."""
        if self._model is None:
            raise RuntimeError("Pocket TTS not initialized")

        import hashlib

        voice_id = f"clone_{hashlib.sha1(name.encode()).hexdigest()[:8]}"

        loop = asyncio.get_running_loop()
        voice_state = await loop.run_in_executor(
            None,
            lambda: self._model.get_state_for_audio_prompt(audio_path),
        )
        self._voice_states[voice_id] = voice_state

        # Persist as safetensors for fast future reloads (skips audio processing).
        clones_dir = self._get_clones_dir()
        safetensors_path = clones_dir / f"{voice_id}.safetensors"
        try:
            from pocket_tts import export_model_state  # type: ignore

            await loop.run_in_executor(
                None,
                lambda: export_model_state(voice_state, str(safetensors_path)),
            )
        except Exception as e:
            self.logger.warning(f"Could not export voice state to safetensors: {e}")

        voice = Voice(
            id=voice_id,
            name=name,
            language=language,
            description=description or f"Cloned from audio: {name}",
            metadata={"is_cloned": True, "safetensors": str(safetensors_path)},
        )
        self._save_cloned_voice_metadata(voice)
        self.logger.info(f"Cloned voice '{name}' → {voice_id}")
        return voice

    async def get_cloned_voices(self) -> List[Voice]:
        voices_meta = self._load_cloned_voices_metadata()
        result = []
        loop = asyncio.get_running_loop()
        for voice_id, voice in voices_meta.items():
            safetensors = voice.metadata.get("safetensors", "")
            if safetensors and Path(safetensors).exists() and voice_id not in self._voice_states:
                try:
                    self._voice_states[voice_id] = await loop.run_in_executor(
                        None,
                        lambda p=safetensors: self._model.get_state_for_audio_prompt(p),
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to reload cloned voice {voice_id}: {e}")
                    continue
            result.append(voice)
        return result

    async def delete_cloned_voice(self, clone_id: str) -> bool:
        self._voice_states.pop(clone_id, None)
        safetensors_path = self._get_clones_dir() / f"{clone_id}.safetensors"
        if safetensors_path.exists():
            safetensors_path.unlink()
        return self._delete_cloned_voice_metadata(clone_id)
