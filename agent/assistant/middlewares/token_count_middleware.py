from __future__ import annotations
from typing import Callable
import tiktoken
import logging
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

logger = logging.getLogger(__name__)


class TokenCountMiddleware(AgentMiddleware):
    """
    Middleware that counts tokens for the outgoing prompt and the model response.
    Logs token counts for monitoring/observability.

    Token counts should be returned via agent state for UI display,
    not stored in middleware.
    """

    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        try:
            self.enc = tiktoken.encoding_for_model(model_name)
        except Exception:
            self.enc = tiktoken.get_encoding("cl100k_base")

    def _count(self, text: str) -> int:
        return len(self.enc.encode(text or ""))

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        prompt_text = ""
        if hasattr(request, "prompt") and request.prompt:
            prompt_text = request.prompt
        else:
            kwargs = getattr(request, "kwargs", {}) or {}
            prompt_text = (
                kwargs.get("messages_text")
                or kwargs.get("input")
                or ""
            )

        prompt_tokens = self._count(prompt_text)
        logger.debug(f"Prompt tokens: {prompt_tokens}")

        response = handler(request)

        response_text = ""
        if hasattr(response, "text") and response.text:
            response_text = response.text
        elif hasattr(response, "content"):
            response_text = response.content
        else:
            response_text = str(response) if response else ""

        response_tokens = self._count(response_text)
        logger.debug(f"Response tokens: {response_tokens}, total: {prompt_tokens + response_tokens}")

        return response

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        prompt_text = ""
        if hasattr(request, "prompt") and request.prompt:
            prompt_text = request.prompt
        else:
            kwargs = getattr(request, "kwargs", {}) or {}
            prompt_text = (
                kwargs.get("messages_text")
                or kwargs.get("input")
                or ""
            )

        prompt_tokens = self._count(prompt_text)
        logger.debug(f"Prompt tokens: {prompt_tokens}")

        response = await handler(request)

        response_text = ""
        if hasattr(response, "text") and response.text:
            response_text = response.text
        elif hasattr(response, "content"):
            response_text = response.content
        else:
            response_text = str(response) if response else ""

        response_tokens = self._count(response_text)
        logger.debug(f"Response tokens: {response_tokens}, total: {prompt_tokens + response_tokens}")

        return response
