"""Property workspace API: fixtures, workflow, waivers, notes/tasks, concurrency, re-evaluation, tenancy."""

from typing import Any

from httpx import ASGITransport, AsyncClient

from server import app
from tests.conftest import login, register_and_verify, unique_email

BASE = "https://property-find-1.preview.emergentagent.com"


async def _tenant_with_properties(prefix: str) -> tuple[AsyncClient, str, dict[str, dict[str, Any]]]:
    c = AsyncClient(transport=ASGITransport(app=app), base_url=BASE)
    email = unique_email(prefix)
    await register_and_verify(c, email)
    await login(c, email)
    journey = (await c.post("/api/journeys", json={"name": f"{prefix} journey"})).json()
    jid = str(journey["id"])
    brief = (await c.get(f"/api/journeys/{jid}/brief")).json()
    draft = brief["draft"]
    draft["budget"]["ceiling_minor"] = 1_300_000_00
    draft["budget"]["preferred_max_minor"] = 1_200_000_00
    draft["beds"] = {"mode": "hard", "min": 3, "max": None}
    draft["land_sqm"] = {"mode": "hard", "min": 400, "max": None}
    draft["locations"]["states"] = ["WA"]
    draft["renovation"]["level"] = "moderate"
    r = await c.put(
        f"/api/journeys/{jid}/brief/draft",
        json={"payload": draft, "expected_row_version": brief["journey"]["row_version"]},
    )
    assert r.status_code == 200, r.text
    r = await c.post(
        f"/api/journeys/{jid}/brief/publish",
        json={"reason": "test brief", "expected_row_version": r.json()["journey"]["row_version"]},
    )
    assert r.status_code == 201, r.text
    r = await c.post("/api/dev/load-demo-properties", json={"journey_id": jid})
    assert r.status_code == 201, r.text
    assert r.json()["created"] == 7
    items = (await c.get(f"/api/journeys/{jid}/properties")).json()
    return c, jid, {p["legacy_ref"]: p for p in items}


async def test_fixture_outcomes_market_state_and_unit_suffixes() -> None:
    c, jid, by_ref = await _tenant_with_properties("props")
    try:
        assert set(by_ref) == {f"DEMO-00{i}" for i in range(1, 8)}
        assert by_ref["DEMO-001"]["evaluation"]["verdict"] == "pass"
        assert by_ref["DEMO-002"]["evaluation"]["verdict"] == "unknown"
        assert by_ref["DEMO-003"]["evaluation"]["verdict"] == "fail"
        assert by_ref["DEMO-004"]["evaluation"]["verdict"] == "unknown"
        assert by_ref["DEMO-006"]["evaluation"]["verdict"] == "unknown"
        # 81A and 81C are separate properties with their own units
        assert by_ref["DEMO-005"]["unit"] == "A" and by_ref["DEMO-006"]["unit"] == "C"
        assert by_ref["DEMO-005"]["id"] != by_ref["DEMO-006"]["id"]
        # Market under offer is a source state; buyer state stays Archived
        p7 = by_ref["DEMO-007"]
        assert p7["campaign"]["market_state"] == "under_offer" and p7["buyer_state"] == "archived"
        # Loading the fixture again creates nothing
        again = await c.post("/api/dev/load-demo-properties", json={"journey_id": jid})
        assert again.json()["created"] == 0
        # Filters
        queue = (
            await c.get(
                f"/api/journeys/{jid}/properties", params={"buyer_state": "reviewing", "verdict": "pass"}
            )
        ).json()
        assert [p["legacy_ref"] for p in queue] == ["DEMO-001"]
        found = (await c.get(f"/api/journeys/{jid}/properties", params={"q": "81a"})).json()
        assert [p["legacy_ref"] for p in found] == ["DEMO-005"]
    finally:
        await c.aclose()


