from fastapi import HTTPException
from services.security import get_prompt_security_service
from utils import get_logger

logger = get_logger(__name__)


async def validate_message_safety(message: str) -> str:
    service = get_prompt_security_service()

    try:
        validated = await service.validate(message, raise_on_injection=True)
        return validated
    except ValueError as e:
        logger.warning(f"Message validation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


async def safe_chat_message(message: str) -> str:
    return await validate_message_safety(message)
