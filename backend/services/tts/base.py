import json
from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional

import numpy as np

from services.audio.base import AudioChunk, AudioConfig
from services.base import BaseService


@dataclass
class Language:
    code: str
    name: str
    native_name: Optional[str] = None


@dataclass
class Voice:
    id: str
    name: str
    language: str = "en-us"
    gender: Optional[str] = None
    description: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TTSConfig:
    voice: Optional[str] = None
    language: str = "en-us"
    speed: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    audio: AudioConfig = field(default_factory=AudioConfig)


@dataclass
class TTSResult:
    audio: np.ndarray
    sample_rate: int
    duration: float
    text: str
    voice: str
    metadata: dict = field(default_factory=dict)

    def to_chunk(self) -> AudioChunk:
        return AudioChunk(
            data=self.audio,
            sample_rate=self.sample_rate,
            metadata={"text": self.text, "voice": self.voice, **self.metadata},
        )


class VoiceCloningMixin:
    CLONED_VOICES_DIR = Path.home() / ".cache" / "voiceagent" / "cloned_voices"

    def _get_clones_dir(self) -> Path:
        self.CLONED_VOICES_DIR.mkdir(parents=True, exist_ok=True)
        return self.CLONED_VOICES_DIR

    def _load_cloned_voices_metadata(self) -> Dict[str, Voice]:
        clones_dir = self._get_clones_dir()
        metadata_file = clones_dir / "voices.json"

        if not metadata_file.exists():
            return {}

        with open(metadata_file, "r") as f:
            data = json.load(f)

        return {
            voice_id: Voice(
                id=voice_id,
                name=v.get("name", voice_id),
                language=v.get("language", "auto"),
                gender=v.get("gender"),
                description=v.get("description"),
                metadata=v.get("metadata", {"is_cloned": True}),
            )
            for voice_id, v in data.items()
        }

    def _save_cloned_voice_metadata(self, voice: Voice) -> None:
        clones_dir = self._get_clones_dir()
        metadata_file = clones_dir / "voices.json"

        existing: Dict = {}
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                existing = json.load(f)

        existing[voice.id] = {
            "name": voice.name,
            "language": voice.language,
            "gender": voice.gender,
            "description": voice.description,
            "metadata": voice.metadata or {"is_cloned": True},
        }

        with open(metadata_file, "w") as f:
            json.dump(existing, f, indent=2)

    def _delete_cloned_voice_metadata(self, voice_id: str) -> bool:
        clones_dir = self._get_clones_dir()
        metadata_file = clones_dir / "voices.json"

        if not metadata_file.exists():
            return False

        with open(metadata_file, "r") as f:
            existing = json.load(f)

        if voice_id not in existing:
            return False

        del existing[voice_id]

        with open(metadata_file, "w") as f:
            json.dump(existing, f, indent=2)

        return True


class BaseTTS(BaseService):
    def __init__(self, name: str, config: Optional[TTSConfig] = None):
        super().__init__(name)
        self.config = config or TTSConfig()
        self._voices: List[Voice] = []

    @property
    def supports_voice_cloning(self) -> bool:
        return False

    @property
    def supports_speed(self) -> bool:
        return False

    @property
    def supports_language(self) -> bool:
        return False

    @property
    def default_voice(self) -> Optional[str]:
        return self.config.voice

    @default_voice.setter
    def default_voice(self, voice_id: str) -> None:
        self.config.voice = voice_id

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs,
    ) -> TTSResult:
        pass

    @abstractmethod
    async def synthesize_stream(
        self,
        text: str,
        voice: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[AudioChunk]:
        pass

    @abstractmethod
    async def get_voices(self) -> List[Voice]:
        pass

    @abstractmethod
    async def get_languages(self) -> List[Language]:
        pass

    async def get_voice(self, voice_id: str) -> Optional[Voice]:
        voices = await self.get_voices()
        return next((v for v in voices if v.id == voice_id), None)

    def _resolve_voice(self, voice: Optional[str]) -> str:
        resolved = voice or self.default_voice
        if not resolved:
            raise ValueError("No voice specified and no default voice set")
        return resolved
