import hmac
import ipaddress
from typing import Annotated, Optional

from fastapi import Header, HTTPException, Request, status

from config import settings
from core.rate_limiter import InMemoryRateLimiter

rate_limiter = InMemoryRateLimiter(
    requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)

TRUSTED_PROXIES = getattr(settings, 'TRUSTED_PROXIES', ['127.0.0.1', '::1', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'])


def _is_trusted_proxy(ip: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(ip)
        for proxy in TRUSTED_PROXIES:
            try:
                if ip_obj in ipaddress.ip_network(proxy, strict=False):
                    return True
            except ValueError:
                if ip == proxy:
                    return True
    except ValueError:
        pass
    return False


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, validating X-Forwarded-For if present.

    Only trusts X-Forwarded-For if the direct connection is from a trusted proxy.
    Falls back to request.client.host if X-Forwarded-For is untrusted.
    """
    direct_ip = request.client.host if request.client else "unknown"

    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        if _is_trusted_proxy(direct_ip):
            client_ip = x_forwarded_for.split(",")[0].strip()
            return client_ip

    return direct_ip


async def verify_api_key(
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
    x_api_key: Annotated[Optional[str], Header()] = None,
) -> None:
    """Verify API key from Authorization header or X-API-Key header.

    Uses timing-safe HMAC comparison. When API_KEY is not set (None),
    skips auth entirely (development mode).

    In production, API_KEY must be set.

    Raises:
        HTTPException: 401 if auth required but invalid or missing
    """
    if settings.API_KEY is None:
        if settings.ENVIRONMENT == "production":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API_KEY not configured",
            )
        return

    token = None
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    if not token and x_api_key:
        token = x_api_key

    if not token or not hmac.compare_digest(token, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def check_rate_limit(request: Request) -> None:
    """Check rate limit for client IP (async-safe).

    Extracts IP from request or X-Forwarded-For header, validating
    that X-Forwarded-For is only trusted from known proxies.
    Raises 429 if limit exceeded.

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    client_ip = _get_client_ip(request)

    if not await rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(settings.RATE_LIMIT_WINDOW_SECONDS)},
        )
