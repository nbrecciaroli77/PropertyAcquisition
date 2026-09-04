"""Request-scoped authority. `workspace_id` is derived from authenticated membership only."""

import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, now_utc
from app.db.base import get_db
from app.db.models import AuthSession, Journey, Membership, User, Workspace

ACCESS_COOKIE = "pa_access"
REFRESH_COOKIE = "pa_refresh"
SIGNED_IN_COOKIE = "pa_signed_in"


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession
    workspace: Workspace
    role: str


def _unauthenticated(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def bearer_or_cookie(request: Request, cookie_name: str) -> str | None:
    token = request.cookies.get(cookie_name)
    if token:
        return token
    header = request.headers.get("Authorization", "")
    if cookie_name == ACCESS_COOKIE and header.startswith("Bearer "):
        return header[7:]
    if cookie_name == REFRESH_COOKIE:
        return request.headers.get("X-Refresh-Token")
    return None


async def get_auth(request: Request, db: AsyncSession = Depends(get_db)) -> AuthContext:
    token = bearer_or_cookie(request, ACCESS_COOKIE)
    if not token:
        raise _unauthenticated()
    payload = decode_access_token(token)
    if payload is None:
        raise _unauthenticated("Session expired")

    row = (
        await db.execute(
            select(AuthSession, User, Membership, Workspace)
            .join(User, User.id == AuthSession.user_id)
            .join(Membership, Membership.user_id == User.id)
            .join(Workspace, Workspace.id == Membership.workspace_id)
            .where(AuthSession.id == uuid.UUID(str(payload["sid"])))
            .order_by(Membership.created_at)
            .limit(1)
        )
    ).first()
    if row is None:
        raise _unauthenticated("Session revoked")
    session, user, membership, workspace = row

    if session.revoked_at is not None or session.expires_at <= now_utc():
        raise _unauthenticated("Session revoked")
    if user.deleted_at is not None:
        raise _unauthenticated()
    if user.email_verified_at is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="email_not_verified")
    return AuthContext(user=user, session=session, workspace=workspace, role=membership.role)


async def scoped_journey(journey_id: uuid.UUID, db: AsyncSession, workspace_id: uuid.UUID) -> Journey:
    """Cross-tenant deep links are indistinguishable from missing rows."""
    journey = (
        await db.execute(
            select(Journey).where(Journey.id == journey_id, Journey.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()
    if journey is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    return journey


def require_writer(auth: AuthContext) -> None:
    if auth.role not in ("owner", "editor"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role cannot change the brief")
