from fastapi.testclient import TestClient

from server import app

client = TestClient(app)

FORBIDDEN_ROUTE_FRAGMENTS = ("send", "value-score", "value_score", "book", "offer", "billing", "scrape")


def test_health_reports_no_database_in_milestone_1() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "not_configured"


def test_meta_declares_synthetic_only_and_locked_flags() -> None:
    body = client.get("/api/meta").json()
    assert body["synthetic_data_only"] is True
    assert body["gate"] == "initial private prototype"
    assert body["flags"]["apple_sign_in"] == "locked_off"
    assert body["flags"]["portal_connectors"] == "locked_off"
    assert body["flags"]["inbound_email"] == "locked_off"
    assert body["flags"]["google_sign_in"] == "off"
    assert body["flags"]["ai_extraction"] == "off"
    assert body["flags"]["email_delivery"] == "off"
    assert "value_score" not in body["flags"]


def test_all_routes_are_under_api_prefix() -> None:
    paths = [getattr(r, "path", "") for r in app.routes]
    for p in paths:
        if p in ("/api/openapi.json",):
            continue
        assert p.startswith("/api/"), p


def test_no_forbidden_pathways_exist() -> None:
    paths = [getattr(r, "path", "").lower() for r in app.routes]
    for p in paths:
        for frag in FORBIDDEN_ROUTE_FRAGMENTS:
            assert frag not in p, f"forbidden pathway {frag!r} found in route {p}"


def test_correlation_id_header_is_returned() -> None:
    r = client.get("/api/health", headers={"x-correlation-id": "abc123"})
    assert r.headers["x-correlation-id"] == "abc123"
    r2 = client.get("/api/health")
    assert len(r2.headers["x-correlation-id"]) == 32
