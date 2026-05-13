from datetime import datetime, timezone

from config.redis import get_redis
from config.settings import get_settings

settings = get_settings()

BLACKLIST_KEY_PREFIX = "token_blacklist:"
REVOKED_TOKENS_KEY = "revoked_tokens:set"


class TokenBlacklistService:
    @staticmethod
    async def add_to_blacklist(
        jti: str,
        expires_at: int,
    ) -> None:
        client = await get_redis()

        now = int(datetime.now(timezone.utc).timestamp())
        ttl = max(expires_at - now, 60)  # Minimum 60 seconds TTL

        key = f"{BLACKLIST_KEY_PREFIX}{jti}"
        await client.setex(key, ttl, "1")

        await client.sadd(REVOKED_TOKENS_KEY, jti)

    @staticmethod
    async def is_blacklisted(jti: str) -> bool:
        client = await get_redis()
        key = f"{BLACKLIST_KEY_PREFIX}{jti}"
        return await client.exists(key) == 1

    @staticmethod
    async def remove_from_blacklist(jti: str) -> bool:
        client = await get_redis()
        key = f"{BLACKLIST_KEY_PREFIX}{jti}"
        result = await client.delete(key)
        return result > 0

    @staticmethod
    async def get_blacklist_stats() -> dict:
        client = await get_redis()

        blacklist_keys = await client.keys(f"{BLACKLIST_KEY_PREFIX}*")
        count = len(blacklist_keys)

        set_size = await client.scard(REVOKED_TOKENS_KEY)

        return {
            "blacklisted_tokens": count,
            "revoked_tokens_set_size": set_size,
        }

    @staticmethod
    async def clear_blacklist() -> int:
        """Clear all blacklisted tokens (testing/admin only)."""
        client = await get_redis()

        keys = await client.keys(f"{BLACKLIST_KEY_PREFIX}*")
        if keys:
            deleted = await client.delete(*keys)
        else:
            deleted = 0

        await client.delete(REVOKED_TOKENS_KEY)

        return deleted
