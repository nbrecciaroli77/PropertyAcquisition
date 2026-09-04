"""Retest of iteration_2 fixes over the public ingress: login lockout keying, marker cookie, session cap."""

import os
import subprocess
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

QA_EMAIL = "lockout-drills@propertyacquisition-demo.com"
QA_PASSWORD = "Prototype2026pass"
OTHER_EMAIL = "other@propertyacquisition-demo.com"
OTHER_PASSWORD = "Prototype2026pass"
OWNER_EMAIL = "owner@propertyacquisition-demo.com"
OWNER_PASSWORD = "Prototype2026pass"


def unlock(email: str) -> None:
    subprocess.run(
        ["python", "-m", "scripts.unlock", email], cwd="/app/backend", capture_output=True, check=False
    )


def rand_ip() -> str:
    n = uuid.uuid4().int
    return f"203.0.{n % 250 + 1}.{(n >> 8) % 250 + 1}"


def post_login(email: str, password: str, xff: str, session: requests.Session | None = None):
    s = session or requests.Session()
    return s.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        headers={"X-Forwarded-For": xff, "Content-Type": "application/json"},
        timeout=60,
    )


# --- FIX 1: login lockout survives the ingress -------------------------------------------------
class TestLockout:
    def teardown_method(self):
        unlock(QA_EMAIL)
        unlock(OTHER_EMAIL)

    def test_six_wrong_passwords_same_ip_lock_out(self):
        unlock(QA_EMAIL)
        ip = rand_ip()
        statuses = [post_login(QA_EMAIL, "WrongPassword123", ip).status_code for _ in range(6)]
        assert statuses[:5] == [401] * 5, statuses
        assert statuses[5] == 429, statuses

        resp = post_login(QA_EMAIL, "WrongPassword123", ip)
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") is not None
        assert int(resp.headers["Retry-After"]) > 0
        assert "Too many failed attempts" in resp.json().get("detail", "")

    def test_lockout_triggers_with_rotating_forwarded_for(self):
        unlock(QA_EMAIL)
        statuses = [post_login(QA_EMAIL, "WrongPassword123", rand_ip()).status_code for _ in range(6)]
        assert statuses[:5] == [401] * 5, statuses
        assert statuses[5] == 429, statuses

    def test_no_collateral_lockout_for_other_account(self):
        unlock(QA_EMAIL)
        unlock(OTHER_EMAIL)
        for _ in range(6):
            post_login(QA_EMAIL, "WrongPassword123", rand_ip())
        # Different email, fresh IP: must not be locked out.
        resp = post_login(OTHER_EMAIL, "AlsoWrongPassword123", rand_ip())
        assert resp.status_code == 401, resp.text[:300]
        # And the correct password for the other account still works.
        ok = post_login(OTHER_EMAIL, OTHER_PASSWORD, rand_ip())
        assert ok.status_code == 200, ok.text[:300]

    def test_correct_password_refused_during_lockout(self):
        unlock(QA_EMAIL)
        for _ in range(6):
            post_login(QA_EMAIL, "WrongPassword123", rand_ip())
        resp = post_login(QA_EMAIL, QA_PASSWORD, rand_ip())
        assert resp.status_code == 429, resp.text[:300]
        assert resp.headers.get("Retry-After") is not None

    def test_unlock_script_restores_access(self):
        unlock(QA_EMAIL)
        for _ in range(6):
            post_login(QA_EMAIL, "WrongPassword123", rand_ip())
        assert post_login(QA_EMAIL, QA_PASSWORD, rand_ip()).status_code == 429
        unlock(QA_EMAIL)
        resp = post_login(QA_EMAIL, QA_PASSWORD, rand_ip())
        assert resp.status_code == 200, resp.text[:300]
        assert resp.json()["user"]["email"] == QA_EMAIL


# --- FIX 4: readable marker cookie ------------------------------------------------------------
class TestMarkerCookie:
    def test_marker_cookie_set_on_login_and_cleared_on_logout(self):
        s = requests.Session()
        resp = post_login(OWNER_EMAIL, OWNER_PASSWORD, rand_ip(), session=s)
        assert resp.status_code == 200, resp.text[:300]
        set_cookies = resp.headers.get("set-cookie", "") + " ".join(
            v for k, v in resp.raw.headers.items() if k.lower() == "set-cookie"
        )
        assert "pa_signed_in=1" in set_cookies, set_cookies
        marker_line = [
            v
            for k, v in resp.raw.headers.items()
            if k.lower() == "set-cookie" and v.startswith("pa_signed_in=")
        ]
        assert marker_line, "no pa_signed_in Set-Cookie header"
        assert "HttpOnly" not in marker_line[0], marker_line[0]
        assert s.cookies.get("pa_signed_in") == "1"
        assert s.cookies.get("pa_access") is not None
        assert s.cookies.get("pa_refresh") is not None

        me = s.get(f"{API}/auth/me", timeout=60)
        assert me.status_code == 200
        assert me.json()["user"]["email"] == OWNER_EMAIL

        out = s.post(f"{API}/auth/logout", timeout=60)
        assert out.status_code == 200
        assert not s.cookies.get("pa_signed_in")
        assert s.get(f"{API}/auth/me", timeout=60).status_code == 401

    def test_anonymous_me_is_401_without_marker(self):
        resp = requests.get(f"{API}/auth/me", timeout=60)
        assert resp.status_code == 401


# --- FIX 6: session cap of 10 -----------------------------------------------------------------
class TestSessionCap:
    def test_sessions_capped_at_ten_and_current_marked(self):
        sessions = []
        for _ in range(12):
            s = requests.Session()
            r = post_login(OWNER_EMAIL, OWNER_PASSWORD, rand_ip(), session=s)
            assert r.status_code == 200, r.text[:200]
            sessions.append(s)

        latest = sessions[-1]
        listing = latest.get(f"{API}/auth/sessions", timeout=60)
        assert listing.status_code == 200
        rows = listing.json()
        assert len(rows) <= 10, f"expected <=10 live sessions, got {len(rows)}"
        current = [r for r in rows if r["current"]]
        assert len(current) == 1, rows
        assert all("_id" not in r for r in rows)

        # Oldest sessions were revoked by the cap.
        assert sessions[0].get(f"{API}/auth/me", timeout=60).status_code == 401

        # Revoking another session still works.
        other = [r for r in rows if not r["current"]][0]
        deleted = latest.delete(f"{API}/auth/sessions/{other['id']}", timeout=60)
        assert deleted.status_code == 200
        after = latest.get(f"{API}/auth/sessions", timeout=60).json()
        assert other["id"] not in [r["id"] for r in after]

        for s in sessions:
            try:
                s.post(f"{API}/auth/logout", timeout=30)
            except Exception:
                pass


@pytest.fixture(scope="session", autouse=True)
def final_unlock():
    yield
    unlock(QA_EMAIL)
    unlock(OTHER_EMAIL)
    unlock(OWNER_EMAIL)
