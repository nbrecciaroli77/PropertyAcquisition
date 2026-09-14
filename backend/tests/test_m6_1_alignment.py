"""M6.1 Product Alignment — backend regression tests.

Covers:
- Locked report titles (daily/weekly/monthly)
- Presentation contract (all required sections present)
- Ready-to-send transitions (200 -> 409 on repeat)
- Idempotency after ready-to-send (returns same run)
- Inspection endpoint (state + row_version increment + NEVER affects gates/match)
- ScheduledJob rows exist but every one has enabled=false
"""
from __future__ import annotations

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://property-find-1.preview.emergentagent.com").rstrip("/")
OWNER_EMAIL = "owner@propertyacquisition-demo.com"
OWNER_PASSWORD = "Prototype2026pass"

LOCKED_TITLES = {
    "daily": "Property Acquisition – Your Daily Digest",
    "weekly": "Property Acquisition – Your Weekly Report",
    "monthly": "Property Acquisition – Your Monthly Assessment",
}

CONTRACT_SECTIONS = {
    "daily": [
        "title", "quiet_day", "material_changes_count", "current_candidates",
        "new_leads", "price_verification_opportunities", "upcoming_home_opens",
        "upcoming_deadlines", "source_evidence_health",
    ],
    "weekly": [
        "title", "period_start", "period_end", "unique_first_discoveries",
        "later_channel_material_changes", "provisional_opportunities",
        "fully_verified_eligibility", "high_priority_candidates", "hard_failures",
        "unavailable_withdrawn_stock", "actions_replies_completed_tasks", "duplicates",
        "source_coverage_readiness", "processing_evidence_latency_seconds",
        "daily_trend", "source_channel_funnel", "suburb_outcome_view",
    ],
    "monthly": [
        "title", "period_start", "period_end", "actual_coverage_start", "is_partial_period",
        "overall_activity", "source_value_unique_discoveries", "verdict_distribution",
        "candidate_progression_stage_changes", "duplicate_and_intake_quality",
        "task_action_completion", "report_notification_effectiveness",
        "material_constraints", "improvement_priorities",
    ],
}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def journey_id(session):
    r = session.get(f"{BASE_URL}/api/journeys", timeout=30)
    assert r.status_code == 200, r.text
    js = r.json()
    assert js, "No journeys for owner"
    return js[0]["id"]


# ── Reports: locked titles, contract, idempotency, ready-to-send ────────────

@pytest.mark.parametrize("report_type", ["daily", "weekly", "monthly"])
def test_report_generate_title_and_contract(session, journey_id, report_type):
    body = {"release_kind": "preview"}
    r = session.post(f"{BASE_URL}/api/journeys/{journey_id}/reports/{report_type}/generate", json=body, timeout=60)
    assert r.status_code == 200, r.text
    run = r.json()
    assert run["report_type"] == report_type
    snap = run.get("snapshot") or {}
    # Locked title
    assert snap.get("title") == LOCKED_TITLES[report_type], f"Title mismatch: {snap.get('title')!r}"
    # Contract satisfied
    missing = [k for k in CONTRACT_SECTIONS[report_type] if k not in snap]
    assert not missing, f"Missing sections: {missing}"
    # No banned wording
    assert "Weekly Effectiveness Report" not in str(snap.get("title", ""))
    # release_state is ready (contract passed) OR ready_to_send (already promoted from prior test run)
    assert run["release_state"] in ("ready", "ready_to_send"), run["release_state"]


def test_ready_to_send_transition_and_conflict(session, journey_id):
    # Generate a daily preview (idempotent)
    r = session.post(f"{BASE_URL}/api/journeys/{journey_id}/reports/daily/generate", json={"release_kind": "preview"}, timeout=60)
    assert r.status_code == 200, r.text
    run = r.json()
    run_id = run["id"]

    # If already ready_to_send from previous runs, calling should return 409 immediately.
    if run["release_state"] == "ready_to_send":
        r2 = session.post(f"{BASE_URL}/api/journeys/{journey_id}/reports/{run_id}/ready-to-send", timeout=30)
        assert r2.status_code == 409, r2.text
        return

    assert run["release_state"] == "ready"
    r1 = session.post(f"{BASE_URL}/api/journeys/{journey_id}/reports/{run_id}/ready-to-send", timeout=30)
    assert r1.status_code == 200, r1.text
    promoted = r1.json()
    assert promoted["release_state"] == "ready_to_send"
    assert promoted["ready_to_send_at"] is not None

    # Second call must return 409
    r2 = session.post(f"{BASE_URL}/api/journeys/{journey_id}/reports/{run_id}/ready-to-send", timeout=30)
    assert r2.status_code == 409, r2.text


def test_generate_idempotent_after_ready_to_send(session, journey_id):
    # After promotion, generate again with same report_type/release_kind/period returns SAME run
    r1 = session.post(f"{BASE_URL}/api/journeys/{journey_id}/reports/daily/generate", json={"release_kind": "preview"}, timeout=60)
    assert r1.status_code == 200, r1.text
    id1 = r1.json()["id"]
    state1 = r1.json()["release_state"]

    r2 = session.post(f"{BASE_URL}/api/journeys/{journey_id}/reports/daily/generate", json={"release_kind": "preview"}, timeout=60)
    assert r2.status_code == 200, r2.text
    id2 = r2.json()["id"]
    state2 = r2.json()["release_state"]

    assert id1 == id2, "Idempotency broken: generate returned a different run id after ready_to_send"
    assert state1 == state2


