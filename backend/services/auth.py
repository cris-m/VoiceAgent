from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID, uuid4

import jwt
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from models.user import User
from services.token_blacklist import TokenBlacklistService

settings = get_settings()


class AuthService:
    # Dummy hash (bcrypt of empty string) used to prevent username enumeration
    # via timing differences when authenticating non-existent users.
    DUMMY_HASH = "$2b$12$7BIv/cP4SqVgN6EZhLzKP.T3QvT1TfWZxuqjCO1H9u7EFfLpQ/YMG"

    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

    @staticmethod
    def create_access_token(user_id: UUID, username: str) -> tuple[str, str]:
        jti = str(uuid4())
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)

        payload = {
            "jti": jti,
            "user_id": str(user_id),
            "username": username,
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token, jti

    @staticmethod
    def create_refresh_token(user_id: UUID, username: str) -> tuple[str, str]:
        jti = str(uuid4())
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)

        payload = {
            "jti": jti,
            "user_id": str(user_id),
            "username": username,
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp()),
            "type": "refresh",
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return token, jti

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verify and decode a JWT token (signature + expiration only).

        Note: blacklist check is the caller's responsibility — see
        `api/dependency/auth.py::get_current_user_id` and `get_refresh_token_from_cookie`.
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    async def get_user_by_username(
        session: AsyncSession, username: str
    ) -> Optional[User]:
        result = await session.execute(
            select(User).where(User.username == username).where(User.is_active == True)
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
        result = await session.execute(
            select(User).where(User.email == email).where(User.is_active == True)
        )
        return result.scalars().first()

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: UUID) -> Optional[User]:
        result = await session.execute(
            select(User).where(User.user_id == user_id).where(User.is_active == True)
        )
        return result.scalars().first()

    @staticmethod
    async def create_user(
        session: AsyncSession, username: str, email: str, password: str
    ) -> User:
        hashed_password = AuthService.hash_password(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    @staticmethod
    async def revoke_token(jti: str, expires_at: int) -> None:
        await TokenBlacklistService.add_to_blacklist(jti, expires_at)

    @staticmethod
    async def authenticate_user(
        session: AsyncSession, username: str, password: str
    ) -> Optional[User]:
        """Authenticate user with username and password.

        Always performs password verification (even for non-existent users)
        to prevent timing attacks that reveal valid usernames.
        """
        user = await AuthService.get_user_by_username(session, username)

        # Always verify (even when user is missing) to prevent timing attacks
        # that would otherwise reveal valid usernames.
        hashed_password = user.hashed_password if user else AuthService.DUMMY_HASH
        if not AuthService.verify_password(password, hashed_password):
            return None

        return user
