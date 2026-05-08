from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    username: str


class UserResponse(BaseModel):
    user_id: UUID
    username: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AuthError(BaseModel):
    detail: str
    code: str
