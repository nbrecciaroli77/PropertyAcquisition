import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, update

# Enable dev routes for the in-process test runner BEFORE load_dotenv so that
# the .env value (DEV_ROUTES_ENABLED=false) does not override this.
os.environ.setdefault("DEV_ROUTES_ENABLED", "true")
# Allow signup in test runs regardless of the production SIGNUP_ENABLED=false gate.
os.environ.setdefault("SIGNUP_ENABLED", "true")

load_dotenv()

from app.db.base import dispose_engine, get_sessionmaker  # noqa: E402
from app.db.models import (  # noqa: E402
    AuditEvent,
    AuthSession,
    AuthToken,
    BriefVersion,
    Journey,
    LoginAttempt,
    Membership,
    OutboxMessage,
    User,
    Workspace,
)
from server import app  # noqa: E402

TEST_EMAIL_DOMAIN = "m2tests.pa-prototype.com"


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@{TEST_EMAIL_DOMAIN}"


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://property-find-1.preview.emergentagent.com",
    ) as c:
        yield c


@pytest_asyncio.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://property-find-1.preview.emergentagent.com",
    ) as c:
        yield c


@pytest_asyncio.fixture(autouse=True, scope="session")
async def _cleanup() -> AsyncIterator[None]:
    yield
    async with get_sessionmaker()() as db:
        users = (
            (await db.execute(select(User).where(User.email.like(f"%@{TEST_EMAIL_DOMAIN}")))).scalars().all()
        )
        ids = [u.id for u in users]
        workspaces = (
            (await db.execute(select(Workspace).where(Workspace.owner_user_id.in_(ids)))).scalars().all()
            if ids
            else []
        )
        ws_ids = [w.id for w in workspaces]
        if ws_ids:
            await db.execute(
                update(Journey).where(Journey.workspace_id.in_(ws_ids)).values(current_version_id=None)
            )
            await db.execute(delete(BriefVersion).where(BriefVersion.workspace_id.in_(ws_ids)))
            await db.execute(delete(Journey).where(Journey.workspace_id.in_(ws_ids)))
        if ids:
            await db.execute(delete(AuditEvent).where(AuditEvent.actor_user_id.in_(ids)))
            await db.execute(delete(AuthSession).where(AuthSession.user_id.in_(ids)))
            await db.execute(delete(AuthToken).where(AuthToken.user_id.in_(ids)))
            await db.execute(delete(Membership).where(Membership.user_id.in_(ids)))
        if ws_ids:
            await db.execute(delete(Workspace).where(Workspace.id.in_(ws_ids)))
        await db.execute(delete(OutboxMessage).where(OutboxMessage.to_email.like(f"%@{TEST_EMAIL_DOMAIN}")))
        await db.execute(delete(LoginAttempt).where(LoginAttempt.identifier.like(f"%@{TEST_EMAIL_DOMAIN}")))
        if ids:
            await db.execute(delete(User).where(User.id.in_(ids)))
        await db.commit()
    await dispose_engine()


async def register_and_verify(client: AsyncClient, email: str, password: str = "Prototype2026pass") -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "display_name": "Test owner"},
    )
    assert r.status_code == 201, r.text
    outbox = (await client.get("/api/dev/outbox", params={"email": email})).json()
    verify = next(m for m in outbox if m["kind"] == "verify_email")
    token = verify["action_url"].split("token=")[1]
    r = await client.post("/api/auth/verify-email", json={"token": token})
    assert r.status_code == 200, r.text


async def login(client: AsyncClient, email: str, password: str = "Prototype2026pass") -> dict[str, object]:
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    body: dict[str, object] = r.json()
    return body


@pytest.fixture
def password() -> str:
    return "Prototype2026pass"
