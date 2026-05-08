import logging
import os
from datetime import datetime

from deepagents import create_deep_agent

logger = logging.getLogger(__name__)
from deepagents.middleware.skills import SkillsMiddleware
from langchain.agents.middleware import (
    dynamic_prompt,
    ModelRequest,
    ToolCallLimitMiddleware,
    ModelRetryMiddleware,
    ToolRetryMiddleware,
    ContextEditingMiddleware,
    HumanInTheLoopMiddleware,
)
from langgraph.store.postgres import PostgresStore

from assistant.config import Configuration
from assistant.tools import all_tools
from assistant.mcp import get_mcp_tools
from assistant.backend import composite_backend
from assistant.state import AgentContext
from assistant.middlewares.token_count_middleware import TokenCountMiddleware


@dynamic_prompt
def select_prompt(request: ModelRequest) -> str:
    ctx = getattr(request.runtime, 'context', {}) or {}
    config = Configuration.from_runnable_config(context=ctx)

    runnable_config = getattr(request, 'config', None) or {}
    configurable = (runnable_config.get('configurable') if isinstance(runnable_config, dict) else {}) or {}
    mode = ctx.get("mode") or configurable.get("mode") or "chat"
    mode = str(mode).lower().strip()

    current_date = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    if mode == "voice":
        prompt = config.voice_system_prompt
        voice_name = ctx.get("voice_name") or "the assistant"
        voice_description = ctx.get("voice_description") or "a clear, professional voice"
        logger.debug(
            "[select_prompt] mode=voice voice_name=%r voice_description=%r",
            voice_name, voice_description,
        )
        return prompt.format(
            current_date=current_date,
            voice_name=voice_name,
            voice_description=voice_description,
        )

    return config.chat_system_prompt.format(current_date=current_date)


def create_agent():
    config = Configuration.from_runnable_config()
    model = config.get_model()

    mcp_tools = get_mcp_tools()
    store = PostgresStore(config.database_url)
    combined_tools = all_tools + mcp_tools

    model_name = config.agent_model.split(":")[-1] if ":" in config.agent_model else config.agent_model

    middleware_stack = [
        select_prompt,
        TokenCountMiddleware(model_name=model_name),
        ToolCallLimitMiddleware(
            run_limit=10,
            thread_limit=50,
            exit_behavior="continue",
        ),
        ModelRetryMiddleware(max_retries=2, backoff_factor=1.0),
        ToolRetryMiddleware(max_retries=2, backoff_factor=1.0),
        ContextEditingMiddleware(),
        HumanInTheLoopMiddleware(interrupt_on={"memory_delete": {}, "memory_store": {}}),
        SkillsMiddleware(backend=composite_backend(), sources=["/skills/"]),
    ]

    agent = create_deep_agent(
        name="voice_agent",
        model=model,
        context_schema=AgentContext,
        tools=combined_tools,
        system_prompt="",
        middleware=middleware_stack,
        memory=["./assistant/AGENTS.md", "./assistant/user/AGENTS.md"],
        backend=composite_backend(),
        store=store,
    ).with_config({"recursion_limit": config.recursion_limit})

    return agent


agent = create_agent()
