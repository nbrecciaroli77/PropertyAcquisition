"""Bug-fix verification: 401 -> refresh -> replay flow (iteration_5).

Covers backend side of the fix:
- login sets pa_access/pa_refresh/pa_signed_in cookies
- removing pa_access -> /auth/me returns 401
- POST /auth/refresh with only pa_refresh -> 200 + rotated cookies
- old refresh token is rejected afterwards (401)
- POST /journeys works with the new access cookie
"""
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
OWNER_EMAIL = "owner@propertyacquisition-demo.com"
OWNER_PASSWORD = "Prototype2026pass"
TIMEOUT = 45


@pytest.fixture(scope="module")
def logged_in_jar():
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    names = {c.name for c in s.cookies}
    assert {"pa_access", "pa_refresh", "pa_signed_in"}.issubset(names), names
    return s


def test_login_sets_all_three_cookies(logged_in_jar):
    names = {c.name for c in logged_in_jar.cookies}
    assert "pa_access" in names
    assert "pa_refresh" in names
    assert "pa_signed_in" in names


def test_me_without_access_returns_401_then_refresh_rotates(logged_in_jar):
    s = logged_in_jar
    # Preserve refresh value to test rotation.
    old_refresh = next(c.value for c in s.cookies if c.name == "pa_refresh")
    # Simulate expired access token by dropping only pa_access.
    s.cookies.set("pa_access", "", domain=next(c.domain for c in s.cookies if c.name == "pa_access"))
    # Clean out the empty cookie so it isn't sent as a stale value.
    s.cookies.clear(domain=next(c.domain for c in s.cookies if c.name == "pa_refresh"), path="/", name="pa_access")

    r = s.get(f"{BASE_URL}/api/auth/me", timeout=TIMEOUT)
    assert r.status_code == 401, r.text

    r2 = s.post(f"{BASE_URL}/api/auth/refresh", timeout=TIMEOUT)
    assert r2.status_code == 200, r2.text
    names = {c.name for c in s.cookies}
    assert "pa_access" in names
    new_refresh = next(c.value for c in s.cookies if c.name == "pa_refresh")
    assert new_refresh and new_refresh != old_refresh, "refresh token should rotate"

    # Old refresh token must be rejected.
    reuse = requests.Session()
    reuse.cookies.set("pa_refresh", old_refresh)
    r3 = reuse.post(f"{BASE_URL}/api/auth/refresh", timeout=TIMEOUT)
    assert r3.status_code == 401, r3.text

    # /auth/me now works with fresh access token.
    r4 = s.get(f"{BASE_URL}/api/auth/me", timeout=TIMEOUT)
    assert r4.status_code == 200


def test_journey_create_after_refresh(logged_in_jar):
    s = logged_in_jar
    name = f"TEST_refreshflow_{uuid.uuid4().hex[:8]}"
    r = s.post(
        f"{BASE_URL}/api/journeys",
        json={"name": name, "timezone": "Australia/Perth"},
        timeout=TIMEOUT,
    )
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body.get("name") == name
    assert "id" in body


def test_wrong_password_no_refresh_trigger():
    """Negative check: a wrong-password login returns invalid credentials with no refresh."""
    s = requests.Session()
    # Use lockout-drills account with one wrong attempt so we don't touch owner rate limit.
    r = s.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "lockout-drills@propertyacquisition-demo.com", "password": "WrongPassword123"},
        timeout=TIMEOUT,
    )
    assert r.status_code in (400, 401, 403), r.text
    # No auth cookies set.
    assert not any(c.name in {"pa_access", "pa_refresh", "pa_signed_in"} for c in s.cookies)
