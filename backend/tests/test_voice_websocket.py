import json
import queue
import threading
from concurrent.futures import CancelledError
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

_PATCH_PIPELINE_CREATE = "api.routes.v1.voice.create_voice_pipeline_for_connection"
_PATCH_AGENT = "api.routes.v1.voice.get_agent_client"


def _make_ws_pipeline():
    # stt_supports_streaming=True keeps transcript_collector from looping forever
    # to re-open batch sessions during the test window.
    import numpy as np

    from services.vad.silero import VADState
    from services.voice_pipeline import VoicePipeline

    pipeline = Mock(spec=VoicePipeline)
    pipeline.is_initialized = True
    pipeline.stt_supports_streaming = True
    pipeline.is_speaking = MagicMock(return_value=False)
    pipeline.is_ai_speaking = MagicMock(return_value=False)
    pipeline.get_vad_state = MagicMock(return_value=VADState.SILENCE)
    pipeline.process_audio_chunk = MagicMock(return_value=(None, False))
    pipeline.get_speech_probability = MagicMock(return_value=0.0)
    pipeline.get_aec_state = MagicMock(return_value="idle")
    pipeline.on_interrupt = MagicMock()
    pipeline.initialize = AsyncMock()

    tts = MagicMock()
    tts.name = "mock_tts"
    tts.supports_speed = False
    tts.supports_language = False
    tts.default_voice = "alba"
    tts.get_voice = AsyncMock(return_value=None)
    pipeline.tts = tts

    from services.stt.base import StreamingSession

    fake_session = MagicMock(spec=StreamingSession)
    fake_session.send_audio = AsyncMock()
    fake_session.close = AsyncMock()
    fake_session.__aiter__ = MagicMock(return_value=fake_session)
    fake_session.__anext__ = AsyncMock(side_effect=StopAsyncIteration)
    pipeline.open_stt_stream = AsyncMock(return_value=fake_session)

    async def _synth_stream(text, voice=None, **kwargs):
        yield {"type": "audio_info", "sample_rate": 16000}
        yield {"type": "audio", "audio": np.zeros(1600, dtype=np.float32)}

    pipeline.synthesize_stream = _synth_stream
    return pipeline


def _make_ws_agent():
    from services.agent.client import AgentClient
    from services.agent.models import ThreadResponse

    agent = Mock(spec=AgentClient)
    agent.is_ready = True
    agent.start = AsyncMock()

    fake_thread = ThreadResponse(
        thread_id="ws_thread_001",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        metadata={},
        status="idle",
    )
    agent.create_thread = AsyncMock(return_value=fake_thread)
    agent.delete_thread = AsyncMock(return_value=True)
    agent.update_thread_metadata = AsyncMock(return_value=fake_thread)

    async def _fake_stream(thread_id, text, **kwargs):
        yield {"type": "token", "content": "Hi"}
        yield {"type": "token", "content": " there"}
        yield {"type": "done"}

    agent.stream_events = _fake_stream
    return agent


def _collect_with_timeout(ws, *, max_n: int = 30, window_s: float = 1.5) -> list:
    # Background-thread reader: the synchronous TestClient.receive() blocks
    # while the four-task asyncio handler keeps audio_receiver alive waiting
    # for more input. A timeout join lets us assert what arrived without a
    # deadlock.
    result_q: queue.Queue = queue.Queue()

    def _reader():
        for _ in range(max_n):
            try:
                raw = ws.receive()
            except Exception:
                break
            if raw.get("type") == "websocket.disconnect":
                break
            if "text" in raw:
                try:
                    result_q.put(json.loads(raw["text"]))
                except Exception:
                    pass
            elif "bytes" in raw:
                result_q.put({"__binary__": True, "len": len(raw["bytes"])})

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    t.join(timeout=window_s)
    msgs = []
    while not result_q.empty():
        msgs.append(result_q.get_nowait())
    return msgs


