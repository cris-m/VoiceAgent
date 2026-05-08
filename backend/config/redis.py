from typing import Optional
import redis.asyncio as redis
from config.settings import get_settings

settings = get_settings()

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis_client

    if _redis_client is None:
        _redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=30,
        )
        await _redis_client.ping()

    return _redis_client


async def close_redis() -> None:
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None


async def clear_redis() -> None:
    """Clear all Redis data (for testing only)."""
    client = await get_redis()
    await client.flushdb()
