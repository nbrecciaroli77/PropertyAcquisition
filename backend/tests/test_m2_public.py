"""Milestone 2 QA suite executed against the public preview URL with a real cookie jar.

Modules covered: app/api/auth.py (signup, verify-email, login, sessions, profile, logout-all,
forgot/reset password, lockout), app/api/dev.py (outbox), app/api/journeys.py (journeys CRUD,
onboarding, brief draft/publish/versions/reset-weights), app/core/deps.py (tenant isolation).

Test accounts are created under the m2tests.pa-prototype.com domain, which the session-scoped
cleanup fixture in conftest.py removes at the end of the run.
"""

import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL is missing from env and /app/frontend/.env")
BASE_URL = base_url.rstrip("/")
TIMEOUT = 60

DOMAIN = "m2tests.pa-prototype.com"
PASSWORD = "Prototype2026pass"
OWNER = ("owner@propertyacquisition-demo.com", "Prototype2026pass")
OTHER = ("other@propertyacquisition-demo.com", "Prototype2026pass")


def new_email(prefix: str = "qa") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@{DOMAIN}"


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def api(s, method, path, **kw):
    return s.request(method, f"{BASE_URL}{path}", timeout=TIMEOUT, **kw)


def outbox_for(s, email, kind):
    r = api(s, "GET", "/api/dev/outbox", params={"email": email})
    assert r.status_code == 200, r.text[:300]
    return [m for m in r.json() if m["kind"] == kind]


def signup(s, email, password=PASSWORD, workspace_name=None):
    body = {"email": email, "password": password, "display_name": "QA Owner"}
    if workspace_name:
        body["workspace_name"] = workspace_name
    return api(s, "POST", "/api/auth/signup", json=body)


def verify(s, email):
    msgs = outbox_for(s, email, "verify_email")
    assert msgs, f"no verification message queued for {email}"
    token = msgs[0]["action_url"].split("token=")[1]
    r = api(s, "POST", "/api/auth/verify-email", json={"token": token})
    assert r.status_code == 200, r.text[:300]
    return token


def login(s, email, password=PASSWORD):
    return api(s, "POST", "/api/auth/login", json={"email": email, "password": password})


@pytest.fixture(scope="module")
def owner_client():
    s = session()
    r = login(s, *OWNER)
    assert r.status_code == 200, r.text[:400]
    return s


@pytest.fixture(scope="module")
def owner_journey_id(owner_client):
    r = api(owner_client, "GET", "/api/journeys")
    assert r.status_code == 200, r.text[:300]
    journeys = r.json()
    assert journeys, "seeded owner has no journey"
    return journeys[0]["id"]


@pytest.fixture(scope="module")
def other_client():
    s = session()
    r = login(s, *OTHER)
    assert r.status_code == 200, r.text[:400]
    return s


@pytest.fixture(scope="module")
def verified_account():
    """A fresh, verified, signed-in account with its own journey."""
    s = session()
    email = new_email("acct")
    assert signup(s, email, workspace_name="QA workspace").status_code == 201
    verify(s, email)
    r = login(s, email)
    assert r.status_code == 200, r.text[:400]
    jr = api(s, "POST", "/api/journeys", json={"name": "QA journey"})
    assert jr.status_code == 201, jr.text[:300]
    return {"client": s, "email": email, "journey": jr.json()}


