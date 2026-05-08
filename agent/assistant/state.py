from typing import Literal, Optional
from langchain.agents.middleware import AgentState


class AgentContext(AgentState):
    mode: Literal["voice", "chat"] = "chat"

    last_prompt_tokens: Optional[int] = None
    last_response_tokens: Optional[int] = None
    total_prompt_tokens: Optional[int] = 0
    total_response_tokens: Optional[int] = 0
    last_token_update: Optional[str] = None  # ISO timestamp