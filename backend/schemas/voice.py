from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class VoiceConfig(BaseModel):
    voice_id: str = Field(default="default")
    language: str = Field(default="en-us")
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    stt_model: str = Field(default="base")


class VoiceConfigUpdate(BaseModel):
    voice_id: Optional[str] = None
    language: Optional[str] = None
    speed: Optional[float] = Field(default=None, ge=0.5, le=2.0)


class VoiceStatusResponse(BaseModel):
    status: AgentStatus
    is_connected: bool = False
    active_connections: int = 0
    stt_ready: bool = False
    tts_ready: bool = False
    llm_ready: bool = False
    config: VoiceConfig


class VoiceInfo(BaseModel):
    id: str
    name: str
    language: str
    gender: Optional[str] = None
    description: Optional[str] = None
    style: Optional[str] = None
    tags: Optional[List[str]] = None
    preview_text: Optional[str] = None


class LanguageInfo(BaseModel):
    code: str
    name: str
    native_name: Optional[str] = None


class VoicesResponse(BaseModel):
    voices: List[VoiceInfo]
    default_voice: str


class LanguagesResponse(BaseModel):
    languages: List[LanguageInfo]
    default_language: str


class TranscriptionResponse(BaseModel):
    text: str
    language: Optional[str] = None
    duration_seconds: float


class NarrationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    voice_id: Optional[str] = None
    speed: Optional[float] = Field(default=None, ge=0.5, le=2.0)
    language: Optional[str] = "auto"


class VoiceCloneResponse(BaseModel):
    id: str
    name: str
    language: str
    description: Optional[str] = None
    is_cloned: bool = True
    message: str


class ClonedVoicesResponse(BaseModel):
    voices: List[VoiceInfo]
    count: int
