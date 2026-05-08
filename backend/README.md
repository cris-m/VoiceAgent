# Backend

FastAPI service. Owns the voice WebSocket pipeline, the audio HTTP routes (narrate, transcribe, voice clone, music), JWT auth, and file storage.

For overall architecture see [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md). For full-stack setup see the [project README](../README.md).

## Routes

| Path | Method | Purpose |
|---|---|---|
| `/api/v1/health` | GET | Liveness probe. |
| `/api/v1/ready` | GET | Readiness probe. |
| `/api/v1/voice/ws` | WS | Real-time voice pipeline (STT, agent, TTS). |
| `/api/v1/voice/voices` | GET | Voice catalog merged with cloned voices. |
| `/api/v1/voice/languages` | GET | Languages supported by the active TTS provider. |
| `/api/v1/voice/config` | GET / PUT | Read or update active voice settings and capabilities. |
| `/api/v1/voice/status` | GET | Pipeline status for the orb UI. |
| `/api/v1/voice/interrupt` | POST | Request a barge-in. |
| `/api/v1/voice/narrate` | POST | Synthesize text to a saved audio file. |
| `/api/v1/voice/narrations` | GET | List a user's narrations. |
| `/api/v1/voice/narrations/{id}` | DELETE | Delete a narration. |
| `/api/v1/voice/transcribe` | POST (multipart) | Transcribe an uploaded audio file. |
| `/api/v1/voice/clone` | POST (multipart) | Clone a voice from reference audio (Pocket TTS only). |
| `/api/v1/voice/clones` | GET | List cloned voices. |
| `/api/v1/voice/clones/{id}` | DELETE | Delete a cloned voice. |
| `/api/v1/music/list` | GET | User's generated music. |
| `/api/v1/music/generate` | POST | Generate music from a prompt. |
| `/api/v1/music/{id}` | DELETE | Delete a track. |
| `/api/v1/auth/register` | POST | Create a user. |
| `/api/v1/auth/login` | POST | Get an access token plus a refresh cookie. |
| `/api/v1/auth/me` | GET | Current user info. |
| `/api/v1/auth/refresh` | POST | Refresh an expired access token. |
| `/api/v1/auth/logout` | POST | Revoke the current token. |
| `/api/v1/agent/...` | various | LangGraph thread CRUD passthrough. |
| `/api/v1/personality/...` | various | Personality preset CRUD. |

OpenAPI is at `/docs` when `ENVIRONMENT=development`.

## Configuration

Full reference in [`.env.example`](.env.example). Highlights:

| Variable | Default | Notes |
|---|---|---|
| `STT_PROVIDER` | `whisper` | Only `whisper` is wired today. |
| `WHISPER_MODEL` | `distil-large-v3` | `tiny`, `base`, `small`, `medium`, `large-v3`, `distil-large-v3`. |
| `TTS_PROVIDER` | `kokoro` | `kokoro` (8 voices, supports speed/language) or `pocket_tts` (27 voices, supports cloning). |
| `MUSIC_PROVIDER` | `ace_step` | `ace_step` or `disabled`. |
| `HF_TOKEN` | empty | Required only for Pocket TTS voice cloning. |
| `SECRET_KEY` | dev placeholder | Set in production (32+ random chars). |
| `API_KEY` | empty | If set, every API call needs `Authorization: Bearer <key>`. |
| `CORS_ORIGINS` | localhost variants | Add your production domain here. |

## Code layout

```
backend/
├── api/
│   ├── dependency/        Auth, rate limiter, security middleware
│   └── routes/v1/
│       ├── voice.py       WS handler + narrate, transcribe, clone routes
│       ├── auth.py        Register, login, refresh, logout
│       ├── agent.py       LangGraph thread CRUD passthrough
│       ├── music.py
│       ├── personality.py
│       └── server.py      Health and readiness
├── services/
│   ├── voice_pipeline.py  Orchestrates STT, TTS, VAD; per-connection factory
│   ├── stt/whisper.py     faster-whisper wrapper
│   ├── stt/audio_chunker.py
│   ├── tts/kokoro.py      Kokoro 82M ONNX
│   ├── tts/pocket_tts.py  Kyutai Pocket TTS
│   ├── tts/text_chunker.py
│   ├── tts/base.py        Capability flags interface
│   ├── vad/silero.py      Silero VAD with hysteresis state machine
│   ├── audio/aec.py       Boolean "is TTS playing" flag
│   ├── agent/client.py    LangGraph SDK wrapper
│   ├── auth.py            JWT issuance and verification
│   ├── token_blacklist.py Redis-backed revocation
│   └── music/ace_step.py  MusicGen-small via transformers
├── core/                  rate limiter, error envelope normalizer
├── config/
│   ├── settings.py        pydantic-settings
│   ├── database.py        async SQLAlchemy session
│   └── redis.py
├── models/                SQLAlchemy ORM
├── schemas/               Pydantic request/response shapes
├── alembic/               Migrations
├── utils/                 logging, file storage, TTS sanitizer
├── tests/                 18 test files, 265 passing
├── main.py                FastAPI app factory + lifespan
└── pyproject.toml
```

## Tests

Inside the dev stack:

```bash
docker exec voiceagent-backend-dev pytest
```

Without Docker:

```bash
cd backend
uv sync --extra dev
uv run pytest tests/ -v
```

The suite hits no network and loads no real models. Whisper, Kokoro, Pocket TTS, and the LangGraph SDK are mocked. Postgres is replaced with in-memory SQLite, Redis with a stateful AsyncMock. Full run completes in about 16 seconds.

## During development

```bash
# Tail logs
docker compose -f ../docker-compose.dev.yml logs -f backend

# Filter for the signals that matter most when tuning latency
docker compose -f ../docker-compose.dev.yml logs backend | grep -E "Latency|Barge-in|Transcript"

# uvicorn --reload picks up code changes automatically.
# If you change backend/.env, recreate the container so env_file is reread:
docker compose -f ../docker-compose.dev.yml up -d backend
```

## Database migrations

Alembic is wired up. New schema changes:

```bash
cd backend
uv run alembic revision --autogenerate -m "add new column"
uv run alembic upgrade head
```

The dev stack's Postgres volume is `voiceagent-postgres-data-dev`. To start fresh, stop the stack and `docker volume rm voiceagent-postgres-data-dev`.