# --- Signup, verification and the development outbox ---
class TestSignupAndVerification:
    def test_signup_does_not_sign_in_and_queues_suppressed_email(self):
        s = session()
        email = new_email("signup")
        r = signup(s, email, workspace_name="Brand new household")
        assert r.status_code == 201, r.text[:400]
        data = r.json()
        assert data["status"] == "verification_pending"
        assert data["email"] == email
        assert "no email is delivered" in data["message"]
        # Signup must not establish a session
        assert "pa_access" not in s.cookies.get_dict()
        assert api(s, "GET", "/api/auth/me").status_code == 401

        msgs = outbox_for(s, email, "verify_email")
        assert len(msgs) == 1
        assert msgs[0]["delivery_state"] == "suppressed_no_provider"
        assert "/verify-email?token=" in msgs[0]["action_url"]

    def test_login_before_verification_is_403_email_not_verified(self):
        s = session()
        email = new_email("unverified")
        assert signup(s, email).status_code == 201
        r = login(s, email)
        assert r.status_code == 403, r.text[:300]
        assert r.json()["detail"] == "email_not_verified"
        assert "pa_access" not in s.cookies.get_dict()

    def test_verification_token_is_single_use(self):
        s = session()
        email = new_email("single")
        assert signup(s, email).status_code == 201
        token = verify(s, email)
        again = api(s, "POST", "/api/auth/verify-email", json={"token": token})
        assert again.status_code == 400, again.text[:300]
        assert "invalid or has expired" in again.json()["detail"]

    def test_login_after_verification_sets_httponly_cookies(self):
        s = session()
        email = new_email("verified")
        assert signup(s, email, workspace_name="Verified household").status_code == 201
        verify(s, email)
        r = login(s, email)
        assert r.status_code == 200, r.text[:400]
        body = r.json()
        assert body["user"]["email"] == email
        assert body["user"]["email_verified"] is True
        assert body["workspace"]["name"] == "Verified household"
        assert body["workspace"]["role"] == "owner"
        names = {c.name for c in s.cookies}
        assert {"pa_access", "pa_refresh"} <= names
        set_cookie = r.headers.get("set-cookie", "").lower()
        assert "httponly" in set_cookie and "secure" in set_cookie
        me = api(s, "GET", "/api/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["email"] == email

    def test_new_account_has_no_journey(self):
        s = session()
        email = new_email("nojourney")
        assert signup(s, email).status_code == 201
        verify(s, email)
        assert login(s, email).status_code == 200
        r = api(s, "GET", "/api/journeys")
        assert r.status_code == 200
        assert r.json() == []

    def test_signup_rejects_weak_password_and_extra_workspace_id(self):
        s = session()
        r = api(
            s,
            "POST",
            "/api/auth/signup",
            json={"email": new_email("weak"), "password": "short1", "display_name": "QA"},
        )
        assert r.status_code == 422, r.text[:300]
        r2 = api(
            s,
            "POST",
            "/api/auth/signup",
            json={
                "email": new_email("wsid"),
                "password": PASSWORD,
                "display_name": "QA",
                "workspace_id": str(uuid.uuid4()),
            },
        )
        assert r2.status_code == 422, r2.text[:300]

    def test_duplicate_signup_is_neutral(self):
        s = session()
        r = signup(s, OWNER[0])
        assert r.status_code == 201, r.text[:300]
        assert r.json()["status"] == "verification_pending"

    def test_reissue_verification_is_neutral_for_unknown_email(self):
        s = session()
        r = api(s, "POST", "/api/auth/reissue-verification", json={"email": new_email("ghost")})
        assert r.status_code == 202, r.text[:300]
        assert r.json()["status"] == "accepted"


# --- Login lockout ---
class TestLockout:
    def test_five_failures_then_429(self):
        s = session()
        email = new_email("lockout")
        codes = [login(s, email, "WrongPassword1").status_code for _ in range(5)]
        assert codes == [401] * 5, codes
        sixth = login(s, email, "WrongPassword1")
        assert sixth.status_code == 429, f"{sixth.status_code} {sixth.text[:200]}"


# --- Onboarding: guided setup persistence ---
class TestOnboarding:
    def test_journey_step_persists_and_completes(self, verified_account):
        s = verified_account["client"]
        journey = verified_account["journey"]
        assert journey["onboarding_step"] == 1
        assert journey["onboarding_complete"] is False

        r = api(
            s,
            "PATCH",
            f"/api/journeys/{journey['id']}",
            json={"onboarding_step": 4, "expected_row_version": journey["row_version"]},
        )
        assert r.status_code == 200, r.text[:300]
        assert r.json()["onboarding_step"] == 4

        got = api(s, "GET", f"/api/journeys/{journey['id']}")
        assert got.status_code == 200
        assert got.json()["onboarding_step"] == 4  # resumable

        stale = api(
            s,
            "PATCH",
            f"/api/journeys/{journey['id']}",
            json={"onboarding_step": 2, "expected_row_version": journey["row_version"]},
        )
        assert stale.status_code == 409, stale.text[:200]

        done = api(s, "POST", f"/api/journeys/{journey['id']}/complete-onboarding")
        assert done.status_code == 200, done.text[:300]
        body = done.json()
        assert body["onboarding_complete"] is True
        assert body["onboarding_step"] == 6
        assert body["status"] == "active"
        verified_account["journey"] = body

    def test_journey_create_rejects_client_workspace_id(self, verified_account):
        r = api(
            verified_account["client"],
            "POST",
            "/api/journeys",
            json={"name": "Rejected", "workspace_id": str(uuid.uuid4())},
        )
        assert r.status_code == 422, r.text[:300]


# --- Brief draft, validation, publication and versions ---
class TestBrief:
    @pytest.fixture(scope="class")
    def brief_account(self):
        s = session()
        email = new_email("brief")
        assert signup(s, email).status_code == 201
        verify(s, email)
        assert login(s, email).status_code == 200
        jr = api(s, "POST", "/api/journeys", json={"name": "Brief journey"})
        assert jr.status_code == 201, jr.text[:300]
        return {"client": s, "email": email, "journey_id": jr.json()["id"]}

    def brief(self, acct):
        r = api(acct["client"], "GET", f"/api/journeys/{acct['journey_id']}/brief")
        assert r.status_code == 200, r.text[:300]
        return r.json()

    def save(self, acct, payload, row_version, step=None):
        body = {"payload": payload, "expected_row_version": row_version}
        if step is not None:
            body["onboarding_step"] = step
        return api(acct["client"], "PUT", f"/api/journeys/{acct['journey_id']}/brief/draft", json=body)

    def test_default_brief_has_all_criteria_and_modes(self, brief_account):
        b = self.brief(brief_account)
        draft = b["draft"]
        for key in (
            "budget",
            "property_profile",
            "beds",
            "baths",
            "parking",
            "land_sqm",
            "floor_sqm",
            "renovation",
            "timing",
            "locations",
            "policies",
            "weights",
        ):
            assert key in draft, key
        assert draft["schema_version"] == 1
        assert draft["currency"] == "AUD"
        assert draft["budget"]["mode"] == "hard"
        assert draft["land_sqm"]["mode"] == "hard"
        assert b["weight_total_enabled"] == 100
        # Unknown is first class: nothing is coerced to 0/false
        assert draft["budget"]["ceiling_minor"] is None
        assert draft["property_profile"]["detached_required"] is None
        assert "value_score" not in str(b).lower()

    def test_publication_blockers_are_field_linked(self, brief_account):
        b = self.brief(brief_account)
        draft = b["draft"]
        journey = b["journey"]
        # Hard budget with no ceiling + hard land rule with no value already block
        fields = {e["field"] for e in b["validation"]}
        assert "budget.ceiling_minor" in fields
        assert "land_sqm.min" in fields

        pub = api(
            brief_account["client"],
            "POST",
            f"/api/journeys/{brief_account['journey_id']}/brief/publish",
            json={"reason": "Should be blocked", "expected_row_version": journey["row_version"]},
        )
        assert pub.status_code == 422, pub.text[:300]
        detail = pub.json()["detail"]
        assert detail["code"] == "brief_invalid"
        assert {e["field"] for e in detail["errors"]} >= {"budget.ceiling_minor", "land_sqm.min"}

        # Preferred max above ceiling
        draft["budget"] = {
            "mode": "hard",
            "ceiling_minor": 100_000_000,
            "preferred_min_minor": 80_000_000,
            "preferred_max_minor": 120_000_000,
        }
        draft["land_sqm"] = {"mode": "hard", "min": 400, "max": 900}
        r = self.save(brief_account, draft, journey["row_version"])
        assert r.status_code == 200, r.text[:300]
        b = r.json()
        fields = {e["field"] for e in b["validation"]}
        assert "budget.preferred_max_minor" in fields
        assert "land_sqm.min" not in fields

        # All four weights disabled
        draft = b["draft"]
        draft["budget"]["preferred_max_minor"] = 95_000_000
        for name in ("price", "land", "location", "condition"):
            draft["weights"][f"{name}_enabled"] = False
        r = self.save(brief_account, draft, b["journey"]["row_version"])
        assert r.status_code == 200, r.text[:300]
        b = r.json()
        assert b["weight_total_enabled"] == 0
        assert "weights" in {e["field"] for e in b["validation"]}

        # Fixing everything clears blockers
        draft = b["draft"]
        for name in ("price", "land", "location", "condition"):
            draft["weights"][f"{name}_enabled"] = True
        draft["locations"] = {
            "mode": "hard",
            "states": ["WA"],
            "included": [{"suburb": "Subiaco", "state": "WA", "postcode": "6008"}],
            "excluded": [],
            "radius_km": 10,
            "anchors": [],
        }
        r = self.save(brief_account, draft, b["journey"]["row_version"])
        assert r.status_code == 200, r.text[:300]
        b = r.json()
        assert b["validation"] == [], b["validation"]

    def test_publish_twice_creates_immutable_versions(self, brief_account):
        b = self.brief(brief_account)
        assert b["validation"] == [], b["validation"]
        r1 = api(
            brief_account["client"],
            "POST",
            f"/api/journeys/{brief_account['journey_id']}/brief/publish",
            json={"reason": "First publication for QA", "expected_row_version": b["journey"]["row_version"]},
        )
        assert r1.status_code == 201, r1.text[:400]
        b1 = r1.json()
        assert b1["current_version"]["version_no"] == 1
        assert b1["current_version"]["reason"] == "First publication for QA"
        assert b1["current_version"]["actor_email"] == brief_account["email"]
        v1_payload = b1["current_version"]["payload"]

        draft = b1["draft"]
        draft["beds"] = {"mode": "preference", "min": 4, "max": 5}
        r = self.save(brief_account, draft, b1["journey"]["row_version"])
        assert r.status_code == 200, r.text[:300]
        b2src = r.json()
        r2 = api(
            brief_account["client"],
            "POST",
            f"/api/journeys/{brief_account['journey_id']}/brief/publish",
            json={
                "reason": "Second publication after bedroom change",
                "expected_row_version": b2src["journey"]["row_version"],
            },
        )
        assert r2.status_code == 201, r2.text[:400]
        assert r2.json()["current_version"]["version_no"] == 2

        versions = api(
            brief_account["client"], "GET", f"/api/journeys/{brief_account['journey_id']}/brief/versions"
        )
        assert versions.status_code == 200
        vlist = versions.json()
        assert [v["version_no"] for v in vlist] == [2, 1]
        older = next(v for v in vlist if v["version_no"] == 1)
        assert older["payload"] == v1_payload, "version 1 payload mutated after publishing version 2"
        assert older["reason"] == "First publication for QA"
        assert all(v["actor_email"] == brief_account["email"] for v in vlist)

    def test_publish_requires_reason(self, brief_account):
        b = self.brief(brief_account)
        r = api(
            brief_account["client"],
            "POST",
            f"/api/journeys/{brief_account['journey_id']}/brief/publish",
            json={"reason": "", "expected_row_version": b["journey"]["row_version"]},
        )
        assert r.status_code == 422, r.text[:300]

    def test_reset_weights_restores_defaults(self, brief_account):
        b = self.brief(brief_account)
        draft = b["draft"]
        draft["weights"] = {
            "price": 10,
            "land": 5,
            "location": 5,
            "condition": 5,
            "price_enabled": True,
            "land_enabled": False,
            "location_enabled": True,
            "condition_enabled": True,
        }
        r = self.save(brief_account, draft, b["journey"]["row_version"])
        assert r.status_code == 200, r.text[:300]
        assert r.json()["weight_total_enabled"] == 20

        rr = api(
            brief_account["client"],
            "POST",
            f"/api/journeys/{brief_account['journey_id']}/brief/reset-weights",
        )
        assert rr.status_code == 200, rr.text[:300]
        body = rr.json()
        w = body["draft"]["weights"]
        assert (w["price"], w["land"], w["location"], w["condition"]) == (30, 30, 20, 20)
        assert all(w[f"{n}_enabled"] for n in ("price", "land", "location", "condition"))
        assert body["weight_total_enabled"] == 100

    def test_locations_all_states_and_conflict_error(self, brief_account):
        b = self.brief(brief_account)
        draft = b["draft"]
        draft["locations"] = {
            "mode": "hard",
            "states": ["WA", "SA", "NT", "QLD", "NSW", "ACT", "VIC", "TAS"],
            "included": [{"suburb": "Subiaco", "state": "WA", "postcode": "6008"}],
            "excluded": [{"suburb": "subiaco", "state": "WA", "postcode": None}],
            "radius_km": 15,
            "anchors": [{"label": "Work", "address": "1 St Georges Tce, Perth", "max_minutes": None}],
        }
        r = self.save(brief_account, draft, b["journey"]["row_version"])
        assert r.status_code == 200, r.text[:300]
        b = r.json()
        assert len(b["draft"]["locations"]["states"]) == 8
        errors = {e["field"]: e["message"] for e in b["validation"]}
        assert "locations.excluded" in errors
        assert "both included and excluded" in errors["locations.excluded"]
        assert b["draft"]["locations"]["anchors"][0]["max_minutes"] is None

        draft = b["draft"]
        draft["locations"]["excluded"] = []
        draft["locations"]["radius_km"] = 0
        r = self.save(brief_account, draft, b["journey"]["row_version"])
        assert r.status_code == 200, r.text[:300]
        assert "locations.radius_km" in {e["field"] for e in r.json()["validation"]}

        draft = r.json()["draft"]
        draft["locations"]["radius_km"] = 12
        r = self.save(brief_account, draft, r.json()["journey"]["row_version"])
        assert r.status_code == 200
        assert r.json()["validation"] == []

    def test_draft_rejects_unknown_payload_fields(self, brief_account):
        b = self.brief(brief_account)
        draft = dict(b["draft"])
        draft["value_score"] = 42
        r = self.save(brief_account, draft, b["journey"]["row_version"])
        assert r.status_code == 422, r.text[:300]

    def test_invalid_mode_rejected(self, brief_account):
        b = self.brief(brief_account)
        draft = b["draft"]
        draft["beds"]["mode"] = "maybe"
        r = self.save(brief_account, draft, b["journey"]["row_version"])
        assert r.status_code == 422, r.text[:300]


# --- Tenant isolation ---
class TestTenantIsolation:
    def test_cross_tenant_reads_are_404(self, other_client, owner_journey_id):
        for path in ("", "/brief", "/brief/versions"):
            r = api(other_client, "GET", f"/api/journeys/{owner_journey_id}{path}")
            assert r.status_code == 404, f"{path} -> {r.status_code} {r.text[:200]}"
            assert "Perth family home" not in r.text

    def test_cross_tenant_writes_are_404(self, other_client, owner_journey_id):
        r = api(
            other_client,
            "PUT",
            f"/api/journeys/{owner_journey_id}/brief/draft",
            json={"payload": {"schema_version": 1, "currency": "AUD"}, "expected_row_version": 1},
        )
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"
        r = api(
            other_client,
            "POST",
            f"/api/journeys/{owner_journey_id}/brief/publish",
            json={"reason": "Cross tenant attempt", "expected_row_version": 1},
        )
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"
        r = api(
            other_client,
            "PATCH",
            f"/api/journeys/{owner_journey_id}",
            json={"name": "Hijacked", "expected_row_version": 1},
        )
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"
        r = api(other_client, "POST", f"/api/journeys/{owner_journey_id}/complete-onboarding")
        assert r.status_code == 404, f"{r.status_code} {r.text[:200]}"

    def test_other_tenant_sees_only_its_own_journeys(self, other_client, owner_journey_id):
        r = api(other_client, "GET", "/api/journeys")
        assert r.status_code == 200
        ids = [j["id"] for j in r.json()]
        assert owner_journey_id not in ids
        assert all("Perth family home 2026" != j["name"] for j in r.json())

    def test_owner_still_reads_own_journey(self, owner_client, owner_journey_id):
        r = api(owner_client, "GET", f"/api/journeys/{owner_journey_id}/brief")
        assert r.status_code == 200, r.text[:300]
        assert r.json()["current_version"]["version_no"] >= 1

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/journeys"),
            ("GET", "/api/auth/me"),
            ("GET", "/api/auth/sessions"),
        ],
    )
    def test_anonymous_requests_are_401(self, method, path):
        r = api(session(), method, path)
        assert r.status_code == 401, f"{path} -> {r.status_code}"

    def test_anonymous_journey_deep_link_is_401(self, owner_journey_id):
        r = api(session(), "GET", f"/api/journeys/{owner_journey_id}/brief")
        assert r.status_code == 401, r.text[:200]


