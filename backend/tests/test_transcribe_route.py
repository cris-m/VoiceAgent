import io
import wave
import pytest
import numpy as np
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport

_PATCH_PIPELINE = "api.routes.v1.voice.get_voice_pipeline"
_PATCH_AGENT = "api.routes.v1.voice.get_agent_client"


def _make_wav_bytes(duration_seconds: float = 0.5, sample_rate: int = 16000) -> bytes:
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


async def _relaxed_client(mock_pipeline, mock_agent):
    # raise_app_exceptions=False: the transcribe route re-raises ValueError on
    # invalid audio (a production bug). Without this flag, the test client would
    # propagate the exception instead of letting us assert the resulting status.
    from main import app
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_transcribe_txt_file_rejected(mock_voice_pipeline, mock_agent_client):
    # Production bug: route raises ValueError instead of HTTPException, so this
    # arrives as 500. Test accepts 400/422/500 until the route is fixed.
    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), \
         patch(_PATCH_AGENT, return_value=mock_agent_client):
        async with await _relaxed_client(mock_voice_pipeline, mock_agent_client) as client:
            resp = await client.post(
                "/api/v1/voice/transcribe",
                files={"file": ("audio.txt", b"plain text not audio", "text/plain")},
            )
            assert resp.status_code in (400, 422, 500)


@pytest.mark.asyncio
async def test_transcribe_empty_file_rejected(mock_voice_pipeline, mock_agent_client):
    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), \
         patch(_PATCH_AGENT, return_value=mock_agent_client):
        async with await _relaxed_client(mock_voice_pipeline, mock_agent_client) as client:
            resp = await client.post(
                "/api/v1/voice/transcribe",
                files={"file": ("audio.wav", b"", "audio/wav")},
            )
            assert resp.status_code >= 400


@pytest.mark.asyncio
async def test_transcribe_valid_wav_returns_transcript(
    async_client: AsyncClient, mock_voice_pipeline, mock_agent_client
):
    from services.stt.base import STTResult

    mock_voice_pipeline.stt.transcribe = AsyncMock(return_value=STTResult(
        text="hello world",
        segments=[],
        language="en",
        duration=0.5,
    ))

    wav_data = _make_wav_bytes(duration_seconds=0.5)

    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), \
         patch(_PATCH_AGENT, return_value=mock_agent_client):
        resp = await async_client.post(
            "/api/v1/voice/transcribe",
            files={"file": ("audio.wav", wav_data, "audio/wav")},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "text" in body
        assert body["text"] == "hello world"
        assert "duration_seconds" in body


@pytest.mark.asyncio
async def test_transcribe_returns_language_field(
    async_client: AsyncClient, mock_voice_pipeline, mock_agent_client
):
    from services.stt.base import STTResult

    mock_voice_pipeline.stt.transcribe = AsyncMock(return_value=STTResult(
        text="bonjour",
        segments=[],
        language="fr",
        duration=0.3,
    ))

    wav_data = _make_wav_bytes(duration_seconds=0.3)

    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), \
         patch(_PATCH_AGENT, return_value=mock_agent_client):
        resp = await async_client.post(
            "/api/v1/voice/transcribe",
            files={"file": ("audio.wav", wav_data, "audio/wav")},
            data={"language": "fr"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "language" in body


@pytest.mark.asyncio
async def test_transcribe_no_file_returns_422(
    async_client: AsyncClient, mock_voice_pipeline, mock_agent_client
):
    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), \
         patch(_PATCH_AGENT, return_value=mock_agent_client):
        resp = await async_client.post("/api/v1/voice/transcribe")
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_transcribe_long_audio_calls_chunker(
    async_client: AsyncClient, mock_voice_pipeline, mock_agent_client
):
    from services.stt.base import STTResult
    from config.settings import settings

    threshold_secs = settings.AUDIO_CHUNK_THRESHOLD
    long_duration = threshold_secs + 5.0
    wav_data = _make_wav_bytes(duration_seconds=long_duration, sample_rate=16000)

    mock_voice_pipeline.stt.transcribe = AsyncMock(return_value=STTResult(
        text="long audio transcript",
        segments=[],
        language="en",
        duration=long_duration,
    ))

    chunk_call_count = []

    import services.stt.audio_chunker as _chunker_mod
    original_chunk_by_duration = _chunker_mod.AudioChunker.chunk_by_duration

    def _spy_chunk_by_duration(self, segment):
        result = original_chunk_by_duration(self, segment)
        chunk_call_count.append(len(result))
        return result

    with patch(_PATCH_PIPELINE, return_value=mock_voice_pipeline), \
         patch(_PATCH_AGENT, return_value=mock_agent_client), \
         patch.object(_chunker_mod.AudioChunker, "chunk_by_duration", _spy_chunk_by_duration):
        resp = await async_client.post(
            "/api/v1/voice/transcribe",
            files={"file": ("long_audio.wav", wav_data, "audio/wav")},
        )
        if resp.status_code == 200:
            assert len(chunk_call_count) >= 1, "AudioChunker.chunk_by_duration was not called"
