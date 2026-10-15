import itertools
import os
import uuid
from collections.abc import AsyncIterator
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, or_, select

# Enable dev routes for the in-process test runner BEFORE load_dotenv so that
# the .env value (DEV_ROUTES_ENABLED=false) does not override this.
os.environ.setdefault("DEV_ROUTES_ENABLED", "true")
# Allow signup in test runs regardless of the production SIGNUP_ENABLED=false gate.
os.environ.setdefault("SIGNUP_ENABLED", "true")

load_dotenv()

# In-process tests write synthetic rows; they must target a disposable local database.
_DB_HOST = urlparse(os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")).hostname
if _DB_HOST not in ("127.0.0.1", "localhost") and os.environ.get("PA_TEST_ALLOW_REMOTE_DB") != "1":
    pytest.exit(f"Refusing to run in-process tests against non-disposable database host {_DB_HOST!r}.", returncode=4)

from app.db.base import dispose_engine, get_sessionmaker  # noqa: E402
from app.db.models import LoginAttempt, OutboxMessage, User, Workspace  # noqa: E402
from server import app  # noqa: E402

TEST_EMAIL_DOMAIN = "m2tests.pa-prototype.com"

# Exact identities created by this test session. Cleanup never matches by email domain.
_TRACKED_EMAILS: set[str] = set()
_TRACKED_USER_IDS: set[uuid.UUID] = set()
_TRACKED_IPS: set[str] = set()
_ip_counter = itertools.count(1)


def track_email(email: str) -> str:
    _TRACKED_EMAILS.add(email.strip().lower())
    return email


def track_user_id(user_id: uuid.UUID) -> uuid.UUID:
    _TRACKED_USER_IDS.add(user_id)
    return user_id


def track_ip(ip: str) -> str:
    _TRACKED_IPS.add(ip)
    return ip


def unique_email(prefix: str = "user") -> str:
    return track_email(f"{prefix}-{uuid.uuid4().hex[:10]}@{TEST_EMAIL_DOMAIN}")


def _client_ip() -> str:
    n = next(_ip_counter)
    ip = f"198.18.{(n // 250) % 250}.{n % 250 + 1}"
    _TRACKED_IPS.add(ip)
    return ip


async def purge_tracked() -> None:
    """Deletes only the exact users/workspaces this session created (FK cascades remove children)."""
    if not (_TRACKED_EMAILS or _TRACKED_USER_IDS or _TRACKED_IPS):
        return
    async with get_sessionmaker()() as db:
        emails = sorted(_TRACKED_EMAILS)
        ids = set(_TRACKED_USER_IDS)
        if emails:
            ids |= set((await db.execute(select(User.id).where(User.email.in_(emails)))).scalars().all())
        if ids:
            await db.execute(delete(Workspace).where(Workspace.owner_user_id.in_(ids)))
            await db.execute(delete(User).where(User.id.in_(ids)))
        identifiers = [f"email:{e}" for e in emails] + [f"ip:{ip}" for ip in _TRACKED_IPS]
        if identifiers:
            await db.execute(delete(LoginAttempt).where(LoginAttempt.identifier.in_(identifiers)))
        if emails:
            await db.execute(delete(OutboxMessage).where(or_(OutboxMessage.to_email.in_(emails))))
        await db.commit()
    _TRACKED_EMAILS.clear()
    _TRACKED_USER_IDS.clear()
    _TRACKED_IPS.clear()


def _new_client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://property-find-1.preview.emergentagent.com",
        headers={"X-Forwarded-For": _client_ip()},
    )


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with _new_client() as c:
        yield c


@pytest_asyncio.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    async with _new_client() as c:
        yield c


@pytest_asyncio.fixture(autouse=True)
async def _per_test_cleanup() -> AsyncIterator[None]:
    # Runs after every test, including failed ones.
    yield
    await purge_tracked()


@pytest_asyncio.fixture(autouse=True, scope="session")
async def _session_cleanup() -> AsyncIterator[None]:
    yield
    await purge_tracked()
    await dispose_engine()


async def register_and_verify(client: AsyncClient, email: str, password: str = "Prototype2026pass") -> None:
    track_email(email)
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