# --- Settings: profile, sessions, sign out everywhere ---
class TestSettingsAndSessions:
    def test_profile_update_persists(self):
        s = session()
        email = new_email("profile")
        assert signup(s, email).status_code == 201
        verify(s, email)
        assert login(s, email).status_code == 200
        r = api(
            s, "PATCH", "/api/auth/me", json={"display_name": "QA Renamed", "timezone": "Australia/Sydney"}
        )
        assert r.status_code == 200, r.text[:300]
        assert r.json()["user"]["display_name"] == "QA Renamed"
        me = api(s, "GET", "/api/auth/me")
        assert me.json()["user"]["display_name"] == "QA Renamed"
        assert me.json()["user"]["timezone"] == "Australia/Sydney"

    def test_sessions_list_revoke_and_logout_all(self):
        email = new_email("sessions")
        s1 = session()
        assert signup(s1, email).status_code == 201
        verify(s1, email)
        assert login(s1, email).status_code == 200
        s2 = session()
        assert login(s2, email).status_code == 200

        r = api(s1, "GET", "/api/auth/sessions")
        assert r.status_code == 200, r.text[:300]
        sessions = r.json()
        assert len(sessions) == 2, sessions
        current = [x for x in sessions if x["current"]]
        assert len(current) == 1
        other = next(x for x in sessions if not x["current"])

        rv = api(s1, "DELETE", f"/api/auth/sessions/{other['id']}")
        assert rv.status_code == 200, rv.text[:300]
        assert api(s2, "GET", "/api/auth/me").status_code == 401
        assert len(api(s1, "GET", "/api/auth/sessions").json()) == 1

        la = api(s1, "POST", "/api/auth/logout-all")
        assert la.status_code == 200, la.text[:300]
        assert api(s1, "GET", "/api/auth/me").status_code == 401
        assert api(s1, "GET", "/api/journeys").status_code == 401

    def test_revoking_unknown_session_is_404(self):
        s = session()
        email = new_email("revoke404")
        assert signup(s, email).status_code == 201
        verify(s, email)
        assert login(s, email).status_code == 200
        r = api(s, "DELETE", f"/api/auth/sessions/{uuid.uuid4()}")
        assert r.status_code == 404, r.text[:200]

    def test_refresh_rotates_session(self):
        s = session()
        email = new_email("refresh")
        assert signup(s, email).status_code == 201
        verify(s, email)
        assert login(s, email).status_code == 200
        before = s.cookies.get("pa_refresh")
        r = api(s, "POST", "/api/auth/refresh")
        assert r.status_code == 200, r.text[:300]
        assert s.cookies.get("pa_refresh") != before
        assert api(s, "GET", "/api/auth/me").status_code == 200


