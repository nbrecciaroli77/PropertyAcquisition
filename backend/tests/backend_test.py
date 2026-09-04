"""Milestone 1 backend API tests against the public preview URL.

Modules covered: app/api/system.py (/api/health, /api/meta), correlation-id middleware,
and route surface boundaries (no other /api routes should exist).
"""

import os

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL is missing from env and /app/frontend/.env")
BASE_URL = base_url.rstrip("/")


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# --- /api/health ---
class TestHealth:
    def test_health_ok(self, client):
        r = client.get(f"{BASE_URL}/api/health", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert data["status"] == "ok"
        assert data["milestone"] == 1
        assert data["database"] == "not_configured"

    def test_health_correlation_id_generated(self, client):
        r = client.get(f"{BASE_URL}/api/health", timeout=30)
        assert r.headers.get("x-correlation-id")

    def test_health_correlation_id_echoed(self, client):
        r = client.get(f"{BASE_URL}/api/health", headers={"x-correlation-id": "TEST-cid-123"}, timeout=30)
        assert r.headers.get("x-correlation-id") == "TEST-cid-123"


# --- /api/meta ---
class TestMeta:
    @pytest.fixture(scope="class")
    def meta(self, client):
        r = client.get(f"{BASE_URL}/api/meta", timeout=30)
        assert r.status_code == 200, r.text[:300]
        return r.json()

    def test_meta_core_fields(self, meta):
        assert meta["milestone"] == 1
        assert meta["synthetic_data_only"] is True
        assert isinstance(meta["app_name"], str) and meta["app_name"]
        assert isinstance(meta["gate"], str)
        assert isinstance(meta["working_name_status"], str)

    @pytest.mark.parametrize(
        "flag,expected",
        [
            ("apple_sign_in", "locked_off"),
            ("google_sign_in", "off"),
            ("ai_extraction", "off"),
            ("email_delivery", "off"),
            ("inbound_email", "locked_off"),
            ("portal_connectors", "locked_off"),
        ],
    )
    def test_meta_flags(self, meta, flag, expected):
        assert meta["flags"][flag] == expected

    def test_no_value_score_anywhere(self, client):
        r = client.get(f"{BASE_URL}/api/meta", timeout=30)
        assert "value_score" not in r.text
        assert "value_score" not in r.json()["flags"]

    def test_meta_correlation_id(self, client):
        r = client.get(f"{BASE_URL}/api/meta", headers={"x-correlation-id": "meta-cid"}, timeout=30)
        assert r.headers.get("x-correlation-id") == "meta-cid"


# --- Route surface boundaries ---
class TestRouteSurface:
    @pytest.mark.parametrize(
        "path",
        ["/api/send", "/api/properties", "/api/tasks", "/api/agents", "/api/sources", "/api/status"],
    )
    def test_unknown_api_routes_404(self, client, path):
        r = client.get(f"{BASE_URL}{path}", timeout=30)
        assert r.status_code == 404, f"{path} -> {r.status_code}"

    def test_post_health_not_allowed(self, client):
        r = client.post(f"{BASE_URL}/api/health", json={}, timeout=30)
        assert r.status_code in (404, 405)

    def test_openapi_route_surface(self, client):
        r = client.get(f"{BASE_URL}/api/openapi.json", timeout=30)
        if r.status_code != 200:
            pytest.skip("openapi not exposed through ingress")
        paths = set(r.json().get("paths", {}))
        assert paths == {"/api/health", "/api/meta"}, paths
