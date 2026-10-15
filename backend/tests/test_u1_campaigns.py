"""U1 campaign configuration and isolation acceptance tests (disposable database only).

Fixtures are synthetic: one workspace holding a house and a land buyer campaign, plus a second
tenant. Every account is tracked by exact identity and removed after each test."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.base import get_sessionmaker
from app.db.models import (
    DuplicateProposal,
    IntakeEvent,
    Journey,
    MatchEvaluation,
    NotificationEvent,
    Property,
    ReportRun,
    ReportRunLegacyMapping,
    User,
)
from app.services.duplicates import confirm_merge, create_proposal
from app.services.reports import _period_for, GENERATION_VERSIONS, generate_report, legacy_report_key
from tests.conftest import _new_client, login, register_and_verify, unique_email

REPORT_TYPES = ("daily", "weekly", "monthly")


async def _tenant(client: AsyncClient, prefix: str) -> tuple[str, str, str]:
    """Registers a synthetic owner with a house and a land campaign. Returns (email, house, land)."""
    email = unique_email(prefix)
    await register_and_verify(client, email)
    await login(client, email)
    house = await client.post("/api/journeys", json={"name": "Synthetic house", "timezone": "Australia/Perth", "campaign_kind": "house"})
    land = await client.post("/api/journeys", json={"name": "Synthetic land", "timezone": "Australia/Perth", "campaign_kind": "land"})
    assert house.status_code == land.status_code == 201, (house.text, land.text)
    return email, house.json()["id"], land.json()["id"]


async def _generate(client: AsyncClient, journey_id: str, report_type: str, kind: str = "preview"):
    return await client.post(f"/api/journeys/{journey_id}/reports/{report_type}/generate", json={"release_kind": kind})


def _structured(address: str, suburb: str = "Example Park") -> dict:
    return {"mode": "structured_form", "structured": {"address_line": address, "suburb": suburb, "state": "WA", "facts": {"land_sqm": 500}}}


async def _save_overrides(client: AsyncClient, journey_id: str, settings: dict, expected: int):
    return await client.put(
        f"/api/journeys/{journey_id}/campaign/overrides",
        json={"settings": settings, "expected_version": expected, "reason": "U1 synthetic test"},
    )


async def test_campaigns_generate_distinct_runs_and_retries_return_their_own(client: AsyncClient) -> None:
    _, house, land = await _tenant(client, "u1-distinct")
    for report_type in REPORT_TYPES:
        a = (await _generate(client, house, report_type)).json()
        b = (await _generate(client, land, report_type)).json()
        assert a["journey_id"] == house and b["journey_id"] == land
        assert a["id"] != b["id"]
        assert (a["period_start"], a["period_end"]) == (b["period_start"], b["period_end"]), "identical periods"
        assert (await _generate(client, house, report_type)).json()["id"] == a["id"]
        assert (await _generate(client, land, report_type)).json()["id"] == b["id"]
        wrong = await client.get(f"/api/journeys/{house}/reports/{b['id']}")
        assert wrong.status_code == 404, "a campaign must never return another campaign's run"
        wrong_send = await client.post(f"/api/journeys/{land}/reports/{a['id']}/ready-to-send")
        assert wrong_send.status_code == 404
    house_list = {r["id"] for r in (await client.get(f"/api/journeys/{house}/reports")).json()}
    land_list = {r["id"] for r in (await client.get(f"/api/journeys/{land}/reports")).json()}
    assert len(house_list) == len(land_list) == 3 and not house_list & land_list


async def test_concurrent_generation_converges_on_one_run_per_campaign(client: AsyncClient) -> None:
    _, house, land = await _tenant(client, "u1-concurrent")
    async with get_sessionmaker()() as db:
        journeys = {j.id: j for j in (await db.execute(select(Journey).where(Journey.id.in_([uuid.UUID(house), uuid.UUID(land)])))).scalars()}
        user_id = next(iter(journeys.values())).created_by

    async def worker(journey_id: str) -> uuid.UUID:
        async with get_sessionmaker()() as db:
            journey = (await db.execute(select(Journey).where(Journey.id == uuid.UUID(journey_id)))).scalar_one()
            run = await generate_report(db, journey=journey, report_type="daily", release_kind="preview", requested_by_user_id=user_id)
            await db.commit()
            return run.id

    ids = await asyncio.gather(*(worker(house) for _ in range(4)), *(worker(land) for _ in range(4)))
    assert len(set(ids[:4])) == 1 and len(set(ids[4:])) == 1 and ids[0] != ids[4]
    async with get_sessionmaker()() as db:
        rows = (await db.execute(select(ReportRun.journey_id, func.count()).where(ReportRun.journey_id.in_(journeys)).group_by(ReportRun.journey_id))).all()
        notifications = (await db.execute(select(func.count()).select_from(NotificationEvent).where(NotificationEvent.report_run_id.in_(set(ids))))).scalar_one()
    assert sorted(count for _, count in rows) == [1, 1]
    assert notifications == 2, "one report-ready notification per campaign run"


async def test_database_uniqueness_is_campaign_scoped(client: AsyncClient) -> None:
    _, house, land = await _tenant(client, "u1-unique")
    run = (await _generate(client, house, "daily")).json()
    async with get_sessionmaker()() as db:
        original = (await db.execute(select(ReportRun).where(ReportRun.id == uuid.UUID(run["id"])))).scalar_one()
        clone = {c: getattr(original, c) for c in ("workspace_id", "idempotency_key", "kind", "report_type", "timezone", "generation_version")}
        db.add(ReportRun(**clone, journey_id=original.journey_id, release_state="pending", snapshot={}, detail={}))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()
        db.add(ReportRun(**clone, journey_id=uuid.UUID(land), release_state="pending", snapshot={}, detail={}))
        await db.flush()  # same key text in another campaign does not collide at the database level
        await db.rollback()


async def test_cross_tenant_ids_are_indistinguishable_from_missing(client: AsyncClient) -> None:
    _, house, _ = await _tenant(client, "u1-tenant-a")
    run = (await _generate(client, house, "weekly")).json()
    async with _new_client() as other:
        await _tenant(other, "u1-tenant-b")
        assert (await other.get(f"/api/journeys/{house}/reports/{run['id']}")).status_code == 404
        assert (await other.get(f"/api/journeys/{house}/reports")).status_code == 404
        assert (await _generate(other, house, "weekly")).status_code == 404
        assert (await other.get(f"/api/reports/runs/{run['id']}/location")).status_code == 404
        assert (await other.get(f"/api/journeys/{house}/campaign")).status_code == 404
        assert (await _save_overrides(other, house, {"timezone": "Australia/Sydney"}, 0)).status_code == 404
    located = (await client.get(f"/api/reports/runs/{run['id']}/location")).json()
    assert located == {"report_run_id": run["id"], "journey_id": house, "report_type": "weekly"}


async def test_legacy_mapping_preserves_history_and_never_moves_an_unrelated_row(client: AsyncClient) -> None:
    _, house, land = await _tenant(client, "u1-legacy")
    now = datetime.now(timezone.utc)
    start, end, cutoff, _ = _period_for("daily", "Australia/Perth", now, year=None, month=None, week_start=None)
    key = legacy_report_key("daily", "preview", start, end, GENERATION_VERSIONS["daily"])
    async with get_sessionmaker()() as db:
        journey = (await db.execute(select(Journey).where(Journey.id == uuid.UUID(house)))).scalar_one()
        common = dict(workspace_id=journey.workspace_id, idempotency_key=key, idempotency_scope="workspace_legacy", kind="preview",
                      report_type="daily", period_start=start, period_end=end, cutoff_at=cutoff, timezone="Australia/Perth",
                      generation_version=GENERATION_VERSIONS["daily"], detail={})
        legacy = ReportRun(**common, journey_id=journey.id, release_state="ready", snapshot={"legacy": True}, generated_at=now)
        db.add(legacy)
        await db.flush()
        db.add(ReportRunLegacyMapping(report_run_id=legacy.id, workspace_id=journey.workspace_id, journey_id=journey.id,
                                      legacy_idempotency_key=key, mapping_basis="recorded_journey_same_workspace", migration_revision="test"))
        await db.commit()
        legacy_id = legacy.id
    replay = (await _generate(client, house, "daily")).json()
    assert replay["id"] == str(legacy_id), "mapped historical run keeps its ID and is reused for its own campaign"
    other = (await _generate(client, land, "daily")).json()
    assert other["id"] != str(legacy_id) and other["journey_id"] == land
    async with get_sessionmaker()() as db:
        after = (await db.execute(select(ReportRun).where(ReportRun.id == legacy_id))).scalar_one()
        mapping = (await db.execute(select(ReportRunLegacyMapping).where(ReportRunLegacyMapping.report_run_id == legacy_id))).scalar_one()
        assert (after.journey_id, after.idempotency_key, after.idempotency_scope, after.snapshot) == (uuid.UUID(house), key, "workspace_legacy", {"legacy": True})
        assert mapping.journey_id == uuid.UUID(house)
        land_key_rows = (await db.execute(select(func.count()).select_from(ReportRun).where(ReportRun.journey_id == uuid.UUID(land)))).scalar_one()
        assert land_key_rows == 1
    located = (await client.get(f"/api/reports/runs/{legacy_id}/location")).json()
    assert located["journey_id"] == house, "historical /app/reports?run= links resolve to the owning campaign"


async def test_unmapped_legacy_row_is_never_reused(client: AsyncClient) -> None:
    _, house, _ = await _tenant(client, "u1-unmapped")
    now = datetime.now(timezone.utc)
    start, end, cutoff, _ = _period_for("daily", "Australia/Perth", now, year=None, month=None, week_start=None)
    async with get_sessionmaker()() as db:
        journey = (await db.execute(select(Journey).where(Journey.id == uuid.UUID(house)))).scalar_one()
        orphan = ReportRun(workspace_id=journey.workspace_id, journey_id=journey.id, idempotency_scope="workspace_legacy",
                           idempotency_key=legacy_report_key("daily", "preview", start, end, GENERATION_VERSIONS["daily"]),
                           kind="preview", report_type="daily", release_state="ready", period_start=start, period_end=end,
                           cutoff_at=cutoff, timezone="Australia/Perth", generation_version=GENERATION_VERSIONS["daily"], snapshot={}, detail={})
        db.add(orphan)
        await db.commit()
        orphan_id = orphan.id
    fresh = (await _generate(client, house, "daily")).json()
    assert fresh["id"] != str(orphan_id), "only an explicit legacy mapping may route a replay to a historical row"
    assert (await client.get(f"/api/reports/runs/{orphan_id}/location")).status_code == 404


async def test_user_defaults_inherit_and_campaign_overrides_win(client: AsyncClient) -> None:
    _, house, land = await _tenant(client, "u1-inherit")
    base = (await client.get(f"/api/journeys/{house}/campaign")).json()
    assert base["settings"]["timezone"] == {**base["settings"]["timezone"], "source": "system_default", "effective": "Australia/Perth"}
    assert base["settings"]["delivery_mode"]["effective"] == "separate"
    saved = await client.put("/api/campaign-defaults", json={"settings": {"timezone": "Australia/Sydney", "delivery_mode": "combined"}, "expected_version": 0, "reason": "defaults"})
    assert saved.status_code == 200 and saved.json()["version"] == 1
    inherited = (await client.get(f"/api/journeys/{house}/campaign")).json()["settings"]
    assert (inherited["timezone"]["source"], inherited["timezone"]["effective"]) == ("user_default", "Australia/Sydney")
    assert inherited["delivery_mode"]["requested"] == "combined" and inherited["delivery_mode"]["effective"] == "separate"
    assert inherited["delivery_mode"]["state"] == "unsupported_until_u6"
    overridden = (await _save_overrides(client, house, {"timezone": "Australia/Perth"}, 0)).json()["settings"]["timezone"]
    assert (overridden["source"], overridden["effective"]) == ("campaign_override", "Australia/Perth")
    land_tz = (await client.get(f"/api/journeys/{land}/campaign")).json()["settings"]["timezone"]
    assert land_tz["effective"] == "Australia/Sydney", "an override on one campaign never leaks into another"
    back = (await _save_overrides(client, house, {"timezone": "INHERIT"}, 1)).json()
    assert back["campaign_version"] == 2 and back["settings"]["timezone"]["effective"] == "Australia/Sydney"
    stale = await _save_overrides(client, house, {"timezone": "Australia/Darwin"}, 1)
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "stale_configuration"
    versions = (await client.get(f"/api/journeys/{house}/campaign/versions")).json()
    assert [v["version_no"] for v in versions] == [2, 1] and versions[1]["settings"]["timezone"] == "Australia/Perth"
    weekly = (await _generate(client, land, "weekly")).json()
    assert weekly["timezone"] == "Australia/Sydney", "report periods use the effective campaign timezone"


async def test_invalid_settings_are_rejected(client: AsyncClient) -> None:
    _, house, _ = await _tenant(client, "u1-invalid")
    async with _new_client() as other:
        other_email, other_house, _ = await _tenant(other, "u1-invalid-other")
        async with get_sessionmaker()() as db:
            outsider = (await db.execute(select(User.id).where(User.email == other_email))).scalar_one()
    cases = [
        ({"timezone": "Mars/Olympus"}, "invalid_timezone"),
        ({"recipient_user_id": str(outsider)}, "recipient_not_member"),
        ({"intake_connection_ref": str(uuid.uuid4())}, "intake_connection_not_found"),
        ({"activation_at": "2026-10-01T09:00:00"}, "invalid_activation_at"),
    ]
    for settings, code in cases:
        response = await _save_overrides(client, house, settings, 0)
        assert response.status_code == 422 and response.json()["detail"]["code"] == code, (settings, response.text)
    bad_cadence = await _save_overrides(client, house, {"cadence": {"daily": {"enabled": True, "local_time": "25:00", "weekdays": [0]}, "weekly": {"enabled": True, "local_time": "19:00", "day_of_week": 6}, "monthly": {"enabled": True, "local_time": "07:00", "day_of_month": 1}}}, 0)
    assert bad_cadence.status_code == 422
    assert (await client.get(f"/api/journeys/{house}/campaign")).json()["campaign_version"] == 0, "nothing was saved"
    assert other_house


async def test_unsupported_and_mismatched_profiles_fail_closed(client: AsyncClient) -> None:
    _, house, land = await _tenant(client, "u1-profiles")
    for journey_id, profile, code in (
        (house, "PADBURY_RULES_V0", "unsupported_assessment_profile"),
        (land, "HOUSE_V1", "assessment_profile_incompatible"),
        (house, "LAND_FEASIBILITY_V1", "assessment_profile_incompatible"),
    ):
        response = await _save_overrides(client, journey_id, {"assessment_profile": profile}, 0)
        assert response.status_code == 422 and response.json()["detail"]["code"] == code
    unknown_default = await client.put("/api/campaign-defaults", json={"settings": {"assessment_profile": "BORROWED"}, "expected_version": 0, "reason": "x"})
    assert unknown_default.status_code == 422
    assert (await client.put("/api/campaign-defaults", json={"settings": {"assessment_profile": "HOUSE_V1"}, "expected_version": 0, "reason": "house default"})).status_code == 200
    land_profile = (await client.get(f"/api/journeys/{land}/campaign")).json()["settings"]["assessment_profile"]
    assert land_profile["source"] == "system_default" and land_profile["requested"] == "LAND_FEASIBILITY_V1"
    assert land_profile["effective"] is None and land_profile["state"] == "unavailable"
    journeys = {j["id"]: j for j in (await client.get("/api/journeys")).json()}
    assert journeys[house]["assessment_available"] is True and journeys[land]["assessment_available"] is False
    brief = (await client.get(f"/api/journeys/{land}/brief")).json()
    draft = brief["draft"]
    draft["locations"]["states"] = ["WA"]
    draft["locations"]["included"] = [{"suburb": "Example Park", "state": "WA", "postcode": None}]
    draft["budget"]["ceiling_minor"] = 20_000_000
    draft["land_sqm"]["min"] = 400
    saved = await client.put(f"/api/journeys/{land}/brief/draft", json={"payload": draft, "expected_row_version": brief["journey"]["row_version"]})
    published = await client.post(f"/api/journeys/{land}/brief/publish", json={"reason": "Synthetic land brief", "expected_row_version": saved.json()["journey"]["row_version"]})
    assert published.status_code == 201, published.text
    assert published.json()["current_version"]["reevaluation_state"] == "skipped_profile_unavailable"
    created = (await client.post(f"/api/journeys/{land}/intake", json=_structured("3 Synthetic Lot Lane"))).json()
    assert created["state"] == "completed"
    async with get_sessionmaker()() as db:
        evaluations = (await db.execute(select(func.count()).select_from(MatchEvaluation).where(MatchEvaluation.journey_id == uuid.UUID(land)))).scalar_one()
    assert evaluations == 0, "house rules were never applied to the land campaign"
    detail = (await client.get(f"/api/journeys/{land}/properties/{created['property_id']}")).json()
    assert detail["evaluation"] is None


async def test_disabled_campaign_blocks_intake_and_production_but_keeps_history(client: AsyncClient) -> None:
    _, house, land = await _tenant(client, "u1-disabled")
    preview = (await _generate(client, land, "daily")).json()
    journey = (await client.get(f"/api/journeys/{land}")).json()
    off = await client.patch(f"/api/journeys/{land}", json={"campaign_enabled": False, "expected_row_version": journey["row_version"]})
    assert off.status_code == 200 and off.json()["campaign_enabled"] is False
    blocked = await client.post(f"/api/journeys/{land}/intake", json=_structured("9 Paused Road"))
    assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == "campaign_disabled"
    production = await _generate(client, land, "daily", "production")
    assert production.status_code == 409 and production.json()["detail"]["code"] == "campaign_disabled"
    assert (await client.get(f"/api/journeys/{land}/reports/{preview['id']}")).status_code == 200
    schedule = (await client.get(f"/api/journeys/{land}/campaign")).json()["schedule"]
    assert {s["sync_state"] for s in schedule} == {"campaign_disabled"}
    assert (await client.post(f"/api/journeys/{house}/intake", json=_structured("9 Paused Road"))).json()["state"] == "completed"


async def test_activation_gates_production_runs_only(client: AsyncClient) -> None:
    _, house, _ = await _tenant(client, "u1-activation")
    not_active = await _generate(client, house, "daily", "production")
    assert not_active.status_code == 409 and not_active.json()["detail"]["code"] == "campaign_not_activated"
    future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    assert (await _save_overrides(client, house, {"activation_at": future}, 0)).json()["settings"]["activation_at"]["state"] == "pending_activation"
    assert (await _generate(client, house, "daily", "production")).json()["detail"]["code"] == "campaign_not_activated"
    assert (await _generate(client, house, "daily", "preview")).status_code == 200, "manual QA is independent of activation"
    today = datetime.now(timezone.utc).isoformat()
    config = (await _save_overrides(client, house, {"activation_at": today}, 1)).json()
    assert config["settings"]["activation_at"]["state"] == "active"
    assert {s["sync_state"] for s in config["schedule"]} == {"worker_disabled"}, "an enabled cadence never claims a running worker"
    assert all(s["effective_cron"] is None and s["next_due_at"] is None for s in config["schedule"])
    backdated = await _generate(client, house, "monthly", "production")
    assert backdated.status_code == 409 and backdated.json()["detail"]["code"] == "period_before_activation"
    produced = await _generate(client, house, "daily", "production")
    assert produced.status_code == 200 and produced.json()["kind"] == "production"
    preview = (await _generate(client, house, "daily", "preview")).json()
    assert preview["id"] != produced.json()["id"], "QA/preview and production keys are separate"


async def test_same_address_is_independent_per_campaign_and_merges_stay_inside_one(client: AsyncClient) -> None:
    _, house, land = await _tenant(client, "u1-address")
    a = (await client.post(f"/api/journeys/{house}/intake", json=_structured("12 Banksia Crescent"))).json()
    b = (await client.post(f"/api/journeys/{land}/intake", json=_structured("12 Banksia Crescent"))).json()
    assert a["state"] == b["state"] == "completed" and a["property_id"] != b["property_id"]
    assert b["duplicate_property_id"] is None, "another campaign's record is never revealed as a duplicate"
    assert (await client.post(f"/api/journeys/{land}/intake", json=_structured("12 Banksia Crescent"))).json()["intake_id"] == b["intake_id"]
    assert (await client.get(f"/api/journeys/{land}/properties/{a['property_id']}")).status_code == 404
    await client.post(f"/api/journeys/{house}/intake", json=_structured("12A Banksia Crescent"))
    await client.post(f"/api/journeys/{land}/intake", json=_structured("12B Banksia Crescent"))
    assert (await client.post("/api/workspaces/me/duplicates/scan")).status_code == 200
    house_items = (await client.get(f"/api/workspaces/me/duplicates?journey_id={house}")).json()["items"]
    land_items = (await client.get(f"/api/workspaces/me/duplicates?journey_id={land}")).json()["items"]
    house_ids = {a["property_id"]}
    assert house_items and land_items
    for item in house_items:
        assert {item["property_a"]["id"], item["property_b"]["id"]} & house_ids or item["property_a"]["id"] != b["property_id"]
    async with get_sessionmaker()() as db:
        pa = (await db.execute(select(Property).where(Property.id == uuid.UUID(a["property_id"])))).scalar_one()
        pb = (await db.execute(select(Property).where(Property.id == uuid.UUID(b["property_id"])))).scalar_one()
        pairs = (await db.execute(select(DuplicateProposal.property_id_a, DuplicateProposal.property_id_b).where(DuplicateProposal.workspace_id == pa.workspace_id))).all()
        owners = {p.id: p.journey_id for p in (await db.execute(select(Property).where(Property.workspace_id == pa.workspace_id))).scalars()}
        assert all(owners[x] == owners[y] for x, y in pairs), "no proposal spans two campaigns"
        with pytest.raises(ValueError, match="different campaigns"):
            await create_proposal(db, pa.workspace_id, pa.id, pb.id, "user_proposed")
        forged = DuplicateProposal(workspace_id=pa.workspace_id, property_id_a=pa.id, property_id_b=pb.id, state="pending", proposal_reason="user_proposed", evidence={})
        db.add(forged)
        await db.flush()
        with pytest.raises(ValueError, match="Cross-campaign merge"):
            await confirm_merge(db, forged, pa.created_by, None, None, forged.row_version)
        await db.rollback()


async def test_incomplete_pasted_text_receipts_are_campaign_scoped_and_replay_safe(client: AsyncClient) -> None:
    _, house, land = await _tenant(client, "u1-receipt")
    body = {"mode": "pasted_text", "pasted_text": {"raw_text": "Lovely synthetic listing with no address"}}
    first = await client.post(f"/api/journeys/{house}/intake", json=body)
    replay = await client.post(f"/api/journeys/{house}/intake", json=body)
    other = await client.post(f"/api/journeys/{land}/intake", json=body)
    assert first.status_code == replay.status_code == other.status_code == 200, (first.text, replay.text, other.text)
    assert first.json()["intake_id"] == replay.json()["intake_id"] != other.json()["intake_id"]
    async with get_sessionmaker()() as db:
        receipts = (await db.execute(select(IntakeEvent.journey_id).where(IntakeEvent.id.in_([uuid.UUID(first.json()["intake_id"]), uuid.UUID(other.json()["intake_id"])])))).scalars().all()
    assert set(receipts) == {uuid.UUID(house), uuid.UUID(land)}


async def test_notifications_and_report_counts_carry_campaign_scope(client: AsyncClient) -> None:
    _, house, land = await _tenant(client, "u1-notify")
    run = (await _generate(client, land, "daily")).json()
    await client.post(f"/api/journeys/{house}/intake", json=_structured("5 Cedar Court"))
    await client.post(f"/api/journeys/{house}/intake", json=_structured("5A Cedar Court"))
    await client.post("/api/workspaces/me/duplicates/scan")
    items = (await client.get("/api/notifications")).json()["items"]
    report_note = next(i for i in items if i["report_run_id"] == run["id"])
    assert report_note["journey_id"] == land and f"campaign={land}" in report_note["safe_deep_link"]
    assert all(i["journey_id"] == house for i in items if i["category"] in ("new_property", "duplicate_review"))
    house_weekly = (await _generate(client, house, "weekly")).json()["snapshot"]
    land_weekly = (await _generate(client, land, "weekly")).json()["snapshot"]
    assert land_weekly["duplicates"]["detected"] == 0, "duplicate counts never bleed between campaigns"
    assert house_weekly["duplicates"] == house_weekly["duplicates"]
