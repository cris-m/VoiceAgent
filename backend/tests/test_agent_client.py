from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.agent.client import AgentClient

_DEFAULT_ASSISTANTS = [{"assistant_id": "asst_default", "name": "TestAgent", "graph_id": "graph_1"}]


def _mock_lg_client(assistants=None, thread=None):
    client = MagicMock()

    client.assistants = MagicMock()
    # NOTE: do NOT use `assistants or default` — [] is falsy and would fall through.
    resolved_assistants = _DEFAULT_ASSISTANTS if assistants is None else assistants
    client.assistants.search = AsyncMock(return_value=resolved_assistants)

    client.threads = MagicMock()
    client.threads.create = AsyncMock(
        return_value=thread
        or {
            "thread_id": "thread_abc",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "metadata": {},
            "status": "idle",
        }
    )
    client.threads.get = AsyncMock(
        return_value={
            "thread_id": "thread_abc",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "metadata": {},
            "status": "idle",
        }
    )
    client.threads.search = AsyncMock(return_value=[])
    client.threads.delete = AsyncMock(return_value=None)
    client.threads.update = AsyncMock(
        return_value={
            "thread_id": "thread_abc",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "metadata": {"name": "Updated"},
            "status": "idle",
        }
    )
    client.threads.get_state = AsyncMock(return_value={"values": {}, "next": [], "tasks": []})

    client.runs = MagicMock()
    client.runs.stream = MagicMock(return_value=_empty_async_iter())
    client.runs.wait = AsyncMock(return_value={"messages": []})
    client.runs.list = AsyncMock(return_value=[])

    return client


async def _empty_async_iter():
    return
    yield  # pragma: no cover


def _make_agent_client(mock_lg=None) -> AgentClient:
    agent = AgentClient.__new__(AgentClient)
    from services.base import ServiceStatus

    agent.name = "langgraph-agent"
    agent.status = ServiceStatus.READY
    agent.logger = MagicMock()
    agent._error = None
    agent._url = "http://localhost:2024"
    agent._client = mock_lg or _mock_lg_client()
    agent._default_assistant_id = "asst_default"
    return agent


class TestAgentClientInitialization:
    @pytest.mark.asyncio
    async def test_initialize_discovers_first_assistant(self):
        lg_client = _mock_lg_client(
            assistants=[
                {"assistant_id": "asst_001", "name": "Agent 1", "graph_id": "g1"},
                {"assistant_id": "asst_002", "name": "Agent 2", "graph_id": "g2"},
            ]
        )

        agent = AgentClient.__new__(AgentClient)
        from services.base import ServiceStatus

        agent.name = "langgraph-agent"
        agent.status = ServiceStatus.UNINITIALIZED
        agent.logger = MagicMock()
        agent._error = None
        agent._url = "http://localhost:2024"
        agent._client = None
        agent._default_assistant_id = None

        with patch("services.agent.client.get_client", return_value=lg_client):
            await agent.initialize()

        assert agent._default_assistant_id == "asst_001"

    @pytest.mark.asyncio
    async def test_initialize_with_no_assistants_logs_warning(self):
        lg_client = _mock_lg_client(assistants=[])

        agent = AgentClient.__new__(AgentClient)
        from services.base import ServiceStatus

        agent.name = "langgraph-agent"
        agent.status = ServiceStatus.UNINITIALIZED
        agent.logger = MagicMock()
        agent._error = None
        agent._url = "http://localhost:2024"
        agent._client = None
        agent._default_assistant_id = None

        with patch("services.agent.client.get_client", return_value=lg_client):
            await agent.initialize()

        warning_messages = [str(call) for call in agent.logger.warning.call_args_list]
        assert any("No assistants" in m for m in warning_messages)
        assert agent._default_assistant_id is None


class TestThreadOperations:
    @pytest.mark.asyncio
    async def test_create_thread_returns_thread_response(self):
        agent = _make_agent_client()
        result = await agent.create_thread()
        assert result.thread_id == "thread_abc"

    @pytest.mark.asyncio
    async def test_create_thread_passes_metadata(self):
        lg = _mock_lg_client()
        agent = _make_agent_client(lg)
        await agent.create_thread(metadata={"name": "My Session"})
        lg.threads.create.assert_called_once_with(metadata={"name": "My Session"})

    @pytest.mark.asyncio
    async def test_get_thread_returns_thread_response(self):
        agent = _make_agent_client()
        result = await agent.get_thread("thread_abc")
        assert result.thread_id == "thread_abc"

    @pytest.mark.asyncio
    async def test_delete_thread_returns_true(self):
        lg = _mock_lg_client()
        agent = _make_agent_client(lg)
        result = await agent.delete_thread("thread_abc")
        assert result is True
        lg.threads.delete.assert_called_once_with("thread_abc")

    @pytest.mark.asyncio
    async def test_update_thread_metadata(self):
        lg = _mock_lg_client()
        agent = _make_agent_client(lg)
        result = await agent.update_thread_metadata("thread_abc", {"name": "Updated"})
        assert result.thread_id == "thread_abc"
        assert result.metadata == {"name": "Updated"}

    @pytest.mark.asyncio
    async def test_list_threads_delegates_params(self):
        lg = _mock_lg_client()
        agent = _make_agent_client(lg)
        await agent.list_threads(limit=50, offset=10)
        lg.threads.search.assert_called_once_with(limit=50, offset=10, metadata=None, status=None)


