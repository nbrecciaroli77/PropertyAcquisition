# mypy: ignore-errors
# QA-cycle suite authored during the M3 consolidated test run; exercises the public ingress.
"""M3 property workspace over the PUBLIC ingress (cookie auth). Run with -p no:randomly.

Covers: fixture catalogue + verdicts, list filters/sort, compare, detail shape, workflow
transitions/waivers/concurrency, notes/tasks/saved, today/activity, brief re-evaluation and
cross-tenant isolation.
"""

import os
import re
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
TIMEOUT = 45
PASSWORD = "Prototype2026pass"


def _creds() -> dict[str, str]:
    content = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    emails = re.findall(r"Email: `([^`]+)`", content)
    return {"owner": emails[0], "other": emails[1]}


def _session(email: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PASSWORD}, timeout=TIMEOUT)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text[:300]}"
    assert "pa_access" in s.cookies, f"pa_access cookie missing, got {s.cookies.keys()}"
    return s


def _journey_id(s: requests.Session) -> str:
    r = s.get(f"{BASE_URL}/api/journeys", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    js = r.json()
    assert js, "no journeys for account"
    return str(js[0]["id"])


@pytest.fixture(scope="module")
def owner() -> requests.Session:
    return _session(_creds()["owner"])


@pytest.fixture(scope="module")
def other() -> requests.Session:
    return _session(_creds()["other"])


@pytest.fixture(scope="module")
def jid(owner: requests.Session) -> str:
    return _journey_id(owner)


@pytest.fixture(scope="module")
def other_jid(other: requests.Session) -> str:
    return _journey_id(other)


def _by_ref(s: requests.Session, journey: str) -> dict:
    r = s.get(f"{BASE_URL}/api/journeys/{journey}/properties", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return {p["legacy_ref"]: p for p in r.json()}


@pytest.fixture(scope="module")
def props(owner: requests.Session, jid: str) -> dict:
    return _by_ref(owner, jid)


# ---------------------------------------------------------------- fixture catalogue
class TestCatalogue:
    def test_seven_demo_properties(self, props):
        assert sorted(props) == [f"DEMO-00{i}" for i in range(1, 8)]

    @pytest.mark.parametrize(
        "ref,verdict",
        [
            ("DEMO-001", "pass"),
            ("DEMO-002", "unknown"),
            ("DEMO-003", "fail"),
            ("DEMO-004", "unknown"),
            ("DEMO-005", "pass"),
            ("DEMO-006", "unknown"),
            ("DEMO-007", "pass"),
        ],
    )
    def test_verdicts(self, props, ref, verdict):
        assert props[ref]["evaluation"]["verdict"] == verdict

    def test_demo003_land_fail_and_fit(self, props):
        ev = props["DEMO-003"]["evaluation"]
        assert ev["fit"]["pct"] == 87
        land = next(g for g in ev["gates"] if g["criterion"] == "land_sqm")
        assert land["outcome"] == "fail"
        assert props["DEMO-003"]["facts"]["land_sqm"]["value_int"] == 318

    def test_demo002_contact_agent_price(self, props):
        assert props["DEMO-002"]["campaign"]["price_kind"] == "contact_agent"
        assert props["DEMO-002"]["campaign"]["raw_price"]

    def test_demo004_conflicting_price(self, props):
        assert props["DEMO-004"]["campaign"]["price_kind"] == "conflicting"

    def test_demo006_land_unknown_not_zero(self, props):
        land = props["DEMO-006"]["facts"]["land_sqm"]
        assert land["value_state"] == "unknown"
        assert land["value_int"] is None

    def test_demo007_under_offer_archived(self, props):
        assert props["DEMO-007"]["campaign"]["market_state"] == "under_offer"
        assert props["DEMO-007"]["buyer_state"] == "archived"

    def test_units_distinct(self, props):
        assert props["DEMO-005"]["unit"] == "A"
        assert props["DEMO-006"]["unit"] == "C"
        assert props["DEMO-005"]["id"] != props["DEMO-006"]["id"]

    def test_evaluation_version_and_hash(self, props):
        ev = props["DEMO-001"]["evaluation"]
        assert ev["evaluation_version"] == "gates_v1+scoring_v1"
        assert isinstance(ev["input_hash"], str) and len(ev["input_hash"]) > 8

    def test_no_mongo_id_leak(self, props):
        assert all("_id" not in p for p in props.values())


# ---------------------------------------------------------------- filters, sort, compare
class TestListFilters:
    def test_filter_buyer_state(self, owner, jid):
        r = owner.get(f"{BASE_URL}/api/journeys/{jid}/properties?buyer_state=reviewing", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data and all(p["buyer_state"] == "reviewing" for p in data)

    def test_filter_verdict_fail(self, owner, jid):
        r = owner.get(f"{BASE_URL}/api/journeys/{jid}/properties?verdict=fail", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert [p["legacy_ref"] for p in data] == ["DEMO-003"]

    def test_filter_saved(self, owner, jid):
        r = owner.get(f"{BASE_URL}/api/journeys/{jid}/properties?saved=true", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data and all(p["saved"] is True for p in data)
        assert "DEMO-005" in [p["legacy_ref"] for p in data]

    def test_search_q(self, owner, jid):
        r = owner.get(f"{BASE_URL}/api/journeys/{jid}/properties?q=81a", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data, "q=81a returned nothing"
        assert all("81a" in f"{p['address_line']}".lower() for p in data)

    @pytest.mark.parametrize("sort", ["fit", "address", "checked"])
    def test_sorts(self, owner, jid, sort):
        r = owner.get(f"{BASE_URL}/api/journeys/{jid}/properties?sort={sort}", timeout=TIMEOUT)
        assert r.status_code == 200
        assert len(r.json()) == 7

    def test_sort_fit_descending_known_first(self, owner, jid):
        data = owner.get(f"{BASE_URL}/api/journeys/{jid}/properties?sort=fit", timeout=TIMEOUT).json()
        pcts = [p["evaluation"]["fit"]["pct"] for p in data]
        known = [p for p in pcts if p is not None]
        assert known == sorted(known, reverse=True)
        assert pcts[: len(known)] == known

    def test_bad_sort_rejected(self, owner, jid):
        r = owner.get(f"{BASE_URL}/api/journeys/{jid}/properties?sort=bogus", timeout=TIMEOUT)
        assert r.status_code == 422

    def test_compare_four(self, owner, jid, props):
        ids = [props[f"DEMO-00{i}"]["id"] for i in (1, 2, 3, 5)]
        r = owner.get(
            f"{BASE_URL}/api/journeys/{jid}/properties/compare?ids={','.join(ids)}", timeout=TIMEOUT
        )
        assert r.status_code == 200, r.text
        assert [p["id"] for p in r.json()] == ids

    def test_compare_five_rejected(self, owner, jid, props):
        ids = [props[f"DEMO-00{i}"]["id"] for i in (1, 2, 3, 4, 5)]
        r = owner.get(
            f"{BASE_URL}/api/journeys/{jid}/properties/compare?ids={','.join(ids)}", timeout=TIMEOUT
        )
        assert r.status_code == 422

    def test_compare_invalid_uuid(self, owner, jid):
        r = owner.get(f"{BASE_URL}/api/journeys/{jid}/properties/compare?ids=not-a-uuid", timeout=TIMEOUT)
        assert r.status_code == 422


# ---------------------------------------------------------------- detail shape
class TestDetail:
    def test_detail_shape(self, owner, jid, props):
        pid = props["DEMO-001"]["id"]
        r = owner.get(f"{BASE_URL}/api/journeys/{jid}/properties/{pid}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        for key in (
            "facts",
            "observations",
            "evaluation",
            "waivers",
            "notes",
            "tasks",
            "activity",
            "allowed_transitions",
        ):
            assert key in d, f"missing {key}"
        for fact in d["facts"].values():
            assert fact["source_label"]
            assert fact["freshness"] in {"fresh", "ageing", "stale"}
        ev = d["evaluation"]
        assert ev["fit"]["state"] in {"known", "unknown"}
        assert isinstance(ev["coverage"]["pct"], int)
        assert ev["components"]
        assert all(g["outcome"] in {"pass", "fail", "unknown"} for g in ev["gates"])
        assert d["observations"] and d["observations"][0]["source_label"]

    def test_unknown_property_404(self, owner, jid):
        r = owner.get(
            f"{BASE_URL}/api/journeys/{jid}/properties/00000000-0000-4000-8000-000000000000",
            timeout=TIMEOUT,
        )
        assert r.status_code == 404


# ---------------------------------------------------------------- workflow / waivers
class TestWorkflow:
    def test_illegal_transition_409(self, owner, jid, props):
        p = props["DEMO-001"]
        r = owner.post(
            f"{BASE_URL}/api/journeys/{jid}/properties/{p['id']}/stage",
            json={"to_state": "settled", "expected_row_version": p["buyer_row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409, r.text
        assert r.json()["detail"]["code"] == "transition_not_allowed"

    def test_stale_row_version_409(self, owner, jid, props):
        p = props["DEMO-001"]
        r = owner.post(
            f"{BASE_URL}/api/journeys/{jid}/properties/{p['id']}/stage",
            json={"to_state": "shortlisted", "expected_row_version": p["buyer_row_version"] + 99},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409, r.text
        assert r.json()["detail"]["code"] == "stale_write"

    def test_fail_promotion_blocked_then_waived(self, owner, jid, props):
        pid = props["DEMO-003"]["id"]
        url = f"{BASE_URL}/api/journeys/{jid}/properties/{pid}"
        detail = owner.get(url, timeout=TIMEOUT).json()
        assert detail["buyer_state"] == "rejected", f"seed changed: {detail['buyer_state']}"
        # rejected -> reviewing
        r = owner.post(
            f"{url}/stage",
            json={"to_state": "reviewing", "expected_row_version": detail["buyer_row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        detail = r.json()
        assert detail["buyer_state"] == "reviewing"
        # promotion blocked
        r = owner.post(
            f"{url}/stage",
            json={"to_state": "shortlisted", "expected_row_version": detail["buyer_row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409, r.text
        body = r.json()["detail"]
        assert body["code"] == "hard_failure_cannot_be_promoted"
        assert body["failing"] == ["land_sqm"]
        # waiver on a passing gate is rejected
        r = owner.post(
            f"{url}/waivers", json={"criterion": "beds", "reason": "not applicable test"}, timeout=TIMEOUT
        )
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "waiver_not_applicable"
        # waiver on the failing gate
        r = owner.post(
            f"{url}/waivers",
            json={"criterion": "land_sqm", "reason": "QA waiver - corner block compensates"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 201, r.text
        detail = r.json()
        assert "land_sqm" in detail["waived_criteria"]
        assert detail["evaluation"]["verdict"] == "fail", "waiver must not flip the verdict"
        land = next(g for g in detail["evaluation"]["gates"] if g["criterion"] == "land_sqm")
        assert land["outcome"] == "fail", "waiver must not flip the gate outcome"
        waiver_id = next(w["id"] for w in detail["waivers"] if w["criterion"] == "land_sqm")
        # promotion now allowed
        r = owner.post(
            f"{url}/stage",
            json={"to_state": "shortlisted", "expected_row_version": detail["buyer_row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        detail = r.json()
        assert detail["buyer_state"] == "shortlisted"
        # revoke waiver
        r = owner.delete(f"{url}/waivers/{waiver_id}", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.json()["waived_criteria"] == []
        detail = r.json()
        # restore: shortlisted -> reviewing -> rejected
        r = owner.post(
            f"{url}/stage",
            json={"to_state": "reviewing", "expected_row_version": detail["buyer_row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        r = owner.post(
            f"{url}/stage",
            json={"to_state": "rejected", "expected_row_version": r.json()["buyer_row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        assert r.json()["buyer_state"] == "rejected"


# ---------------------------------------------------------------- notes, tasks, saved, today
class TestCollaboration:
    def test_saved_toggle_roundtrip(self, owner, jid, props):
        pid = props["DEMO-001"]["id"]
        url = f"{BASE_URL}/api/journeys/{jid}/properties/{pid}"
        d = owner.get(url, timeout=TIMEOUT).json()
        original = d["saved"]
        r = owner.post(
            f"{url}/saved",
            json={"saved": not original, "expected_row_version": d["buyer_row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        assert r.json()["saved"] is (not original)
        r = owner.post(
            f"{url}/saved",
            json={"saved": original, "expected_row_version": r.json()["buyer_row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200
        assert r.json()["saved"] is original

    def test_notes_create_edit_stale(self, owner, jid, props):
        pid = props["DEMO-002"]["id"]
        url = f"{BASE_URL}/api/journeys/{jid}/properties/{pid}"
        r = owner.post(f"{url}/notes", json={"body": "TEST_QA note m3"}, timeout=TIMEOUT)
        assert r.status_code == 201, r.text
        note = next(n for n in r.json()["notes"] if n["body"] == "TEST_QA note m3")
        r = owner.patch(
            f"{url}/notes/{note['id']}",
            json={"body": "TEST_QA note m3 edited", "expected_row_version": note["row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        edited = next(n for n in r.json()["notes"] if n["id"] == note["id"])
        assert edited["body"] == "TEST_QA note m3 edited"
        r = owner.patch(
            f"{url}/notes/{note['id']}",
            json={"body": "stale", "expected_row_version": note["row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 409, r.text
        assert r.json()["detail"]["code"] == "stale_write"

    def test_tasks_create_and_toggle(self, owner, jid, props):
        pid = props["DEMO-002"]["id"]
        url = f"{BASE_URL}/api/journeys/{jid}/properties/{pid}"
        r = owner.post(f"{url}/tasks", json={"title": "TEST_QA task m3"}, timeout=TIMEOUT)
        assert r.status_code == 201, r.text
        task = next(t for t in r.json()["tasks"] if t["title"] == "TEST_QA task m3")
        assert task["done"] is False
        r = owner.patch(
            f"{url}/tasks/{task['id']}",
            json={"done": True, "expected_row_version": task["row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        done = next(t for t in r.json()["tasks"] if t["id"] == task["id"])
        assert done["done"] is True and done["done_at"]
        # persistence check
        d = owner.get(url, timeout=TIMEOUT).json()
        assert next(t for t in d["tasks"] if t["id"] == task["id"])["done"] is True

    def test_today(self, owner, jid):
        r = owner.get(f"{BASE_URL}/api/journeys/{jid}/today", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        t = r.json()
        assert t["total_properties"] == 7
        assert t["known_failures"] == 1
        assert t["verification_required"] == 3
        assert isinstance(t["eligible_reviewing"], int)
        assert isinstance(t["open_tasks"], int)
        assert isinstance(t["changes"], list) and t["changes"]
        assert isinstance(t["attention"], list)

    def test_activity(self, owner, jid):
        r = owner.get(f"{BASE_URL}/api/journeys/{jid}/activity", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        events = r.json()
        assert events
        kinds = {e["kind"] for e in events}
        assert {"stage_changed", "waiver_recorded", "waiver_revoked"} & kinds
        assert all(e["summary"] for e in events)


# ---------------------------------------------------------------- brief-driven re-evaluation
class TestReevaluation:
    """Fresh tenant so the seeded workspace is untouched."""

    @pytest.fixture(scope="class")
    def fresh(self) -> tuple[requests.Session, str]:
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        email = f"qa-m3-{uuid.uuid4().hex[:8]}@m2tests.pa-prototype.com"
        r = s.post(
            f"{BASE_URL}/api/auth/signup",
            json={"email": email, "password": PASSWORD, "display_name": "QA M3"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 201, r.text
        outbox = s.get(f"{BASE_URL}/api/dev/outbox?email={email}", timeout=TIMEOUT).json()
        token = next(m for m in outbox if m["kind"] == "verify_email")["action_url"].split("token=")[1]
        assert s.post(f"{BASE_URL}/api/auth/verify-email", json={"token": token}, timeout=TIMEOUT).ok
        assert s.post(
            f"{BASE_URL}/api/auth/login", json={"email": email, "password": PASSWORD}, timeout=TIMEOUT
        ).ok
        jr = s.post(f"{BASE_URL}/api/journeys", json={"name": "QA M3 journey"}, timeout=TIMEOUT)
        assert jr.status_code == 201, jr.text
        return s, str(jr.json()["id"])

    def _publish(self, s, journey, draft, row_version, reason):
        r = s.put(
            f"{BASE_URL}/api/journeys/{journey}/brief/draft",
            json={"payload": draft, "expected_row_version": row_version},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        r = s.post(
            f"{BASE_URL}/api/journeys/{journey}/brief/publish",
            json={"reason": reason, "expected_row_version": r.json()["journey"]["row_version"]},
            timeout=TIMEOUT,
        )
        assert r.status_code == 201, r.text
        return r.json()

    def test_reevaluation_flow(self, fresh):
        s, journey = fresh
        brief = s.get(f"{BASE_URL}/api/journeys/{journey}/brief", timeout=TIMEOUT).json()
        draft = brief["draft"]
        draft["budget"]["ceiling_minor"] = 1_300_000_00
        draft["budget"]["preferred_max_minor"] = 1_200_000_00
        draft["beds"] = {"mode": "hard", "min": 3, "max": None}
        draft["land_sqm"] = {"mode": "hard", "min": 400, "max": None}
        draft["locations"]["states"] = ["WA"]
        published = self._publish(s, journey, draft, brief["journey"]["row_version"], "QA base brief")
        assert published["current_version"]["version_no"] == 1

        r = s.post(f"{BASE_URL}/api/dev/load-demo-properties", json={"journey_id": journey}, timeout=TIMEOUT)
        assert r.status_code == 201, r.text
        assert r.json()["created"] == 7
        r = s.post(f"{BASE_URL}/api/dev/load-demo-properties", json={"journey_id": journey}, timeout=TIMEOUT)
        assert r.status_code == 201, r.text
        assert r.json()["created"] == 0, "loader is not idempotent"

        before = _by_ref(s, journey)
        assert before["DEMO-001"]["evaluation"]["verdict"] == "pass"

        draft2 = s.get(f"{BASE_URL}/api/journeys/{journey}/brief", timeout=TIMEOUT).json()
        payload = draft2["draft"]
        payload["land_sqm"] = {"mode": "hard", "min": 700, "max": None}
        published2 = self._publish(
            s, journey, payload, draft2["journey"]["row_version"], "QA raise land floor"
        )
        assert published2["current_version"]["version_no"] == 2
        assert published2["current_version"]["reevaluation_state"] == "completed"

        after = _by_ref(s, journey)
        ev = after["DEMO-001"]["evaluation"]
        assert ev["brief_version_no"] == 2
        assert ev["verdict"] == "fail", f"expected fail after land floor 700, got {ev['verdict']}"

        versions = s.get(f"{BASE_URL}/api/journeys/{journey}/brief/versions", timeout=TIMEOUT).json()
        assert len(versions) >= 2
        assert all(v["reevaluation_state"] == "completed" for v in versions), versions


# ---------------------------------------------------------------- tenant isolation
class TestTenantIsolation:
    def test_cross_tenant_reads_and_writes_404(self, owner, other, jid, other_jid, props):
        other_props = _by_ref(other, other_jid)
        # B may have no properties; use A's ids against B and vice versa
        a_id = props["DEMO-001"]["id"]
        assert (
            owner.get(f"{BASE_URL}/api/journeys/{other_jid}/properties", timeout=TIMEOUT).status_code == 404
        )
        assert owner.get(f"{BASE_URL}/api/journeys/{other_jid}/today", timeout=TIMEOUT).status_code == 404
        assert (
            other.get(f"{BASE_URL}/api/journeys/{other_jid}/properties/{a_id}", timeout=TIMEOUT).status_code
            == 404
        )
        assert (
            other.get(
                f"{BASE_URL}/api/journeys/{other_jid}/properties/compare?ids={a_id}", timeout=TIMEOUT
            ).status_code
            == 404
        )
        assert (
            other.post(
                f"{BASE_URL}/api/journeys/{other_jid}/properties/{a_id}/notes",
                json={"body": "TEST_QA cross tenant"},
                timeout=TIMEOUT,
            ).status_code
            == 404
        )
        assert (
            other.post(
                f"{BASE_URL}/api/journeys/{other_jid}/properties/{a_id}/stage",
                json={"to_state": "shortlisted", "expected_row_version": 1},
                timeout=TIMEOUT,
            ).status_code
            == 404
        )
        if other_props:
            b_id = next(iter(other_props.values()))["id"]
            assert (
                owner.get(f"{BASE_URL}/api/journeys/{jid}/properties/{b_id}", timeout=TIMEOUT).status_code
                == 404
            )

    def test_unauthenticated_rejected(self, jid):
        r = requests.get(f"{BASE_URL}/api/journeys/{jid}/properties", timeout=TIMEOUT)
        assert r.status_code == 401, r.status_code
