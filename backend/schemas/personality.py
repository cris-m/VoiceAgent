from typing import Optional, List
from pydantic import BaseModel, Field


class Personality(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    preview_text: str  # Text to test this personality on UI
    tags: Optional[List[str]] = None
    is_default: bool = False


class PersonalityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    system_prompt: str = Field(min_length=1)
    preview_text: str = Field(min_length=1)
    tags: Optional[List[str]] = None


class PersonalityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, min_length=1, max_length=500)
    system_prompt: Optional[str] = Field(default=None, min_length=1)
    preview_text: Optional[str] = Field(default=None, min_length=1)
    tags: Optional[List[str]] = None


class PersonalitiesResponse(BaseModel):
    personalities: List[Personality]
    default_id: str