class TestStreamEvents:
    @pytest.mark.asyncio
    async def test_stream_events_passes_mode_as_context(self):
        lg = _mock_lg_client()
        captured_context = {}

        async def fake_stream(thread_id, assistant_id, input, stream_mode, context):
            captured_context.update(context)
            return
            yield  # pragma: no cover

        lg.runs.stream = fake_stream
        agent = _make_agent_client(lg)

        async for _ in agent.stream_events("thread_abc", "hello", mode="voice"):
            pass

        assert captured_context.get("mode") == "voice"

    @pytest.mark.asyncio
    async def test_stream_events_passes_voice_name_when_provided(self):
        lg = _mock_lg_client()
        captured_context = {}

        async def fake_stream(thread_id, assistant_id, input, stream_mode, context):
            captured_context.update(context)
            return
            yield

        lg.runs.stream = fake_stream
        agent = _make_agent_client(lg)

        async for _ in agent.stream_events("thread_abc", "hello", mode="voice", voice_name="Heart"):
            pass

        assert captured_context.get("voice_name") == "Heart"

    @pytest.mark.asyncio
    async def test_stream_events_passes_voice_description_when_provided(self):
        lg = _mock_lg_client()
        captured_context = {}

        async def fake_stream(thread_id, assistant_id, input, stream_mode, context):
            captured_context.update(context)
            return
            yield

        lg.runs.stream = fake_stream
        agent = _make_agent_client(lg)

        async for _ in agent.stream_events("thread_abc", "hello", mode="voice", voice_description="Warm, expressive"):
            pass

        assert captured_context.get("voice_description") == "Warm, expressive"

    @pytest.mark.asyncio
    async def test_stream_events_omits_voice_name_when_none(self):
        lg = _mock_lg_client()
        captured_context = {}

        async def fake_stream(thread_id, assistant_id, input, stream_mode, context):
            captured_context.update(context)
            return
            yield

        lg.runs.stream = fake_stream
        agent = _make_agent_client(lg)

        async for _ in agent.stream_events("thread_abc", "hello", mode="chat"):
            pass

        assert "voice_name" not in captured_context
        assert "voice_description" not in captured_context

    @pytest.mark.asyncio
    async def test_stream_events_yields_done_at_end(self):
        lg = _mock_lg_client()
        agent = _make_agent_client(lg)

        events = []
        async for event in agent.stream_events("thread_abc", "hello", mode="chat"):
            events.append(event)

        assert any(e.get("type") == "done" for e in events)

    @pytest.mark.asyncio
    async def test_stream_events_raises_if_no_assistant(self):
        # The client's assistants.search must also return [] so re-discovery fails
        lg = _mock_lg_client(assistants=[])
        agent = _make_agent_client(lg)
        agent._default_assistant_id = None

        with pytest.raises(ValueError, match="No assistant"):
            async for _ in agent.stream_events("thread_abc", "hi"):
                pass

    @pytest.mark.asyncio
    async def test_stream_events_yields_token_events_from_partial(self):
        from unittest.mock import MagicMock as MM

        lg = _mock_lg_client()

        chunk1 = MM()
        chunk1.event = "messages/partial"
        chunk1.data = [{"type": "ai", "content": "Hello world"}]

        async def fake_stream(thread_id, assistant_id, input, stream_mode, context):
            yield chunk1

        lg.runs.stream = fake_stream
        agent = _make_agent_client(lg)

        events = []
        async for event in agent.stream_events("thread_abc", "hi"):
            events.append(event)

        token_events = [e for e in events if e.get("type") == "token"]
        assert len(token_events) == 1
        assert token_events[0]["content"] == "Hello world"

    @pytest.mark.asyncio
    async def test_stream_events_yields_error_event_on_sdk_exception(self):
        lg = _mock_lg_client()

        async def failing_stream(*args, **kwargs):
            raise ConnectionError("timeout")
            yield  # pragma: no cover

        lg.runs.stream = failing_stream
        agent = _make_agent_client(lg)

        events = []
        async for event in agent.stream_events("thread_abc", "hi"):
            events.append(event)

        error_events = [e for e in events if e.get("type") == "error"]
        assert len(error_events) >= 1
        assert "timeout" in error_events[0]["message"]


class TestInvoke:
    @pytest.mark.asyncio
    async def test_invoke_passes_mode_via_context(self):
        lg = _mock_lg_client()
        captured_context = {}

        async def fake_wait(thread_id, assistant_id, input, metadata, context):
            captured_context.update(context)
            return {"messages": []}

        lg.runs.wait = fake_wait
        agent = _make_agent_client(lg)

        await agent.invoke("thread_abc", "hello", mode="voice")

        assert captured_context.get("mode") == "voice"

    @pytest.mark.asyncio
    async def test_invoke_raises_if_no_assistant(self):
        lg = _mock_lg_client(assistants=[])
        agent = _make_agent_client(lg)
        agent._default_assistant_id = None

        with pytest.raises(ValueError, match="No assistant"):
            await agent.invoke("thread_abc", "hi")
