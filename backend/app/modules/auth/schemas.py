from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenPair(BaseModel):
    """Internal token result used while routes set the refresh cookie."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