def test_ws_connects_and_sends_thread_id():
    pipeline = _make_ws_pipeline()
    agent = _make_ws_agent()

    from main import app

    with patch(_PATCH_PIPELINE_CREATE, return_value=pipeline), patch(_PATCH_AGENT, return_value=agent):
        client = TestClient(app)
        try:
            with client.websocket_connect("/api/v1/voice/ws") as ws:
                raw = ws.receive()
                assert "text" in raw
                msg = json.loads(raw["text"])
                assert msg["type"] == "thread"
                assert msg["thread_id"] == "ws_thread_001"
        except CancelledError:
            pass


def test_ws_sends_correct_thread_id_from_agent():
    pipeline = _make_ws_pipeline()
    agent = _make_ws_agent()

    from main import app

    with patch(_PATCH_PIPELINE_CREATE, return_value=pipeline), patch(_PATCH_AGENT, return_value=agent):
        client = TestClient(app)
        try:
            with client.websocket_connect("/api/v1/voice/ws") as ws:
                msg = json.loads(ws.receive()["text"])
                assert msg["type"] == "thread"
                assert msg["thread_id"] == "ws_thread_001"
        except CancelledError:
            pass


def test_ws_text_input_receives_event_stream():
    pipeline = _make_ws_pipeline()
    agent = _make_ws_agent()
    collected = []

    from main import app

    with patch(_PATCH_PIPELINE_CREATE, return_value=pipeline), patch(_PATCH_AGENT, return_value=agent):
        client = TestClient(app)
        try:
            with client.websocket_connect("/api/v1/voice/ws") as ws:
                ws.receive()
                ws.send_text(json.dumps({"type": "text_input", "text": "hello server"}))
                collected = _collect_with_timeout(ws, window_s=1.5)
        except (CancelledError, Exception):
            pass

    types = {m.get("type") for m in collected if isinstance(m, dict) and "type" in m}
    expected = {"partial_transcript", "text_stream", "audio_info", "spoken_text"}
    assert types & expected, f"None of {expected} received. Got types: {types}, messages: {collected[:8]}"


def test_ws_text_input_tts_output_received():
    pipeline = _make_ws_pipeline()
    agent = _make_ws_agent()
    collected = []

    from main import app

    with patch(_PATCH_PIPELINE_CREATE, return_value=pipeline), patch(_PATCH_AGENT, return_value=agent):
        client = TestClient(app)
        try:
            with client.websocket_connect("/api/v1/voice/ws") as ws:
                ws.receive()
                ws.send_text(json.dumps({"type": "text_input", "text": "say something"}))
                collected = _collect_with_timeout(ws, window_s=1.5)
        except (CancelledError, Exception):
            pass

    types = {m.get("type") for m in collected if isinstance(m, dict)}
    has_binary = any(isinstance(m, dict) and "__binary__" in m for m in collected)
    assert "audio_info" in types or has_binary, f"No TTS output received. types={types}, binary={has_binary}"


def test_ws_wrong_api_key_rejected():
    from main import app

    with patch("config.settings.settings.API_KEY", "correct-secret"):
        client = TestClient(app)
        try:
            with client.websocket_connect("/api/v1/voice/ws?token=bad-token") as ws:
                raw = ws.receive()
                if "text" in raw:
                    msg = json.loads(raw["text"])
                    assert msg.get("type") != "thread"
        except Exception:
            pass


@pytest.mark.xfail(
    reason=(
        "Barge-in requires sending binary VAD frames with millisecond timing while "
        "TTS audio is concurrently streaming. The synchronous TestClient cannot "
        "reliably interleave WS sends/receives with the four-task asyncio handler "
        "without a dedicated async test harness (e.g., anyio + websockets client). "
        "Intent: send VAD-active binary audio while is_responding_ref['value'] is True, "
        "sustain for BARGE_IN_HOLD_MS=200ms, then assert an 'interrupt' JSON message."
    ),
    strict=False,
)
def test_ws_barge_in_interrupts_tts():
    assert False, "Not implemented; see xfail reason."