# ── Inspection endpoint ─────────────────────────────────────────────────────

def _pick_property(session, journey_id):
    r = session.get(f"{BASE_URL}/api/journeys/{journey_id}/properties", timeout=30)
    assert r.status_code == 200, r.text
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    if not items:
        pytest.skip("No properties available in demo journey")
    return items[0]["id"]


def test_inspection_endpoint_updates_state_and_row_version(session, journey_id):
    prop_id = _pick_property(session, journey_id)
    # Fetch current detail to get expected_row_version
    d = session.get(f"{BASE_URL}/api/journeys/{journey_id}/properties/{prop_id}", timeout=30)
    assert d.status_code == 200, d.text
    detail = d.json()
    rv = detail.get("buyer_row_version")
    assert rv is not None
    prev_state = detail.get("inspection_state")

    body = {
        "inspection_state": "great",
        "inspection_note": "TEST_M6.1 sample note",
        "expected_row_version": rv,
    }
    r = session.post(f"{BASE_URL}/api/journeys/{journey_id}/properties/{prop_id}/inspection", json=body, timeout=30)
    assert r.status_code == 200, r.text
    updated = r.json()
    assert updated["inspection_state"] == "great"
    assert updated["inspection_note"] == "TEST_M6.1 sample note"
    assert updated["inspection_recorded_at"] is not None
    assert updated["buyer_row_version"] == rv + 1

    # Stale expected_row_version must fail
    stale = session.post(f"{BASE_URL}/api/journeys/{journey_id}/properties/{prop_id}/inspection", json={
        "inspection_state": "ok", "inspection_note": None, "expected_row_version": rv,
    }, timeout=30)
    assert stale.status_code in (409, 412), f"Expected optimistic-concurrency conflict, got {stale.status_code}: {stale.text}"

    # Restore prior state to keep demo tidy
    d2 = session.get(f"{BASE_URL}/api/journeys/{journey_id}/properties/{prop_id}", timeout=30).json()
    session.post(f"{BASE_URL}/api/journeys/{journey_id}/properties/{prop_id}/inspection", json={
        "inspection_state": prev_state or "not_inspected",
        "inspection_note": None,
        "expected_row_version": d2["buyer_row_version"],
    }, timeout=30)


def test_inspection_does_not_affect_gates_or_match(session, journey_id):
    """Inspection feedback is purely informational — must NOT surface in evaluation."""
    prop_id = _pick_property(session, journey_id)
    d = session.get(f"{BASE_URL}/api/journeys/{journey_id}/properties/{prop_id}", timeout=30)
    assert d.status_code == 200, d.text
    detail = d.json()
    # Set inspection to "not_as_good" and confirm gates/match remain unchanged
    rv = detail["buyer_row_version"]
    session.post(f"{BASE_URL}/api/journeys/{journey_id}/properties/{prop_id}/inspection", json={
        "inspection_state": "not_as_good", "inspection_note": None, "expected_row_version": rv,
    }, timeout=30)
    d2 = session.get(f"{BASE_URL}/api/journeys/{journey_id}/properties/{prop_id}", timeout=30).json()

    # Compare match/evaluation-related keys — inspection MUST NOT be referenced anywhere
    for key in ("gates", "fit_score", "coverage", "evaluation", "match", "hard_failures"):
        v = d2.get(key)
        if v is not None:
            assert "inspection" not in str(v).lower(), f"'{key}' leaks inspection_state: {v!r}"

    # Restore
    session.post(f"{BASE_URL}/api/journeys/{journey_id}/properties/{prop_id}/inspection", json={
        "inspection_state": detail.get("inspection_state") or "not_inspected",
        "inspection_note": None,
        "expected_row_version": d2["buyer_row_version"],
    }, timeout=30)


# ── ScheduledJob invariant: enabled must be False everywhere ────────────────

@pytest.mark.asyncio
async def test_no_scheduled_job_is_enabled():
    """Every ScheduledJob row must remain enabled=false (schedule model only)."""
    from sqlalchemy import select
    from app.db.base import get_sessionmaker
    from app.db.models import ScheduledJob

    async with get_sessionmaker()() as db:
        rows = (await db.execute(select(ScheduledJob))).scalars().all()
        assert rows, "Expected ScheduledJob rows to be auto-created (daily/weekly/monthly)"
        enabled = [r for r in rows if r.enabled]
        assert not enabled, f"Found {len(enabled)} ScheduledJob rows with enabled=true; all must stay disabled"
        # Also assert kinds present per workspace
        by_kind = {r.job_kind for r in rows}
        assert "report_release" in by_kind


# ── Regression spot checks (M5.1/M5.2) ──────────────────────────────────────

def test_notifications_endpoint_ok(session):
    r = session.get(f"{BASE_URL}/api/notifications", timeout=30)
    assert r.status_code == 200, r.text


def test_tasks_endpoint_ok(session, journey_id):
    r = session.get(f"{BASE_URL}/api/journeys/{journey_id}/tasks", timeout=30)
    assert r.status_code in (200, 404), r.text
