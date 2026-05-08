from fastapi import APIRouter, HTTPException, Depends, status, Header
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from uuid import UUID
from config.database import get_db
from config.settings import settings
from schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse
from services.auth import AuthService
from services.token_blacklist import TokenBlacklistService
from api.dependency.auth import get_refresh_token_from_cookie, get_current_user_id
from api.dependency import check_rate_limit
from utils import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    dependencies=[Depends(check_rate_limit)],
)


def _set_refresh_token_cookie(response: JSONResponse, refresh_token: str):
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=60 * 60 * 24 * settings.JWT_REFRESH_EXPIRATION_DAYS,
        path="/api/v1/auth",
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserRegister, session: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    try:
        # Don't reveal which field is taken
        existing_user = await AuthService.get_user_by_username(session, request.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this credential already exists",
            )

        existing_email = await AuthService.get_user_by_email(session, request.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this credential already exists",
            )

        user = await AuthService.create_user(
            session,
            username=request.username,
            email=request.email,
            password=request.password,
        )

        access_token, _ = AuthService.create_access_token(user.user_id, user.username)
        refresh_token, _ = AuthService.create_refresh_token(user.user_id, user.username)

        logger.info(f"New user registered: {user.username}")

        response = JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=TokenResponse(
                access_token=access_token,
                user_id=user.user_id,
                username=user.username,
            ).model_dump(mode='json'),
        )

        _set_refresh_token_cookie(response, refresh_token)

        return response

    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        )
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin, session: AsyncSession = Depends(get_db)):
    """Login with username and password."""
    try:
        user = await AuthService.authenticate_user(
            session,
            username=request.username,
            password=request.password,
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token, _ = AuthService.create_access_token(user.user_id, user.username)
        refresh_token, _ = AuthService.create_refresh_token(user.user_id, user.username)

        logger.info(f"User logged in: {user.username}")

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content=TokenResponse(
                access_token=access_token,
                user_id=user.user_id,
                username=user.username,
            ).model_dump(mode='json'),
        )

        _set_refresh_token_cookie(response, refresh_token)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Get current authenticated user profile."""
    try:
        user = await AuthService.get_user_by_id(session, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user",
        )


@router.post("/refresh")
async def refresh(
    refresh_payload: dict = Depends(get_refresh_token_from_cookie),
    session: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token from httpOnly cookie."""
    try:
        user_id = refresh_payload.get("user_id")
        username = refresh_payload.get("username")
        old_jti = refresh_payload.get("jti")
        exp = refresh_payload.get("exp")

        user = await AuthService.get_user_by_id(session, UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        access_token, _ = AuthService.create_access_token(user.user_id, user.username)

        # Rotate refresh token: blacklist old to limit damage window
        if old_jti and exp:
            await TokenBlacklistService.add_to_blacklist(old_jti, exp)

        refresh_token, refresh_jti = AuthService.create_refresh_token(
            user.user_id, user.username
        )

        logger.info(f"Token refreshed for user: {username} (refresh token rotated)")

        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content=TokenResponse(
                access_token=access_token,
                user_id=user.user_id,
                username=user.username,
            ).model_dump(mode='json'),
        )

        _set_refresh_token_cookie(response, refresh_token)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(authorization: str | None = Header(default=None)):
    """Logout user and revoke access token. Clears refresh token cookie."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    payload = AuthService.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    expires_at = payload.get("exp", 0)

    if jti:
        try:
            await AuthService.revoke_token(jti, expires_at)
            logger.info(f"User {payload.get('username')} logged out")
        except Exception as e:
            # Blacklist write failed (Redis down). Don't claim logout succeeded —
            # the access token would still be valid until natural expiration.
            logger.error(f"Logout failed to revoke token: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Logout temporarily unavailable",
            )

    response = JSONResponse(status_code=status.HTTP_200_OK, content={"status": "logged out"})
    # Defense in depth: clear refresh cookie at both paths it could have been set on.
    for cookie_path in ("/api/v1/auth", "/"):
        response.delete_cookie(key="refresh_token", path=cookie_path)

    return response


