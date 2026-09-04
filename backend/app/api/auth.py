import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    SIGNED_IN_COOKIE,
    AuthContext,
    bearer_or_cookie,
    get_auth,
)
from app.core.security import (
    create_access_token,
    hash_password,
    new_opaque_token,
    now_utc,
    token_fingerprint,
    verify_password,
)
from app.db.base import get_db
from app.db.models import AuthSession, AuthToken, LoginAttempt, Membership, User, Workspace
from app.schemas.auth import (
    EmailRequest,
    LoginRequest,
    MeResponse,
    ProfileUpdate,
    ResetPasswordRequest,
    SessionOut,
    SignupRequest,
    SignupResponse,
    TokenRequest,
    UserOut,
    WorkspaceOut,
)
from app.services.outbox import action_url, queue_email, record_audit

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_ACTIVE_SESSIONS = 10

VERIFICATION_PENDING_MESSAGE = (
    "Check your email to confirm your address. In this prototype no email is delivered — "
    "open the development outbox to follow the link."
)


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        ACCESS_COOKIE,
        access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=settings.access_token_minutes * 60,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=settings.refresh_token_days * 86400,
        path="/",
    )
    # Readable marker only: the client uses it to decide whether a session bootstrap is worthwhile.
    response.set_cookie(
        SIGNED_IN_COOKIE,
        "1",
        httponly=False,
        secure=True,
        samesite="none",
        max_age=settings.refresh_token_days * 86400,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, path="/", secure=True, samesite="none", httponly=True)
    response.delete_cookie(SIGNED_IN_COOKIE, path="/", secure=True, samesite="none")


async def _issue_session(db: AsyncSession, user: User, request: Request, response: Response) -> None:
    settings = get_settings()
    refresh_token = new_opaque_token()
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=token_fingerprint(refresh_token),
        user_agent=(request.headers.get("user-agent") or "")[:400],
        expires_at=now_utc() + timedelta(days=settings.refresh_token_days),
    )
    db.add(session)
    await db.flush()
    await _prune_sessions(db, user.id, keep=MAX_ACTIVE_SESSIONS)
    _set_auth_cookies(response, create_access_token(user.id, session.id, user.email), refresh_token)


async def _prune_sessions(db: AsyncSession, user_id: uuid.UUID, keep: int) -> None:
    """Keeps the session list honest: only the newest `keep` sessions stay live."""
    live = (
        (
            await db.execute(
                select(AuthSession)
                .where(
                    AuthSession.user_id == user_id,
                    AuthSession.revoked_at.is_(None),
                    AuthSession.expires_at > now_utc(),
                )
                .order_by(AuthSession.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    for stale in live[keep:]:
        stale.revoked_at = now_utc()
        stale.revoked_reason = "session_cap"


async def _issue_verification(db: AsyncSession, user: User) -> None:
    settings = get_settings()
    token = new_opaque_token()
    db.add(
        AuthToken(
            user_id=user.id,
            kind="verify_email",
            token_hash=token_fingerprint(token),
            expires_at=now_utc() + timedelta(hours=settings.verification_token_hours),
        )
    )
    await queue_email(
        db,
        to_email=user.email,
        kind="verify_email",
        subject="Confirm your email address",
        body_text=(
            f"Hello {user.display_name},\n\nConfirm your email address to finish setting up your "
            "Property Acquisition workspace. This link expires in "
            f"{settings.verification_token_hours} hours.\n"
        ),
        action_url=action_url(f"/verify-email?token={token}"),
    )


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        timezone=user.timezone,
        locale=user.locale,
        email_verified=user.email_verified_at is not None,
    )


async def _me(db: AsyncSession, auth: AuthContext) -> MeResponse:
    count = (
        await db.execute(
            select(func.count())
            .select_from(AuthSession)
            .where(
                AuthSession.user_id == auth.user.id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now_utc(),
            )
        )
    ).scalar_one()
    return MeResponse(
        user=_user_out(auth.user),
        workspace=WorkspaceOut(
            id=auth.workspace.id,
            name=auth.workspace.name,
            timezone=auth.workspace.timezone,
            currency=auth.workspace.currency,
            role=auth.role,
        ),
        session_count=int(count),
    )


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)) -> SignupResponse:
    email = body.email.strip().lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    if existing is not None:
        if existing.email_verified_at is None:
            await _issue_verification(db, existing)
        else:
            await queue_email(
                db,
                to_email=email,
                kind="account_exists",
                subject="You already have an account",
                body_text=(
                    "Someone tried to sign up with this address. Sign in instead, or reset your password.\n"
                ),
                action_url=action_url("/"),
            )
        await db.commit()
        return SignupResponse(
            status="verification_pending", email=email, message=VERIFICATION_PENDING_MESSAGE
        )

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        display_name=body.display_name.strip(),
        timezone=body.timezone,
    )
    db.add(user)
    await db.flush()

    workspace = Workspace(
        name=(body.workspace_name or f"{user.display_name}'s workspace").strip(),
        owner_user_id=user.id,
        timezone=body.timezone,
    )
    db.add(workspace)
    await db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role="owner"))

    await _issue_verification(db, user)
    await record_audit(
        db, action="account.signup", actor_user_id=user.id, workspace_id=workspace.id, subject=email
    )
    await db.commit()
    return SignupResponse(status="verification_pending", email=email, message=VERIFICATION_PENDING_MESSAGE)


