from httpx import AsyncClient

from server import app

FORBIDDEN_ROUTE_FRAGMENTS = ("send", "value-score", "value_score", "book", "offer", "billing", "scrape")


async def test_health_reports_the_configured_database(client: AsyncClient) -> None:
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["milestone"] == 2


async def test_meta_declares_synthetic_only_and_locked_flags(client: AsyncClient) -> None:
    body = (await client.get("/api/meta")).json()
    assert body["synthetic_data_only"] is True
    assert body["gate"] == "initial private prototype"
    assert body["email_delivery"] == "suppressed_no_provider"
    assert body["flags"]["apple_sign_in"] == "locked_off"
    assert body["flags"]["portal_connectors"] == "locked_off"
    assert body["flags"]["inbound_email"] == "locked_off"
    assert body["flags"]["google_sign_in"] == "off"
    assert body["flags"]["ai_extraction"] == "off"
    assert body["flags"]["email_delivery"] == "off"
    assert "value_score" not in body["flags"]


def test_all_routes_are_under_api_prefix() -> None:
    for route in app.routes:
        path = getattr(route, "path", "")
        if path in ("/api/openapi.json",):
            continue
        assert path.startswith("/api/"), path


def test_no_forbidden_pathways_exist() -> None:
    for route in app.routes:
        path = getattr(route, "path", "").lower()
        for fragment in FORBIDDEN_ROUTE_FRAGMENTS:
            assert fragment not in path, f"forbidden pathway {fragment!r} found in route {path}"


async def test_correlation_id_header_is_returned(client: AsyncClient) -> None:
    r = await client.get("/api/health", headers={"x-correlation-id": "abc123"})
    assert r.headers["x-correlation-id"] == "abc123"
    r2 = await client.get("/api/health")
    assert len(r2.headers["x-correlation-id"]) == 32


async def test_cross_origin_writes_are_rejected(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "Prototype2026pass"},
        headers={"origin": "https://attacker.example"},
    )
    assert r.status_code == 403