# --- Password recovery ---
class TestPasswordRecovery:
    def test_forgot_password_is_neutral_and_reset_rotates_credentials(self):
        s = session()
        email = new_email("reset")
        assert signup(s, email).status_code == 201
        verify(s, email)
        assert login(s, email).status_code == 200

        known = api(s, "POST", "/api/auth/forgot-password", json={"email": email})
        unknown = api(s, "POST", "/api/auth/forgot-password", json={"email": new_email("ghost")})
        assert known.status_code == unknown.status_code == 202
        assert known.json() == unknown.json(), "forgot-password responses are not neutral"

        msgs = outbox_for(s, email, "password_reset")
        assert msgs and msgs[0]["delivery_state"] == "suppressed_no_provider"
        token = msgs[0]["action_url"].split("token=")[1]

        new_password = "Prototype2026reset9"
        rp = api(s, "POST", "/api/auth/reset-password", json={"token": token, "password": new_password})
        assert rp.status_code == 200, rp.text[:300]
        assert rp.json()["status"] == "password_reset"

        # Sessions revoked by the reset
        assert api(s, "GET", "/api/auth/me").status_code == 401
        # Old password no longer works, new one does
        s2 = session()
        assert login(s2, email, PASSWORD).status_code == 401
        assert login(s2, email, new_password).status_code == 200
        # Token cannot be reused
        again = api(
            session(), "POST", "/api/auth/reset-password", json={"token": token, "password": new_password}
        )
        assert again.status_code == 400, again.text[:200]

    def test_reset_password_rejects_weak_password(self):
        s = session()
        email = new_email("weakreset")
        assert signup(s, email).status_code == 201
        verify(s, email)
        api(s, "POST", "/api/auth/forgot-password", json={"email": email})
        token = outbox_for(s, email, "password_reset")[0]["action_url"].split("token=")[1]
        r = api(s, "POST", "/api/auth/reset-password", json={"token": token, "password": "abc"})
        assert r.status_code == 422, r.text[:300]


# --- Safety surface ---
class TestSafetySurface:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/send",
            "/api/messages/send",
            "/api/offers",
            "/api/bookings",
            "/api/billing",
            "/api/scrape",
            "/api/value-score",
        ],
    )
    def test_no_unsafe_routes(self, path):
        s = session()
        assert api(s, "GET", path).status_code == 404
        assert api(s, "POST", path, json={}).status_code in (404, 405)

    def test_openapi_has_no_unsafe_or_value_score_paths(self):
        s = session()
        r = api(s, "GET", "/api/openapi.json")
        if r.status_code != 200:
            pytest.skip("openapi not exposed")
        text = r.text.lower()
        for word in (
            "value_score",
            "valuescore",
            "indicative_value",
            "/send",
            "/offer",
            "/billing",
            "scrape",
        ):
            assert word not in text, word
