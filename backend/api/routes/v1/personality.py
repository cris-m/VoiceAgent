from fastapi import APIRouter, Depends, HTTPException

from api.dependency import check_rate_limit, verify_api_key
from schemas.personality import (
    PersonalitiesResponse,
    Personality,
    PersonalityCreate,
    PersonalityUpdate,
)
from utils import get_logger

logger = get_logger(__name__)
router = APIRouter(
    prefix="/personality",
    tags=["Personality"],
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)

_personalities: dict[str, Personality] = {}
_default_personality_id: str = "professional"


def _init_default_personalities():
    defaults = [
        Personality(
            id="professional",
            name="Professional",
            description="Formal, clear, and helpful. Ideal for business and customer service.",
            system_prompt="You are a professional assistant. Be clear, concise, and helpful. Use formal language and maintain a respectful tone.",
            preview_text="Good day! How may I assist you with your business needs today?",
            tags=["Business", "Customer Service"],
            is_default=True,
        ),
        Personality(
            id="friendly",
            name="Friendly",
            description="Warm, casual, and approachable. Great for casual conversations.",
            system_prompt="You are a friendly assistant. Be warm, casual, and conversational. Use everyday language and be approachable.",
            preview_text="Hey there! Great to chat with you. What's on your mind?",
            tags=["Casual", "Social"],
            is_default=False,
        ),
        Personality(
            id="expert",
            name="Expert",
            description="Technical, detailed, and knowledgeable. Perfect for technical support.",
            system_prompt="You are a technical expert. Provide detailed, accurate information. Be thorough in your explanations.",
            preview_text="I can provide detailed technical information. What would you like to know?",
            tags=["Technical", "Support"],
            is_default=False,
        ),
        Personality(
            id="empathetic",
            name="Empathetic",
            description="Understanding, supportive, and patient. Ideal for healthcare and counseling.",
            system_prompt="You are an empathetic assistant. Be understanding, patient, and supportive. Listen carefully and respond with compassion.",
            preview_text="I'm here to listen and help. Please take your time to share what's on your mind.",
            tags=["Healthcare", "Wellness"],
            is_default=False,
        ),
        Personality(
            id="energetic",
            name="Energetic",
            description="Enthusiastic, upbeat, and engaging. Great for sales and marketing.",
            system_prompt="You are an energetic assistant. Be enthusiastic, positive, and engaging. Bring energy to the conversation!",
            preview_text="This is awesome! I'm super excited to help you today! Let's do this!",
            tags=["Sales", "Marketing"],
            is_default=False,
        ),
    ]
    for p in defaults:
        _personalities[p.id] = p


_init_default_personalities()


@router.get("", response_model=PersonalitiesResponse)
async def get_personalities() -> PersonalitiesResponse:
    """Get all available personalities."""
    return PersonalitiesResponse(
        personalities=list(_personalities.values()),
        default_id=_default_personality_id,
    )


@router.get("/{personality_id}", response_model=Personality)
async def get_personality(personality_id: str) -> Personality:
    """Get a specific personality by ID."""
    if personality_id not in _personalities:
        raise HTTPException(status_code=404, detail=f"Personality not found: {personality_id}")
    return _personalities[personality_id]


@router.post("", response_model=Personality)
async def create_personality(data: PersonalityCreate) -> Personality:
    """Create a custom personality."""
    personality_id = data.name.lower().replace(" ", "_")

    if personality_id in _personalities:
        raise HTTPException(status_code=400, detail=f"Personality already exists: {personality_id}")

    personality = Personality(
        id=personality_id,
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        preview_text=data.preview_text,
        tags=data.tags,
        is_default=False,
    )
    _personalities[personality_id] = personality
    logger.info(f"Created personality: {personality_id}")
    return personality


@router.put("/{personality_id}", response_model=Personality)
async def update_personality(personality_id: str, data: PersonalityUpdate) -> Personality:
    """Update a personality."""
    if personality_id not in _personalities:
        raise HTTPException(status_code=404, detail=f"Personality not found: {personality_id}")

    personality = _personalities[personality_id]
    update_data = {}

    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.system_prompt is not None:
        update_data["system_prompt"] = data.system_prompt
    if data.preview_text is not None:
        update_data["preview_text"] = data.preview_text
    if data.tags is not None:
        update_data["tags"] = data.tags

    personality = personality.model_copy(update=update_data)
    _personalities[personality_id] = personality
    logger.info(f"Updated personality: {personality_id}")
    return personality


@router.delete("/{personality_id}")
async def delete_personality(personality_id: str) -> dict:
    """Delete a custom personality."""
    if personality_id not in _personalities:
        raise HTTPException(status_code=404, detail=f"Personality not found: {personality_id}")

    personality = _personalities[personality_id]
    if personality.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default personality")

    del _personalities[personality_id]
    logger.info(f"Deleted personality: {personality_id}")
    return {"status": "deleted", "personality_id": personality_id}


@router.post("/{personality_id}/set-default")
async def set_default_personality(personality_id: str) -> dict:
    """Set a personality as the default."""
    global _default_personality_id

    if personality_id not in _personalities:
        raise HTTPException(status_code=404, detail=f"Personality not found: {personality_id}")

    for pid, p in _personalities.items():
        _personalities[pid] = p.model_copy(update={"is_default": pid == personality_id})

    _default_personality_id = personality_id
    logger.info(f"Set default personality: {personality_id}")
    return {"status": "ok", "default_id": personality_id}
