from typing import List, Optional

from pydantic import BaseModel, Field


class MusicGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=500, description="Music generation prompt")
    style_tags: List[str] = Field(
        default_factory=list, max_length=10, description="Genre/mood tags to guide generation"
    )
    duration: float = Field(default=30.0, ge=5.0, le=180.0, description="Generated audio duration in seconds")
    tempo: Optional[int] = Field(default=None, ge=40, le=240, description="Optional BPM for tempo-aware generation")
    seed: Optional[int] = Field(default=None, description="Optional seed for reproducibility")
