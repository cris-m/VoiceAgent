from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

patcher_rate_limiter = patch("api.dependency.rate_limiter.is_allowed", new=AsyncMock(return_value=True))
patcher_rate_limiter.start()

mock_redis = AsyncMock()
_redis_store: set = set()


async def _redis_setex(key, ttl, value):
    _redis_store.add(str(key))
    return True


async def _redis_exists(key):
    return 1 if str(key) in _redis_store else 0


async def _redis_sadd(key, *members):
    for m in members:
        _redis_store.add(str(m))
    return len(members)


async def _redis_delete(*keys):
    removed = 0
    for k in keys:
        if str(k) in _redis_store:
            _redis_store.discard(str(k))
            removed += 1
    return removed


mock_redis.setex = AsyncMock(side_effect=_redis_setex)
mock_redis.sadd = AsyncMock(side_effect=_redis_sadd)
mock_redis.exists = AsyncMock(side_effect=_redis_exists)
mock_redis.delete = AsyncMock(side_effect=_redis_delete)
mock_redis.keys = AsyncMock(return_value=[])
mock_redis.scard = AsyncMock(return_value=0)

patcher_get_redis = patch("config.redis.get_redis")
patcher_close_redis = patch("config.redis.close_redis")

mock_get_redis = patcher_get_redis.start()
mock_close_redis = patcher_close_redis.start()


async def async_return_redis():
    return mock_redis


mock_get_redis.side_effect = async_return_redis
mock_close_redis.return_value = None

from config.database import get_db
from main import app
from models.user import Base


@pytest.fixture
async def test_db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine):
    SessionLocal = async_sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield SessionLocal
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(test_db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_user():
    return {
        "username": f"testuser_{uuid4().hex[:6]}",
        "email": f"test_{uuid4().hex[:6]}@example.com",
        "password": "SecurePass123",
    }


@pytest.fixture
def test_user_2():
    return {
        "username": f"user2_{uuid4().hex[:6]}",
        "email": f"user2_{uuid4().hex[:6]}@example.com",
        "password": "SecurePass456",
    }


@pytest.fixture
def test_user_3():
    return {
        "username": f"user3_{uuid4().hex[:6]}",
        "email": f"user3_{uuid4().hex[:6]}@example.com",
        "password": "SecurePass789",
    }


@pytest.fixture
async def authenticated_user(async_client, test_user):
    response = await async_client.post("/api/v1/auth/register", json=test_user)
    assert response.status_code == 201, f"Registration failed: {response.text}"
    data = response.json()
    return {
        "user": test_user,
        "token": data["access_token"],
        "user_id": data["user_id"],
        "username": data["username"],
    }


@pytest.fixture
async def auth_user(async_client):
    payload = {
        "username": f"voicetest_{uuid4().hex[:6]}",
        "email": f"voicetest_{uuid4().hex[:6]}@test.com",
        "password": "VoiceTest99!",
    }
    r = await async_client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201, f"Registration failed: {r.text}"
    data = r.json()
    return {
        "token": data["access_token"],
        "user_id": data["user_id"],
        "username": data["username"],
    }


@pytest.fixture
def client(test_db_session):
    from fastapi.testclient import TestClient

    return TestClient(app)


@pytest.fixture
def test_user_data():
    return {
        "username": f"sectest_{uuid4().hex[:6]}",
        "email": f"sectest_{uuid4().hex[:6]}@example.com",
        "password": "SecurePass123!",
    }


@pytest.fixture
def mock_voice_pipeline():
    import numpy as np

    from services.tts.base import TTSResult, Voice
    from services.voice_pipeline import VoicePipeline

    pipeline = Mock(spec=VoicePipeline)
    pipeline.is_initialized = True
    pipeline.supports_voice_cloning = True
    pipeline.stt_supports_streaming = False

    tts = MagicMock()
    tts.name = "mock_tts"
    tts.supports_speed = False
    tts.supports_language = False
    tts.supports_voice_cloning = True
    tts.default_voice = "alba"

    default_voice = Voice(
        id="alba",
        name="Alba (F)",
        language="en",
        gender="female",
        description="Test voice",
        metadata={},
    )

    tts.get_voices = AsyncMock(return_value=[default_voice])
    tts.get_voice = AsyncMock(return_value=default_voice)
    tts.get_languages = AsyncMock(return_value=[])
    tts.get_cloned_voices = AsyncMock(return_value=[])

    fake_audio = np.zeros(16000, dtype=np.float32)
    tts.synthesize = AsyncMock(
        return_value=TTSResult(
            audio=fake_audio,
            sample_rate=16000,
            duration=1.0,
            text="hello",
            voice="alba",
        )
    )

    pipeline.tts = tts

    from services.stt.base import STTResult

    stt = MagicMock()
    stt.supports_streaming = False
    stt.transcribe = AsyncMock(
        return_value=STTResult(
            text="hello world",
            segments=[],
            language="en",
            duration=1.0,
        )
    )
    pipeline.stt = stt

    pipeline.initialize = AsyncMock()
    pipeline.on_interrupt = MagicMock()
    pipeline.get_aec_state = MagicMock(return_value="idle")

    from services.stt.base import StreamingSession

    fake_session = MagicMock(spec=StreamingSession)
    fake_session.send_audio = AsyncMock()
    fake_session.close = AsyncMock()

    async def _fake_aiter(self):
        return
        yield  # pragma: no cover

    fake_session.__aiter__ = _fake_aiter
    pipeline.open_stt_stream = AsyncMock(return_value=fake_session)

    async def _fake_synthesize_stream(text, voice=None, **kwargs):
        yield {"type": "audio_info", "sample_rate": 16000}
        yield {"type": "audio", "audio": np.zeros(1600, dtype=np.float32)}

    pipeline.synthesize_stream = _fake_synthesize_stream
    pipeline.is_speaking = MagicMock(return_value=False)
    pipeline.is_ai_speaking = MagicMock(return_value=False)
    pipeline.get_vad_state = MagicMock()
    from services.vad.silero import VADState

    pipeline.get_vad_state.return_value = VADState.SILENCE
    pipeline.process_audio_chunk = MagicMock(return_value=(None, False))
    pipeline.get_speech_probability = MagicMock(return_value=0.0)

    return pipeline


@pytest.fixture
def mock_agent_client():
    from services.agent.client import AgentClient

    agent = Mock(spec=AgentClient)
    agent.is_ready = True

    from services.agent.models import ThreadResponse

    fake_thread = ThreadResponse(
        thread_id="thread_test_001",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        metadata={},
        status="idle",
    )
    agent.create_thread = AsyncMock(return_value=fake_thread)
    agent.delete_thread = AsyncMock(return_value=True)
    agent.update_thread_metadata = AsyncMock(return_value=fake_thread)
    agent.start = AsyncMock()

    async def _fake_stream_events(thread_id, text, **kwargs):
        yield {"type": "token", "content": "Hi"}
        yield {"type": "token", "content": "."}
        yield {"type": "done"}

    agent.stream_events = _fake_stream_events
    return agent