@router.post("/reissue-verification", status_code=status.HTTP_202_ACCEPTED)
async def reissue_verification(body: EmailRequest, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    email = body.email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is not None and user.email_verified_at is None:
        await _issue_verification(db, user)
        await db.commit()
    return {"status": "accepted", "message": VERIFICATION_PENDING_MESSAGE}


async def _consume_token(db: AsyncSession, raw_token: str, kind: str) -> User:
    token = (
        await db.execute(
            select(AuthToken).where(
                AuthToken.token_hash == token_fingerprint(raw_token), AuthToken.kind == kind
            )
        )
    ).scalar_one_or_none()
    if token is None or token.used_at is not None or token.expires_at <= now_utc():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This link is invalid or has expired."
        )
    token.used_at = now_utc()
    user = (await db.execute(select(User).where(User.id == token.user_id))).scalar_one()
    return user


@router.post("/verify-email")
async def verify_email(body: TokenRequest, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    user = await _consume_token(db, body.token, "verify_email")
    if user.email_verified_at is None:
        user.email_verified_at = now_utc()
    await record_audit(db, action="account.email_verified", actor_user_id=user.id, subject=user.email)
    await db.commit()
    return {"status": "verified", "email": user.email}


def client_ip(request: Request) -> str:
    """First hop of X-Forwarded-For behind the trusted ingress; the socket peer rotates between pods."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:100]
    return request.client.host if request.client else "unknown"


def _identifiers(request: Request, email: str) -> tuple[str, str]:
    return f"email:{email}", f"ip:{client_ip(request)}"


async def _failures_since(db: AsyncSession, identifier: str, minutes: int) -> int:
    since = now_utc() - timedelta(minutes=minutes)
    count = (
        await db.execute(
            select(func.count())
            .select_from(LoginAttempt)
            .where(
                LoginAttempt.identifier == identifier,
                LoginAttempt.successful.is_(False),
                LoginAttempt.created_at >= since,
            )
        )
    ).scalar_one()
    return int(count)


async def _locked_out(db: AsyncSession, request: Request, email: str) -> bool:
    settings = get_settings()
    by_email, by_ip = _identifiers(request, email)
    window = settings.login_lockout_minutes
    if await _failures_since(db, by_email, window) >= settings.login_lockout_attempts:
        return True
    return await _failures_since(db, by_ip, window) >= settings.login_lockout_ip_attempts


@router.post("/login", response_model=MeResponse)
async def login(
    body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> MeResponse:
    settings = get_settings()
    email = body.email.strip().lower()
    by_email, by_ip = _identifiers(request, email)

    if await _locked_out(db, request, email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed attempts. Try again in {settings.login_lockout_minutes} minutes.",
            headers={"Retry-After": str(settings.login_lockout_minutes * 60)},
        )

    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None or user.deleted_at is not None or not verify_password(body.password, user.password_hash):
        db.add(LoginAttempt(identifier=by_email, successful=False))
        db.add(LoginAttempt(identifier=by_ip, successful=False))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Email or password is incorrect."
        )

    if user.email_verified_at is None:
        # The password was correct, so this is not a brute-force signal.
        await _issue_verification(db, user)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="email_not_verified")

    await db.execute(delete(LoginAttempt).where(LoginAttempt.identifier.in_([by_email, by_ip])))
    db.add(LoginAttempt(identifier=by_email, successful=True))
    user.last_login_at = now_utc()
    await _issue_session(db, user, request, response)

    row = (
        await db.execute(
            select(Membership, Workspace)
            .join(Workspace, Workspace.id == Membership.workspace_id)
            .where(Membership.user_id == user.id)
            .order_by(Membership.created_at)
            .limit(1)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No workspace membership")
    membership, workspace = row
    await record_audit(
        db, action="account.login", actor_user_id=user.id, workspace_id=workspace.id, subject=user.email
    )
    await db.commit()
    return await _me(
        db, AuthContext(user=user, session=AuthSession(), workspace=workspace, role=membership.role)
    )


@router.post("/refresh", response_model=MeResponse)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> MeResponse:
    raw = bearer_or_cookie(request, REFRESH_COOKIE)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    session = (
        await db.execute(select(AuthSession).where(AuthSession.refresh_token_hash == token_fingerprint(raw)))
    ).scalar_one_or_none()
    if session is None or session.revoked_at is not None or session.expires_at <= now_utc():
        _clear_auth_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    user = (await db.execute(select(User).where(User.id == session.user_id))).scalar_one()
    rotated = new_opaque_token()
    session.refresh_token_hash = token_fingerprint(rotated)
    session.last_seen_at = now_utc()
    _set_auth_cookies(response, create_access_token(user.id, session.id, user.email), rotated)

    row = (
        await db.execute(
            select(Membership, Workspace)
            .join(Workspace, Workspace.id == Membership.workspace_id)
            .where(Membership.user_id == user.id)
            .order_by(Membership.created_at)
            .limit(1)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No workspace membership")
    membership, workspace = row
    await db.commit()
    return await _me(db, AuthContext(user=user, session=session, workspace=workspace, role=membership.role))


@router.get("/me", response_model=MeResponse)
async def me(auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)) -> MeResponse:
    auth.session.last_seen_at = now_utc()
    await db.commit()
    return await _me(db, auth)


@router.patch("/me", response_model=MeResponse)
async def update_profile(
    body: ProfileUpdate, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> MeResponse:
    auth.user.display_name = body.display_name.strip()
    auth.user.timezone = body.timezone
    await db.commit()
    return await _me(db, auth)


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> list[SessionOut]:
    rows = (
        await db.execute(
            select(AuthSession)
            .where(
                AuthSession.user_id == auth.user.id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now_utc(),
            )
            .order_by(AuthSession.created_at.desc())
        )
    ).scalars()
    return [
        SessionOut(
            id=s.id,
            user_agent=s.user_agent or "Unknown device",
            created_at=s.created_at,
            last_seen_at=s.last_seen_at,
            expires_at=s.expires_at,
            current=s.id == auth.session.id,
        )
        for s in rows
    ]


@router.post("/logout")
async def logout(
    response: Response, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    auth.session.revoked_at = now_utc()
    auth.session.revoked_reason = "logout"
    await db.commit()
    _clear_auth_cookies(response)
    return {"status": "signed_out"}


@router.post("/logout-all")
async def logout_all(
    response: Response, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    sessions = (
        await db.execute(
            select(AuthSession).where(AuthSession.user_id == auth.user.id, AuthSession.revoked_at.is_(None))
        )
    ).scalars()
    revoked = 0
    for s in sessions:
        s.revoked_at = now_utc()
        s.revoked_reason = "logout_all"
        revoked += 1
    await record_audit(
        db,
        action="account.logout_all",
        actor_user_id=auth.user.id,
        workspace_id=auth.workspace.id,
        detail={"revoked": revoked},
    )
    await db.commit()
    _clear_auth_cookies(response)
    return {"status": "all_sessions_revoked", "revoked": str(revoked)}


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(body: EmailRequest, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    settings = get_settings()
    email = body.email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is not None and user.deleted_at is None:
        token = new_opaque_token()
        db.add(
            AuthToken(
                user_id=user.id,
                kind="password_reset",
                token_hash=token_fingerprint(token),
                expires_at=now_utc() + timedelta(hours=settings.reset_token_hours),
            )
        )
        await queue_email(
            db,
            to_email=email,
            kind="password_reset",
            subject="Reset your password",
            body_text=(
                "Use this link to choose a new password. It expires in "
                f"{settings.reset_token_hours} hour. If you did not ask for this, ignore it.\n"
            ),
            action_url=action_url(f"/reset-password?token={token}"),
        )
        await db.commit()
    return {
        "status": "accepted",
        "message": "If that address has an account, a reset link is waiting in the development outbox.",
    }


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    user = await _consume_token(db, body.token, "password_reset")
    user.password_hash = hash_password(body.password)
    if user.email_verified_at is None:
        user.email_verified_at = now_utc()

    sessions = (
        await db.execute(
            select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        )
    ).scalars()
    for s in sessions:
        s.revoked_at = now_utc()
        s.revoked_reason = "password_reset"
    await db.execute(delete(LoginAttempt).where(LoginAttempt.identifier == f"email:{user.email}"))
    await record_audit(db, action="account.password_reset", actor_user_id=user.id, subject=user.email)
    await db.commit()
    _clear_auth_cookies(response)
    return {"status": "password_reset", "email": user.email}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    session = (
        await db.execute(
            select(AuthSession).where(AuthSession.id == session_id, AuthSession.user_id == auth.user.id)
        )
    ).scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.revoked_at = now_utc()
    session.revoked_reason = "revoked"
    await db.commit()
    return {"status": "revoked"}
