"""Security regression: /api/dev/* must be unreachable outside explicitly opted-in envs.

Test matrix
-----------
1. Unauthenticated caller to /api/dev/outbox -> 404 when DEV_ROUTES_ENABLED=false
2. Authenticated ordinary user -> 404 when DEV_ROUTES_ENABLED=false
3. /api/dev/load-demo-properties -> 404 when DEV_ROUTES_ENABLED=false
4. No token or email is exposed when dev routes are disabled
5. Dev routes remain accessible within the in-process test runner (DEV_ROUTES_ENABLED=true)
"""

import os
from contextlib import contextmanager
from collections.abc import Iterator

import pytest
from httpx import AsyncClient

from tests.conftest import login, register_and_verify, unique_email


@contextmanager
def dev_routes_disabled() -> Iterator[None]:
    """Temporarily disable DEV_ROUTES_ENABLED for the duration of the block."""
    original = os.environ.get("DEV_ROUTES_ENABLED")
    os.environ["DEV_ROUTES_ENABLED"] = "false"
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("DEV_ROUTES_ENABLED", None)
        else:
            os.environ["DEV_ROUTES_ENABLED"] = original


# ── 1. Unauthenticated caller cannot read the outbox ──────────────────────────

async def test_outbox_unauthenticated_returns_404_when_disabled(client: AsyncClient) -> None:
    with dev_routes_disabled():
        r = await client.get("/api/dev/outbox")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


# ── 2. Authenticated ordinary user cannot read the outbox ─────────────────────

async def test_outbox_authenticated_user_returns_404_when_disabled(client: AsyncClient) -> None:
    email = unique_email("sec-auth")
    await register_and_verify(client, email)
    await login(client, email)
    with dev_routes_disabled():
        r = await client.get("/api/dev/outbox")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


# ── 3. load-demo-properties returns 404 when disabled ─────────────────────────

async def test_load_demo_returns_404_when_disabled(client: AsyncClient) -> None:
    import uuid

    email = unique_email("sec-demo")
    await register_and_verify(client, email)
    await login(client, email)
    with dev_routes_disabled():
        r = await client.post(
            "/api/dev/load-demo-properties",
            json={"journey_id": str(uuid.uuid4())},
        )
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"


# ── 4. No token or email is exposed in the 404 response ───────────────────────

async def test_outbox_404_response_contains_no_token_or_email(client: AsyncClient) -> None:
    email = unique_email("sec-noleak")
    # Signup so there IS an outbox record for this address
    await client.post(
        "/api/auth/signup",
        json={"email": email, "password": "Prototype2026pass", "display_name": "NoLeak"},
    )
    with dev_routes_disabled():
        r = await client.get("/api/dev/outbox", params={"email": email})
    assert r.status_code == 404
    body_text = r.text.lower()
    # The response must not contain the queried address or any token fragment
    assert email not in body_text
    assert "token=" not in body_text
    assert "verify" not in body_text or "Not found" in r.text  # detail is generic


# ── 5. Dev routes ARE accessible inside the in-process test runner ─────────────

async def test_outbox_accessible_when_dev_routes_enabled(client: AsyncClient) -> None:
    """Proves that DEV_ROUTES_ENABLED=true (set in conftest) keeps tests working."""
    email = unique_email("sec-local")
    await client.post(
        "/api/auth/signup",
        json={"email": email, "password": "Prototype2026pass", "display_name": "Local"},
    )
    # conftest already sets DEV_ROUTES_ENABLED=true so this should work
    r = await client.get("/api/dev/outbox", params={"email": email})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1
    assert r.json()[0]["to_email"] == email


# ── 6. Auth flow still completes end-to-end (no regression) ───────────────────

async def test_register_and_verify_still_works_in_test_runner(client: AsyncClient) -> None:
    email = unique_email("sec-e2e")
    await register_and_verify(client, email)
    body = await login(client, email)
    assert body["user"]["email"] == email  # type: ignore[index]
