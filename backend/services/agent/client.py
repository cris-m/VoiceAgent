import asyncio
from typing import AsyncIterator, Optional, Any

from langgraph_sdk import get_client
from langgraph_sdk.client import LangGraphClient

from config.settings import get_settings
from services.base import BaseService
from services.agent.models import (
    ThreadResponse,
    ThreadState,
    StreamEvent,
    AssistantInfo,
)


class AgentClient(BaseService):
    """Client for interacting with LangGraph deployments."""

    def __init__(self, url: Optional[str] = None):
        super().__init__(name="langgraph-agent")
        settings = get_settings()
        self._url = url or settings.LANGGRAPH_URL
        self._client: Optional[LangGraphClient] = None
        self._default_assistant_id: Optional[str] = None

    async def initialize(self) -> None:
        self.logger.info(f"Connecting to LangGraph at {self._url}")

        self._client = get_client(url=self._url)

        try:
            assistants = await self._client.assistants.search()
            if assistants:
                self._default_assistant_id = assistants[0]["assistant_id"]
                assistant_name = assistants[0].get("name", "Unnamed")
                self.logger.info(f"✅ Agent: {assistant_name} ({self._default_assistant_id})")
                if len(assistants) > 1:
                    self.logger.debug(f"Found {len(assistants)} assistant(s) total")
            else:
                self.logger.warning("No assistants found in deployment")
        except Exception as e:
            self.logger.error(f"Failed to discover assistants: {e}")

    async def shutdown(self) -> None:
        self._client = None
        self._default_assistant_id = None
        self.logger.info("AgentClient shutdown complete")

    async def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            await self._client.assistants.search(limit=1)
            return True
        except Exception:
            return False

    async def _ensure_initialized(self) -> None:
        if not self.is_ready:
            await self.start()
        # Lazy re-discovery: if we're connected but never resolved an assistant
        # (e.g. backend started before the agent service was reachable, or the
        # agent container was recreated mid-session), retry discovery now rather
        # than permanently failing every call with "No assistant available".
        if self._client is not None and self._default_assistant_id is None:
            try:
                assistants = await self._client.assistants.search()
                if assistants:
                    self._default_assistant_id = assistants[0]["assistant_id"]
                    self.logger.info(
                        f"✅ Agent (re-discovered): {assistants[0].get('name', 'Unnamed')} "
                        f"({self._default_assistant_id})"
                    )
            except Exception as e:
                self.logger.warning(f"Assistant re-discovery failed: {e}")

    async def list_assistants(self) -> list[AssistantInfo]:
        await self._ensure_initialized()

        assistants = await self._client.assistants.search()
        return [
            AssistantInfo(
                assistant_id=a["assistant_id"],
                graph_id=a.get("graph_id", ""),
                name=a.get("name"),
                metadata=a.get("metadata"),
                created_at=a.get("created_at"),
            )
            for a in assistants
        ]

    async def create_thread(
        self,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ThreadResponse:
        await self._ensure_initialized()

        thread = await self._client.threads.create(metadata=metadata)
        self.logger.info(f"Created thread: {thread['thread_id']}")

        return ThreadResponse(
            thread_id=thread["thread_id"],
            created_at=thread.get("created_at"),
            updated_at=thread.get("updated_at"),
            metadata=thread.get("metadata"),
            status=thread.get("status"),
        )

    async def get_thread(self, thread_id: str) -> ThreadResponse:
        await self._ensure_initialized()
        thread = await self._client.threads.get(thread_id)
        return ThreadResponse(
            thread_id=thread["thread_id"],
            created_at=thread.get("created_at"),
            updated_at=thread.get("updated_at"),
            metadata=thread.get("metadata"),
            status=thread.get("status"),
        )

    async def list_threads(
        self,
        limit: int = 100,
        offset: int = 0,
        metadata: Optional[dict[str, Any]] = None,
        status: Optional[str] = None,
    ) -> list[ThreadResponse]:
        await self._ensure_initialized()
        threads = await self._client.threads.search(
            limit=limit,
            offset=offset,
            metadata=metadata,
            status=status,
        )

        return [
            ThreadResponse(
                thread_id=t["thread_id"],
                created_at=t.get("created_at"),
                updated_at=t.get("updated_at"),
                metadata=t.get("metadata"),
                status=t.get("status"),
            )
            for t in threads
        ]

    async def delete_thread(self, thread_id: str) -> bool:
        await self._ensure_initialized()
        await self._client.threads.delete(thread_id)
        self.logger.info(f"Deleted thread: {thread_id}")
        return True

    async def update_thread_metadata(self, thread_id: str, metadata: dict) -> ThreadResponse:
        await self._ensure_initialized()
        result = await self._client.threads.update(thread_id, metadata=metadata)
        self.logger.info(f"Updated metadata for thread: {thread_id}")
        return ThreadResponse(
            thread_id=result["thread_id"],
            created_at=result.get("created_at"),
            updated_at=result.get("updated_at"),
            metadata=result.get("metadata"),
            status=result.get("status"),
        )

    async def get_thread_state(self, thread_id: str) -> ThreadState:
        await self._ensure_initialized()
        state = await self._client.threads.get_state(thread_id)
        return ThreadState(
            thread_id=thread_id,
            values=state.get("values", {}),
            next=state.get("next", []),
            tasks=state.get("tasks", []),
            metadata=state.get("metadata"),
        )

    async def stream_events(
        self,
        thread_id: str,
        message: str,
        assistant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        mode: str = "chat",
        voice_name: Optional[str] = None,
        voice_description: Optional[str] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream events in simplified format: token, message, tool_call, error, done.

        `mode` is forwarded to the agent as `context["mode"]` and selects
        between VOICE_SYSTEM_PROMPT and CHAT_SYSTEM_PROMPT in
        agent/assistant/graph.py::select_prompt. Defaults to "chat" for
        backward compatibility; voice routes should pass mode="voice".
        """
        await self._ensure_initialized()
        assistant = assistant_id or self._default_assistant_id
        if not assistant:
            raise ValueError("No assistant available")

        input_data = {
            "messages": [{"role": "human", "content": message}]
        }

        # LangGraph 0.6+ rejects sending both `configurable` and `context` together —
        # `context` is the canonical successor. Pass mode + user_id via context only.
        context: dict[str, Any] = {"mode": mode, "user_id": user_id or "unknown"}
        if voice_name:
            context["voice_name"] = voice_name
        if voice_description:
            context["voice_description"] = voice_description

        try:
            previous_content = ""
            async for chunk in self._client.runs.stream(
                thread_id,
                assistant,
                input=input_data,
                stream_mode="messages",
                context=context,
            ):
                event = chunk.event
                data = chunk.data

                if event == "messages/partial":
                    if isinstance(data, list) and len(data) > 0:
                        msg = data[-1]
                        if msg.get("type") == "ai":
                            full_content = msg.get("content", "")
                            if full_content and len(full_content) > len(previous_content):
                                delta = full_content[len(previous_content):]
                                previous_content = full_content
                                if delta:
                                    yield {"type": "token", "content": delta}

                elif event == "messages/complete":
                    if isinstance(data, list) and len(data) > 0:
                        msg = data[-1]
                        yield {
                            "type": "message",
                            "role": msg.get("type", "assistant"),
                            "content": msg.get("content", ""),
                        }

                elif event == "error":
                    yield {"type": "error", "message": str(data)}

            yield {"type": "done"}

        except Exception as e:
            self.logger.error(f"Stream error: {e}")
            yield {"type": "error", "message": str(e)}

    async def join_stream(
        self,
        thread_id: str,
        run_id: str,
    ) -> AsyncIterator[StreamEvent]:
        await self._ensure_initialized()
        self.logger.info(f"Joining stream for run {run_id} in thread {thread_id}")

        async for chunk in self._client.runs.join_stream(thread_id, run_id):
            yield StreamEvent(
                event=chunk.event,
                data=chunk.data,
                run_id=run_id,
            )

    async def invoke(
        self,
        thread_id: str,
        message: str,
        assistant_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        user_id: Optional[str] = None,
        mode: str = "chat",
    ) -> dict[str, Any]:
        await self._ensure_initialized()
        assistant = assistant_id or self._default_assistant_id
        if not assistant:
            raise ValueError("No assistant available")

        input_data = {
            "messages": [{"role": "human", "content": message}]
        }

        # LangGraph 0.6+ uses `context` instead of `configurable`.
        context = {"mode": mode, "user_id": user_id or "unknown"}

        result = await self._client.runs.wait(
            thread_id,
            assistant,
            input=input_data,
            metadata=metadata,
            context=context,
        )

        return result

    async def get_run_history(
        self,
        thread_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        await self._ensure_initialized()
        runs = await self._client.runs.list(thread_id, limit=limit)
        return runs

    @property
    def default_assistant_id(self) -> Optional[str]:
        return self._default_assistant_id


_agent_client: Optional[AgentClient] = None
_agent_client_lock = asyncio.Lock()
_agent_client_initialized = False


async def initialize_agent_client() -> None:
    global _agent_client, _agent_client_initialized
    async with _agent_client_lock:
        if not _agent_client_initialized:
            _agent_client = AgentClient()
            await _agent_client._ensure_initialized()
            _agent_client_initialized = True


async def shutdown_agent_client() -> None:
    global _agent_client
    async with _agent_client_lock:
        if _agent_client is not None:
            await _agent_client.shutdown()
            _agent_client = None
            _agent_client_initialized = False


def get_agent_client() -> AgentClient:
    if _agent_client is None:
        raise RuntimeError("AgentClient not initialized. Call initialize_agent_client() first.")
    return _agent_client
