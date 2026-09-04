from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _check_password(value: str) -> str:
    if len(value) < 10:
        raise ValueError("Use at least 10 characters.")
    if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
        raise ValueError("Include at least one letter and one number.")
    return value


class SignupRequest(Strict):
    email: EmailStr
    password: str = Field(max_length=200)
    display_name: str = Field(min_length=1, max_length=120)
    workspace_name: str | None = Field(default=None, max_length=160)
    timezone: str = Field(default="Australia/Perth", max_length=64)

    _password = field_validator("password")(_check_password)


class LoginRequest(Strict):
    email: EmailStr
    password: str = Field(max_length=200)


class TokenRequest(Strict):
    token: str = Field(min_length=10, max_length=400)


class EmailRequest(Strict):
    email: EmailStr


class ResetPasswordRequest(Strict):
    token: str = Field(min_length=10, max_length=400)
    password: str = Field(max_length=200)

    _password = field_validator("password")(_check_password)


class ProfileUpdate(Strict):
    display_name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(min_length=1, max_length=64)


class SignupResponse(Strict):
    status: Literal["verification_pending"]
    email: EmailStr
    message: str


class WorkspaceOut(Strict):
    id: UUID
    name: str
    timezone: str
    currency: str
    role: str


class UserOut(Strict):
    id: UUID
    email: EmailStr
    display_name: str
    timezone: str
    locale: str
    email_verified: bool


class SessionOut(Strict):
    id: UUID
    user_agent: str
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    current: bool


class MeResponse(Strict):
    user: UserOut
    workspace: WorkspaceOut
    session_count: int
