from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = Field(default="VoiceAgent")
    APP_VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="development")

    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    WORKERS: int = Field(default=1)
    RELOAD: bool = Field(default=True)

    CORS_ORIGINS: List[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    CORS_ALLOW_METHODS: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    CORS_ALLOW_HEADERS: List[str] = Field(default=["Content-Type", "Authorization", "X-Request-ID"])

    STT_PROVIDER: str = Field(default="whisper")

    # Whisper-specific (local faster-whisper)
    # Options: tiny, base, small, medium, large-v3, distil-large-v3
    # distil-large-v3 is 6× faster than large-v3 at near-identical WER.
    WHISPER_MODEL: str = Field(default="small")
    WHISPER_DEVICE: str = Field(default="cpu")
    WHISPER_COMPUTE_TYPE: str = Field(default="int8")
    WHISPER_CPU_THREADS: int = Field(default=8)

    TTS_PROVIDER: str = Field(default="kokoro")

    # Kokoro-specific (local 82M ONNX, ultra-fast)
    KOKORO_VOICE: str = Field(default="af_heart")
    KOKORO_LANGUAGE: str = Field(default="en-us")
    KOKORO_SPEED: float = Field(default=1.0)
    KOKORO_MODEL_PATH: Optional[str] = Field(default=None)
    KOKORO_VOICES_PATH: Optional[str] = Field(default=None)

    # Pocket TTS-specific (Kyutai 100M-parameter local, voice cloning)
    # Language options: english, french, german, spanish, italian, portuguese
    POCKET_TTS_LANGUAGE: str = Field(default="english")
    POCKET_TTS_VOICE: str = Field(default="alba")


    MUSIC_PROVIDER: str = Field(default="ace_step")

    WS_HEARTBEAT_INTERVAL: int = Field(default=30)
    WS_MAX_MESSAGE_SIZE: int = Field(default=1048576)

    AUDIO_SAMPLE_RATE: int = Field(default=16000)
    AUDIO_CHANNELS: int = Field(default=1)
    AUDIO_STREAM_CHUNK_MS: int = Field(default=100)

    # Text chunking for TTS. Pocket TTS has a hard 50-token-per-chunk limit
    # (skips words past it). 50 tokens ≈ 150-200 chars depending on content
    # (markdown / code averages 2-3 chars/token vs 4-5 for prose). Picking
    # 180 here leaves headroom for unusual text without sacrificing too much
    # crossfade overhead. THRESHOLD = MAX so we always chunk for safety.
    TEXT_CHUNK_THRESHOLD: int = Field(default=180)   # Always chunk if text > 180 chars
    TEXT_MAX_CHUNK_SIZE: int = Field(default=180)    # Max chars per chunk
    AUDIO_CHUNK_THRESHOLD: int = Field(default=60)
    AUDIO_FILE_CHUNK_DURATION_MS: int = Field(default=30000)
    AUDIO_SILENCE_THRESH_DB: int = Field(default=-40)
    AUDIO_MIN_SILENCE_MS: int = Field(default=500)

    VAD_ENABLED: bool = Field(default=True)
    VAD_THRESHOLD: float = Field(default=0.5)
    VAD_MIN_SILENCE_DURATION_MS: int = Field(default=300)
    VAD_MIN_SPEECH_DURATION_MS: int = Field(default=200)

    LANGGRAPH_URL: Optional[str] = Field(default=None)

    # When empty, auth is disabled (development mode).
    API_KEY: Optional[str] = Field(default=None)
    MAX_WS_CONNECTIONS: int = Field(default=10)

    RATE_LIMIT_REQUESTS: int = Field(default=60)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60)

    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    DATABASE_URL: str = Field(default="postgresql://postgres@postgres:5432/voiceagent")
    DATABASE_AUTH_URL: str = Field(default="postgresql+asyncpg://postgres@postgres:5432/voiceagent_auth")
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=0)

    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    SECRET_KEY: str = Field(default="")  # REQUIRED in production, must be set via .env
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRATION_MINUTES: int = Field(default=30)  # 30 minutes for access token
    JWT_REFRESH_EXPIRATION_DAYS: int = Field(default=7)  # 7 days for refresh token

    PASSWORD_HASH_ALGORITHM: str = Field(default="bcrypt")
    PASSWORD_MIN_LENGTH: int = Field(default=8)

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        environment = info.data.get("ENVIRONMENT", "development")
        # In production, SECRET_KEY must be set and have minimum length
        if environment == "production":
            if not v or len(v) < 32:
                raise ValueError(
                    "SECRET_KEY must be set to a random string of at least 32 characters in production. "
                    "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
                )
        # In development, provide a default if not set
        elif not v:
            return "development-key-change-in-production"
        return v

    @field_validator("STT_PROVIDER")
    @classmethod
    def validate_stt_provider(cls, v: str) -> str:
        allowed = ["whisper"]
        if v not in allowed:
            raise ValueError(f"STT_PROVIDER must be one of {allowed}")
        return v

    @field_validator("TTS_PROVIDER")
    @classmethod
    def validate_tts_provider(cls, v: str) -> str:
        allowed = ["kokoro", "pocket_tts"]
        if v not in allowed:
            raise ValueError(f"TTS_PROVIDER must be one of {allowed}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v.upper()


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
