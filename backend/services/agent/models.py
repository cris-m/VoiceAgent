from typing import Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class MessageInput(BaseModel):
    role: Literal["human", "assistant", "system"] = "human"
    content: str


class ThreadCreate(BaseModel):
    metadata: Optional[dict[str, Any]] = None


class ThreadMetadataUpdate(BaseModel):
    metadata: dict[str, Any]


class ThreadResponse(BaseModel):
    thread_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None
    status: Optional[str] = None


class ThreadState(BaseModel):
    thread_id: str
    values: dict[str, Any] = Field(default_factory=dict)
    next: list[str] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = None


class RunConfig(BaseModel):
    thread_id: str
    assistant_id: Optional[str] = None
    input: dict[str, Any] = Field(default_factory=dict)
    metadata: Optional[dict[str, Any]] = None
    config: Optional[dict[str, Any]] = None
    stream_mode: Literal["values", "updates", "messages", "events", "debug"] = "messages"
    interrupt_before: Optional[list[str]] = None
    interrupt_after: Optional[list[str]] = None


class StreamEvent(BaseModel):
    event: str
    data: Any
    run_id: Optional[str] = None


class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    message: str
    user_id: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class AssistantInfo(BaseModel):
    assistant_id: str
    graph_id: str
    name: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
