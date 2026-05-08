import os
from dataclasses import dataclass, field, fields
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.language_models import BaseChatModel
from langchain.chat_models import init_chat_model


@dataclass(kw_only=True)
class Configuration:

    agent_model: str = field(
        default_factory=lambda: os.getenv("AGENT_MODEL", "openai:gpt-4o-mini"),
        metadata={
            "description": (
                "LLM for the voice agent. Format: 'provider:model'. "
                "Examples: 'openai:gpt-4o', 'openai:gpt-4o-mini', "
                "'ollama:llama3', 'anthropic:claude-sonnet-4-20250514'. "
                "Override with AGENT_MODEL env var."
            ),
        },
    )

    agent_temperature: float = field(
        default_factory=lambda: float(os.getenv("AGENT_TEMPERATURE", "0.7")),
        metadata={"description": "Temperature for agent LLM. Override with AGENT_TEMPERATURE env var."},
    )

    recursion_limit: int = field(
        default=100,
        metadata={"description": "Maximum recursion limit for agent graph execution."},
    )

    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://postgres@postgres:5432/voiceagent"),
        metadata={
            "description": (
                "PostgreSQL connection URL for memory storage. "
                "Format: postgresql://[user[:password]@][host][:port]/dbname. "
                "Override with DATABASE_URL env var."
            ),
        },
    )

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None, **_kwargs: Any
    ) -> "Configuration":
        configurable = (
            config["configurable"]
            if config and "configurable" in config
            else {}
        )
        values: dict[str, Any] = {}
        for f in fields(cls):
            if f.init:
                env_key = f.name.upper()
                config_value = configurable.get(f.name)
                env_value = os.environ.get(env_key, config_value)
                if env_value is not None:
                    values[f.name] = env_value
        return cls(**{k: v for k, v in values.items() if v is not None})

    def get_model(self) -> BaseChatModel:
        return init_chat_model(
            model=self.agent_model,
            temperature=self.agent_temperature,
        )

    @property
    def chat_system_prompt(self) -> str:
        from assistant.prompt import CHAT_SYSTEM_PROMPT
        return CHAT_SYSTEM_PROMPT

    @property
    def voice_system_prompt(self) -> str:
        from assistant.prompt import VOICE_SYSTEM_PROMPT
        return VOICE_SYSTEM_PROMPT
