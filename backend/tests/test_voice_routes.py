from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from httpx import AsyncClient

# Patch where the names are USED (api.routes.v1.voice), not where defined.
_PATCH_PIPELINE = "api.routes.v1.voice.get_voice_pipeline"
_PATCH_AGENT = "api.routes.v1.voice.get_agent_client"


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_narrate_empty_text_returns_422(
    async_client: AsyncClient, auth_user, mock_voice_pipeline, mock_agent_client
):
    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), patch(_PATCH_AGENT, return_value=mock_agent_client):
        resp = await async_client.post(
            "/api/v1/voice/narrate",
            json={"text": ""},
            headers=_auth_header(auth_user["token"]),
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_narrate_missing_text_returns_422(
    async_client: AsyncClient, auth_user, mock_voice_pipeline, mock_agent_client
):
    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), patch(_PATCH_AGENT, return_value=mock_agent_client):
        resp = await async_client.post(
            "/api/v1/voice/narrate",
            json={},
            headers=_auth_header(auth_user["token"]),
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_narrate_requires_auth(async_client: AsyncClient, mock_voice_pipeline, mock_agent_client):
    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), patch(_PATCH_AGENT, return_value=mock_agent_client):
        resp = await async_client.post(
            "/api/v1/voice/narrate",
            json={"text": "hello"},
        )
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_narrate_valid_text_returns_200_with_narration_id(
    async_client: AsyncClient, auth_user, mock_voice_pipeline, mock_agent_client, tmp_path
):
    from services.tts.base import TTSResult

    fake_audio = np.zeros(16000, dtype=np.float32)
    mock_voice_pipeline.tts.synthesize = AsyncMock(
        return_value=TTSResult(audio=fake_audio, sample_rate=16000, duration=1.0, text="hello world", voice="alba")
    )

    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch("utils.file_storage.NARRATIONS_DIR", tmp_path),
    ):
        resp = await async_client.post(
            "/api/v1/voice/narrate",
            json={"text": "hello world", "voice_id": "alba"},
            headers=_auth_header(auth_user["token"]),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "id" in body
        assert body["file_type"] == "narration"


@pytest.mark.asyncio
async def test_list_narrations_returns_list(
    async_client: AsyncClient, auth_user, mock_voice_pipeline, mock_agent_client
):
    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), patch(_PATCH_AGENT, return_value=mock_agent_client):
        resp = await async_client.get(
            "/api/v1/voice/narrations",
            headers=_auth_header(auth_user["token"]),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_narrations_requires_auth(async_client: AsyncClient, mock_voice_pipeline, mock_agent_client):
    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), patch(_PATCH_AGENT, return_value=mock_agent_client):
        resp = await async_client.get("/api/v1/voice/narrations")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_nonexistent_narration_returns_404(
    async_client: AsyncClient, auth_user, mock_voice_pipeline, mock_agent_client
):
    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), patch(_PATCH_AGENT, return_value=mock_agent_client):
        resp = await async_client.delete(
            "/api/v1/voice/narrations/nonexistent-id",
            headers=_auth_header(auth_user["token"]),
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_narration_requires_auth(async_client: AsyncClient, mock_voice_pipeline, mock_agent_client):
    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), patch(_PATCH_AGENT, return_value=mock_agent_client):
        resp = await async_client.delete("/api/v1/voice/narrations/some-id")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_narrate_then_list_then_delete_lifecycle(
    async_client: AsyncClient, auth_user, mock_voice_pipeline, mock_agent_client, tmp_path
):
    from services.tts.base import TTSResult

    fake_audio = np.zeros(16000, dtype=np.float32)
    mock_voice_pipeline.tts.synthesize = AsyncMock(
        return_value=TTSResult(audio=fake_audio, sample_rate=16000, duration=1.0, text="lifecycle test", voice="alba")
    )

    auth = _auth_header(auth_user["token"])

    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch("utils.file_storage.NARRATIONS_DIR", tmp_path),
    ):
        r_narrate = await async_client.post(
            "/api/v1/voice/narrate",
            json={"text": "lifecycle test", "voice_id": "alba"},
            headers=auth,
        )
        assert r_narrate.status_code == 200, r_narrate.text
        narration_id = r_narrate.json()["id"]

        r_list = await async_client.get("/api/v1/voice/narrations", headers=auth)
        assert r_list.status_code == 200
        ids = [item["id"] for item in r_list.json()]
        assert narration_id in ids

        r_delete = await async_client.delete(f"/api/v1/voice/narrations/{narration_id}", headers=auth)
        assert r_delete.status_code in (200, 204), r_delete.text

        r_list2 = await async_client.get("/api/v1/voice/narrations", headers=auth)
        ids2 = [item["id"] for item in r_list2.json()]
        assert narration_id not in ids2


@pytest.mark.asyncio
async def test_narrate_long_text_calls_synthesize_multiple_times(
    async_client: AsyncClient, auth_user, mock_voice_pipeline, mock_agent_client, tmp_path
):
    from config.settings import settings
    from services.tts.base import TTSResult

    threshold = settings.TEXT_CHUNK_THRESHOLD
    long_text = "The quick brown fox jumped over the lazy dog. " * (threshold // 45 + 10)

    fake_audio = np.zeros(16000, dtype=np.float32)
    mock_voice_pipeline.tts.synthesize = AsyncMock(
        return_value=TTSResult(audio=fake_audio, sample_rate=16000, duration=1.0, text="chunk", voice="alba")
    )

    with (
        patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline),
        patch(_PATCH_AGENT, return_value=mock_agent_client),
        patch("utils.file_storage.NARRATIONS_DIR", tmp_path),
    ):
        resp = await async_client.post(
            "/api/v1/voice/narrate",
            json={"text": long_text, "voice_id": "alba"},
            headers=_auth_header(auth_user["token"]),
        )
        assert resp.status_code == 200, resp.text
        call_count = mock_voice_pipeline.tts.synthesize.call_count
        assert call_count > 1, f"Expected chunked synthesis, got {call_count} call(s)"
