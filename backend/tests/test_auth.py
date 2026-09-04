"""Milestone 2 account foundations: signup, verification, login, sessions, reset."""

from httpx import AsyncClient

from tests.conftest import login, register_and_verify, unique_email

PASSWORD = "Prototype2026pass"


async def test_signup_is_verification_pending_and_never_signs_in(client: AsyncClient) -> None:
    email = unique_email("pending")
    r = await client.post(
        "/api/auth/signup", json={"email": email, "password": PASSWORD, "display_name": "Pending"}
    )
    assert r.status_code == 201
    assert r.json()["status"] == "verification_pending"
    assert "pa_access" not in r.cookies

    denied = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert denied.status_code == 403
    assert denied.json()["detail"] == "email_not_verified"


async def test_outbox_holds_suppressed_verification_email(client: AsyncClient) -> None:
    email = unique_email("outbox")
    await client.post(
        "/api/auth/signup", json={"email": email, "password": PASSWORD, "display_name": "Outbox"}
    )
    messages = (await client.get("/api/dev/outbox", params={"email": email})).json()
    assert messages, "verification email should be queued"
    assert messages[0]["delivery_state"] == "suppressed_no_provider"
    assert "/verify-email?token=" in messages[0]["action_url"]


async def test_verify_then_login_creates_workspace_and_session(client: AsyncClient) -> None:
    email = unique_email("verified")
    await register_and_verify(client, email)
    body = await login(client, email)
    assert body["user"]["email"] == email  # type: ignore[index]
    assert body["workspace"]["role"] == "owner"  # type: ignore[index]

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["session_count"] >= 1


async def test_weak_password_is_rejected(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup", json={"email": unique_email("weak"), "password": "short1", "display_name": "Weak"}
    )
    assert r.status_code == 422


async def test_verification_token_is_single_use(client: AsyncClient) -> None:
    email = unique_email("single")
    await client.post(
        "/api/auth/signup", json={"email": email, "password": PASSWORD, "display_name": "Single"}
    )
    outbox = (await client.get("/api/dev/outbox", params={"email": email})).json()
    token = outbox[0]["action_url"].split("token=")[1]
    assert (await client.post("/api/auth/verify-email", json={"token": token})).status_code == 200
    assert (await client.post("/api/auth/verify-email", json={"token": token})).status_code == 400


async def test_logout_all_revokes_the_current_access_token(client: AsyncClient) -> None:
    email = unique_email("logoutall")
    await register_and_verify(client, email)
    await login(client, email)
    access = client.cookies.get("pa_access")
    assert access is not None

    assert (await client.post("/api/auth/logout-all")).status_code == 200
    replay = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert replay.status_code == 401


async def test_password_reset_revokes_sessions_and_sets_new_password(client: AsyncClient) -> None:
    email = unique_email("reset")
    await register_and_verify(client, email)
    await login(client, email)
    access = client.cookies.get("pa_access")

    assert (await client.post("/api/auth/forgot-password", json={"email": email})).status_code == 202
    outbox = (await client.get("/api/dev/outbox", params={"email": email})).json()
    reset = next(m for m in outbox if m["kind"] == "password_reset")
    token = reset["action_url"].split("token=")[1]

    new_password = "Rotated2026pass"
    r = await client.post("/api/auth/reset-password", json={"token": token, "password": new_password})
    assert r.status_code == 200

    stale = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert stale.status_code == 401
    assert (
        await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    ).status_code == 401
    await login(client, email, new_password)


async def test_forgot_password_does_not_disclose_unknown_accounts(client: AsyncClient) -> None:
    r = await client.post("/api/auth/forgot-password", json={"email": unique_email("nobody")})
    assert r.status_code == 202


async def test_brute_force_lockout_after_five_failures(client: AsyncClient) -> None:
    email = unique_email("lockout")
    await register_and_verify(client, email)
    for _ in range(5):
        assert (
            await client.post("/api/auth/login", json={"email": email, "password": "Wrong2026pass"})
        ).status_code == 401
    locked = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert locked.status_code == 429


async def test_unauthenticated_requests_are_rejected(client: AsyncClient) -> None:
    fresh = await client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert fresh.status_code == 401
    assert (
        await client.get("/api/journeys", headers={"Authorization": "Bearer not-a-token"})
    ).status_code == 401
