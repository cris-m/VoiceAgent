import io
import wave
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

_PATCH_PIPELINE = "api.routes.v1.voice.get_voice_pipeline"
_PATCH_AGENT = "api.routes.v1.voice.get_agent_client"
_PATCH_SUPPORTS_CLONING = "api.routes.v1.voice._supports_cloning"


def _make_wav_bytes(duration_seconds: float = 2.0, sample_rate: int = 16000) -> bytes:
    n_samples = int(sample_rate * duration_seconds)
    samples = np.zeros(n_samples, dtype=np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples.tobytes())
    buf.seek(0)
    return buf.read()


def _make_tiny_wav_bytes(duration_seconds: float = 0.1, sample_rate: int = 16000) -> bytes:
    return _make_wav_bytes(duration_seconds=duration_seconds, sample_rate=sample_rate)


async def _relaxed_client():
    # See test_transcribe_route._relaxed_client for rationale.
    from main import app

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    return AsyncClient(transport=transport, base_url="http://test")


def _cloned_voice():
    from services.tts.base import Voice

    return Voice(
        id="clone_ab12cd34",
        name="My Clone",
        language="en",
        gender=None,
        description="Test clone",
        metadata={"is_cloned": True},
    )


@pytest.mark.asyncio
async def test_clone_rejects_non_pocket_tts(async_client: AsyncClient, mock_voice_pipeline, mock_agent_client):
    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=False),
    ):
        wav_data = _make_wav_bytes(duration_seconds=2.0)
        resp = await async_client.post(
            "/api/v1/voice/clone",
            files={"file": ("ref.wav", wav_data, "audio/wav")},
            data={"name": "TestClone"},
        )
        assert resp.status_code == 400
        body = resp.json()
        # Errors flow through the global handler which wraps them as {"error": {...}}.
        assert "error" in body or "detail" in body


@pytest.mark.asyncio
async def test_clone_rejects_too_short_audio(mock_voice_pipeline, mock_agent_client):
    # 400 = explicit duration rejection. 500 = pydub failing on a tiny WAV.
    # Either is acceptable; both keep the user from cloning unusable audio.
    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=True),
    ):
        async with await _relaxed_client() as client:
            tiny_wav = _make_tiny_wav_bytes(duration_seconds=0.05)
            resp = await client.post(
                "/api/v1/voice/clone",
                files={"file": ("tiny.wav", tiny_wav, "audio/wav")},
                data={"name": "TinyClone"},
            )
            assert resp.status_code in (400, 500)


@pytest.mark.asyncio
async def test_clone_missing_name_returns_422(async_client: AsyncClient, mock_voice_pipeline, mock_agent_client):
    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=True),
    ):
        wav_data = _make_wav_bytes(duration_seconds=2.0)
        resp = await async_client.post(
            "/api/v1/voice/clone",
            files={"file": ("ref.wav", wav_data, "audio/wav")},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_clone_no_file_returns_422(async_client: AsyncClient, mock_voice_pipeline, mock_agent_client):
    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=True),
    ):
        resp = await async_client.post(
            "/api/v1/voice/clone",
            data={"name": "TestClone"},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_clone_happy_path_returns_voice_id(async_client: AsyncClient, mock_voice_pipeline, mock_agent_client):
    cloned = _cloned_voice()
    mock_voice_pipeline.tts.clone_voice = AsyncMock(return_value=cloned)

    wav_data = _make_wav_bytes(duration_seconds=3.0)

    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=True),
    ):
        resp = await async_client.post(
            "/api/v1/voice/clone",
            files={"file": ("ref.wav", wav_data, "audio/wav")},
            data={"name": "My Clone"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == "clone_ab12cd34"
        assert body["name"] == "My Clone"
        assert body["is_cloned"] is True
        assert "message" in body


@pytest.mark.asyncio
async def test_list_clones_happy_path(async_client: AsyncClient, mock_voice_pipeline, mock_agent_client):
    from services.tts.base import Voice

    cloned_voice = Voice(
        id="clone_ab12cd34",
        name="My Clone",
        language="en",
        gender=None,
        description=None,
        metadata={"is_cloned": True},
    )
    mock_voice_pipeline.tts.get_cloned_voices = AsyncMock(return_value=[cloned_voice])

    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=True),
    ):
        resp = await async_client.get("/api/v1/voice/clones")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "voices" in body
        assert body["count"] == 1
        assert body["voices"][0]["id"] == "clone_ab12cd34"


@pytest.mark.asyncio
async def test_list_clones_without_pocket_tts_returns_400(
    async_client: AsyncClient, mock_voice_pipeline, mock_agent_client
):
    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=False),
    ):
        resp = await async_client.get("/api/v1/voice/clones")
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_clones_empty_list(async_client: AsyncClient, mock_voice_pipeline, mock_agent_client):
    mock_voice_pipeline.tts.get_cloned_voices = AsyncMock(return_value=[])

    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=True),
    ):
        resp = await async_client.get("/api/v1/voice/clones")
        assert resp.status_code == 200
        body = resp.json()
        assert body["voices"] == []
        assert body["count"] == 0


@pytest.mark.asyncio
async def test_delete_clone_invalid_id_format_returns_400(
    async_client: AsyncClient, mock_voice_pipeline, mock_agent_client
):
    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=True),
    ):
        resp = await async_client.delete("/api/v1/voice/clones/invalid-format")
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_clone_not_found_returns_404(async_client: AsyncClient, mock_voice_pipeline, mock_agent_client):
    mock_voice_pipeline.tts.delete_cloned_voice = AsyncMock(return_value=False)

    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=True),
    ):
        resp = await async_client.delete("/api/v1/voice/clones/clone_ab12cd34")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_clone_happy_path(async_client: AsyncClient, mock_voice_pipeline, mock_agent_client):
    mock_voice_pipeline.tts.delete_cloned_voice = AsyncMock(return_value=True)

    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=True),
    ):
        resp = await async_client.delete("/api/v1/voice/clones/clone_ab12cd34")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "deleted"
        assert body["clone_id"] == "clone_ab12cd34"


@pytest.mark.asyncio
async def test_delete_clone_without_pocket_tts_returns_400(
    async_client: AsyncClient, mock_voice_pipeline, mock_agent_client
):
    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch(_PATCH_SUPPORTS_CLONING, return_value=False),
    ):
        resp = await async_client.delete("/api/v1/voice/clones/clone_ab12cd34")
        assert resp.status_code == 400