async def test_hard_failure_cannot_be_promoted_until_waived_and_gate_stays_fail() -> None:
    c, jid, by_ref = await _tenant_with_properties("promo")
    try:
        p3 = by_ref["DEMO-003"]
        pid = p3["id"]
        # DEMO-003 is Rejected in the fixture; go back to reviewing then attempt to shortlist
        r = await c.post(
            f"/api/journeys/{jid}/properties/{pid}/stage",
            json={"to_state": "reviewing", "expected_row_version": p3["buyer_row_version"]},
        )
        assert r.status_code == 200, r.text
        rv = r.json()["buyer_row_version"]
        blocked = await c.post(
            f"/api/journeys/{jid}/properties/{pid}/stage",
            json={"to_state": "shortlisted", "expected_row_version": rv},
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "hard_failure_cannot_be_promoted"
        assert blocked.json()["detail"]["failing"] == ["land_sqm"]
        # A waiver on a passing gate is refused
        bad = await c.post(
            f"/api/journeys/{jid}/properties/{pid}/waivers",
            json={"criterion": "beds", "reason": "not applicable"},
        )
        assert bad.status_code == 422
        waived = await c.post(
            f"/api/journeys/{jid}/properties/{pid}/waivers",
            json={"criterion": "land_sqm", "reason": "Corner block; we accept the smaller land."},
        )
        assert waived.status_code == 201, waived.text
        body = waived.json()
        assert body["waived_criteria"] == ["land_sqm"]
        assert body["evaluation"]["verdict"] == "fail"  # never converted to Pass
        assert (
            next(g for g in body["evaluation"]["gates"] if g["criterion"] == "land_sqm")["outcome"] == "fail"
        )
        ok = await c.post(
            f"/api/journeys/{jid}/properties/{pid}/stage",
            json={"to_state": "shortlisted", "expected_row_version": body["buyer_row_version"]},
        )
        assert ok.status_code == 200, ok.text
        assert ok.json()["buyer_state"] == "shortlisted"
        kinds = [a["kind"] for a in ok.json()["activity"]]
        assert "waiver_recorded" in kinds and "stage_changed" in kinds
        # The brief itself is untouched
        brief = (await c.get(f"/api/journeys/{jid}/brief")).json()
        assert brief["current_version"]["payload"]["land_sqm"]["min"] == 400
    finally:
        await c.aclose()


async def test_transitions_saved_notes_tasks_and_optimistic_concurrency() -> None:
    c, jid, by_ref = await _tenant_with_properties("flow")
    try:
        pid = by_ref["DEMO-001"]["id"]
        rv = by_ref["DEMO-001"]["buyer_row_version"]
        illegal = await c.post(
            f"/api/journeys/{jid}/properties/{pid}/stage",
            json={"to_state": "settled", "expected_row_version": rv},
        )
        assert illegal.status_code == 409 and illegal.json()["detail"]["code"] == "transition_not_allowed"
        stale = await c.post(
            f"/api/journeys/{jid}/properties/{pid}/stage",
            json={"to_state": "shortlisted", "expected_row_version": rv + 5},
        )
        assert stale.status_code == 409 and stale.json()["detail"]["code"] == "stale_write"
        moved = await c.post(
            f"/api/journeys/{jid}/properties/{pid}/stage",
            json={"to_state": "shortlisted", "expected_row_version": rv},
        )
        assert moved.status_code == 200
        saved = await c.post(
            f"/api/journeys/{jid}/properties/{pid}/saved",
            json={"saved": True, "expected_row_version": moved.json()["buyer_row_version"]},
        )
        assert saved.status_code == 200 and saved.json()["saved"] is True
        saved_refs = {
            p["legacy_ref"]
            for p in (await c.get(f"/api/journeys/{jid}/properties", params={"saved": "true"})).json()
        }
        assert saved_refs == {"DEMO-001", "DEMO-005"}

        note = await c.post(
            f"/api/journeys/{jid}/properties/{pid}/notes", json={"body": "Ask about the rear boundary."}
        )
        assert note.status_code == 201
        n = note.json()["notes"][0]
        conflict = await c.patch(
            f"/api/journeys/{jid}/properties/{pid}/notes/{n['id']}",
            json={"body": "edited", "expected_row_version": 99},
        )
        assert conflict.status_code == 409
        edited = await c.patch(
            f"/api/journeys/{jid}/properties/{pid}/notes/{n['id']}",
            json={
                "body": "Ask about the rear boundary and easements.",
                "expected_row_version": n["row_version"],
            },
        )
        assert edited.status_code == 200 and edited.json()["notes"][0]["row_version"] == n["row_version"] + 1

        task = await c.post(
            f"/api/journeys/{jid}/properties/{pid}/tasks", json={"title": "Request the survey"}
        )
        assert task.status_code == 201
        t = task.json()["tasks"][0]
        done = await c.patch(
            f"/api/journeys/{jid}/properties/{pid}/tasks/{t['id']}",
            json={"done": True, "expected_row_version": t["row_version"]},
        )
        assert done.status_code == 200 and done.json()["tasks"][0]["done"] is True
        today = (await c.get(f"/api/journeys/{jid}/today")).json()
        assert today["open_tasks"] == 0 and today["total_properties"] == 7 and today["known_failures"] == 1
    finally:
        await c.aclose()


async def test_publishing_a_new_brief_reevaluates_and_preserves_old_scores() -> None:
    c, jid, by_ref = await _tenant_with_properties("republish")
    try:
        first = by_ref["DEMO-001"]["evaluation"]
        assert first["brief_version_no"] == 1 and first["verdict"] == "pass"
        brief = (await c.get(f"/api/journeys/{jid}/brief")).json()
        draft = brief["draft"]
        draft["land_sqm"]["min"] = 700  # DEMO-001 has 690 m²
        r = await c.put(
            f"/api/journeys/{jid}/brief/draft",
            json={"payload": draft, "expected_row_version": brief["journey"]["row_version"]},
        )
        r = await c.post(
            f"/api/journeys/{jid}/brief/publish",
            json={"reason": "tighter land rule", "expected_row_version": r.json()["journey"]["row_version"]},
        )
        assert r.status_code == 201, r.text
        assert r.json()["current_version"]["reevaluation_state"] == "completed"
        versions = (await c.get(f"/api/journeys/{jid}/brief/versions")).json()
        assert [v["reevaluation_state"] for v in versions] == ["completed", "completed"]
        p1 = (await c.get(f"/api/journeys/{jid}/properties/{by_ref['DEMO-001']['id']}")).json()
        assert p1["evaluation"]["brief_version_no"] == 2
        assert p1["evaluation"]["verdict"] == "fail"
        assert p1["evaluation"]["input_hash"] != first["input_hash"]
    finally:
        await c.aclose()


async def test_compare_limits_and_cross_tenant_isolation() -> None:
    a, a_jid, a_props = await _tenant_with_properties("iso-a")
    b, b_jid, b_props = await _tenant_with_properties("iso-b")
    try:
        ids = [a_props[f"DEMO-00{i}"]["id"] for i in range(1, 6)]
        too_many = await a.get(f"/api/journeys/{a_jid}/properties/compare", params={"ids": ",".join(ids)})
        assert too_many.status_code == 422
        four = await a.get(f"/api/journeys/{a_jid}/properties/compare", params={"ids": ",".join(ids[:4])})
        assert four.status_code == 200 and len(four.json()) == 4

        foreign = b_props["DEMO-001"]["id"]
        assert (await a.get(f"/api/journeys/{b_jid}/properties")).status_code == 404
        assert (await a.get(f"/api/journeys/{a_jid}/properties/{foreign}")).status_code == 404
        assert (await a.get(f"/api/journeys/{b_jid}/properties/{foreign}")).status_code == 404
        assert (
            await a.get(f"/api/journeys/{a_jid}/properties/compare", params={"ids": foreign})
        ).status_code == 404
        assert (
            await a.post(f"/api/journeys/{b_jid}/properties/{foreign}/notes", json={"body": "intrusion"})
        ).status_code == 404
        assert (
            await a.post(
                f"/api/journeys/{a_jid}/properties/{foreign}/stage",
                json={"to_state": "shortlisted", "expected_row_version": 1},
            )
        ).status_code == 404
        assert (await a.get(f"/api/journeys/{b_jid}/today")).status_code == 404
        untouched = (await b.get(f"/api/journeys/{b_jid}/properties/{foreign}")).json()
        assert untouched["notes"] == [] and untouched["buyer_state"] == "reviewing"
    finally:
        await a.aclose()
        await b.aclose()
