"""Rate limiting must survive the ingress: the socket peer address rotates between proxy pods."""

from httpx import AsyncClient

from tests.conftest import register_and_verify, unique_email

PASSWORD = "Prototype2026pass"


async def test_lockout_holds_when_the_client_ip_rotates(client: AsyncClient) -> None:
    email = unique_email("rotating")
    await register_and_verify(client, email)

    for index in range(5):
        response = await client.post(
            "/api/auth/login",
            json={"email": email, "password": "Wrong2026pass"},
            headers={"x-forwarded-for": f"10.208.134.{70 + index}, 172.16.0.1"},
        )
        assert response.status_code == 401

    locked = await client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
        headers={"x-forwarded-for": "10.208.134.99"},
    )
    assert locked.status_code == 429
    assert locked.headers["Retry-After"] == "900"


async def test_one_email_lockout_does_not_lock_another_account(client: AsyncClient) -> None:
    victim = unique_email("victim")
    bystander = unique_email("bystander")
    await register_and_verify(client, victim)
    await register_and_verify(client, bystander)

    for _ in range(5):
        await client.post("/api/auth/login", json={"email": victim, "password": "Wrong2026pass"})

    assert (
        await client.post("/api/auth/login", json={"email": victim, "password": PASSWORD})
    ).status_code == 429
    ok = await client.post("/api/auth/login", json={"email": bystander, "password": PASSWORD})
    assert ok.status_code == 200


async def test_login_sets_a_readable_marker_cookie_and_logout_clears_it(client: AsyncClient) -> None:
    email = unique_email("marker")
    await register_and_verify(client, email)

    login = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200
    assert client.cookies.get("pa_signed_in") == "1"
    assert "HttpOnly" not in login.headers.get("set-cookie", "").split("pa_signed_in")[-1].split(",")[0]

    await client.post("/api/auth/logout")
    assert client.cookies.get("pa_signed_in") is None


async def test_sessions_are_capped_so_the_list_stays_readable(client: AsyncClient) -> None:
    email = unique_email("cap")
    await register_and_verify(client, email)
    for _ in range(12):
        assert (
            await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        ).status_code == 200

    sessions = (await client.get("/api/auth/sessions")).json()
    assert len(sessions) <= 10
    assert sum(1 for s in sessions if s["current"]) == 1
