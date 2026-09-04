"""Versioned buying brief: validation blockers, immutable versions and optimistic concurrency."""

from httpx import ASGITransport, AsyncClient

from app.schemas.brief import Area, default_brief, validate_for_publish
from server import app
from tests.conftest import login, register_and_verify, unique_email

BASE = "https://property-find-1.preview.emergentagent.com"


def _valid_payload() -> dict[str, object]:
    brief = default_brief()
    brief.budget.ceiling_minor = 1_200_000_00
    brief.budget.preferred_max_minor = 1_100_000_00
    brief.land_sqm.min = 400
    brief.locations.states = ["WA"]
    return brief.model_dump()


async def _owner() -> tuple[AsyncClient, str]:
    c = AsyncClient(transport=ASGITransport(app=app), base_url=BASE)
    email = unique_email("brief")
    await register_and_verify(c, email)
    await login(c, email)
    journey = (await c.post("/api/journeys", json={"name": "Brief journey"})).json()
    return c, str(journey["id"])


def test_contradictory_bounds_block_publication() -> None:
    brief = default_brief()
    brief.budget.ceiling_minor = 900_000_00
    brief.budget.preferred_min_minor = 950_000_00
    brief.budget.preferred_max_minor = 940_000_00
    brief.beds.min = 5
    brief.beds.max = 3
    fields = {e.field for e in validate_for_publish(brief)}
    assert "budget.preferred_max_minor" in fields
    assert "beds.max" in fields


def test_zero_enabled_weight_blocks_publication() -> None:
    brief = default_brief()
    brief.budget.ceiling_minor = 1_000_000_00
    brief.land_sqm.min = 400
    brief.locations.states = ["WA"]
    brief.weights.price_enabled = False
    brief.weights.land_enabled = False
    brief.weights.location_enabled = False
    brief.weights.condition_enabled = False
    assert "weights" in {e.field for e in validate_for_publish(brief)}


def test_unknown_criteria_never_block_publication() -> None:
    brief = default_brief()
    brief.budget.mode = "unknown"
    brief.land_sqm.mode = "unknown"
    brief.locations.states = ["WA"]
    assert validate_for_publish(brief) == []


def test_hard_rule_without_a_value_is_blocked() -> None:
    brief = default_brief()
    brief.budget.ceiling_minor = 1_000_000_00
    brief.locations.states = ["WA"]
    brief.beds.mode = "hard"
    fields = {e.field for e in validate_for_publish(brief)}
    assert "beds.min" in fields
    assert "land_sqm.min" in fields


def test_area_cannot_be_included_and_excluded() -> None:
    brief = default_brief()
    brief.budget.ceiling_minor = 1_000_000_00
    brief.land_sqm.min = 400
    brief.locations.included = [Area(suburb="Woodlands", state="WA")]
    brief.locations.excluded = [Area(suburb="woodlands ", state="WA")]
    brief = brief.model_validate(brief.model_dump())
    assert "locations.excluded" in {e.field for e in validate_for_publish(brief)}


async def test_publish_creates_immutable_versions_with_actor_and_reason() -> None:
    c, journey_id = await _owner()
    try:
        brief = (await c.get(f"/api/journeys/{journey_id}/brief")).json()
        row_version = brief["journey"]["row_version"]

        saved = await c.put(
            f"/api/journeys/{journey_id}/brief/draft",
            json={"payload": _valid_payload(), "expected_row_version": row_version},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["validation"] == []
        row_version = saved.json()["journey"]["row_version"]

        published = await c.post(
            f"/api/journeys/{journey_id}/brief/publish",
            json={"reason": "First published brief", "expected_row_version": row_version},
        )
        assert published.status_code == 201, published.text
        first = published.json()["current_version"]
        assert first["version_no"] == 1
        assert first["reason"] == "First published brief"
        assert first["reevaluation_state"] == "queued"

        # A second publication adds a version and leaves version 1 untouched.
        row_version = published.json()["journey"]["row_version"]
        payload = _valid_payload()
        payload["beds"] = {"mode": "preference", "min": 4, "max": None}
        saved = await c.put(
            f"/api/journeys/{journey_id}/brief/draft",
            json={"payload": payload, "expected_row_version": row_version},
        )
        row_version = saved.json()["journey"]["row_version"]
        second = await c.post(
            f"/api/journeys/{journey_id}/brief/publish",
            json={"reason": "Added bedroom preference", "expected_row_version": row_version},
        )
        assert second.status_code == 201

        versions = (await c.get(f"/api/journeys/{journey_id}/brief/versions")).json()
        assert [v["version_no"] for v in versions] == [2, 1]
        assert versions[1]["payload"]["beds"]["min"] is None
        assert versions[0]["payload"]["beds"]["min"] == 4
    finally:
        await c.aclose()


async def test_invalid_brief_publication_returns_field_linked_errors() -> None:
    c, journey_id = await _owner()
    try:
        brief = (await c.get(f"/api/journeys/{journey_id}/brief")).json()
        row_version = brief["journey"]["row_version"]
        payload = _valid_payload()
        payload["budget"] = {
            "mode": "hard",
            "ceiling_minor": 800_000_00,
            "preferred_min_minor": 900_000_00,
            "preferred_max_minor": 950_000_00,
        }
        saved = await c.put(
            f"/api/journeys/{journey_id}/brief/draft",
            json={"payload": payload, "expected_row_version": row_version},
        )
        assert saved.status_code == 200
        assert saved.json()["validation"], "draft saves but reports blockers"
        row_version = saved.json()["journey"]["row_version"]

        blocked = await c.post(
            f"/api/journeys/{journey_id}/brief/publish",
            json={"reason": "Should not publish", "expected_row_version": row_version},
        )
        assert blocked.status_code == 422
        detail = blocked.json()["detail"]
        assert detail["code"] == "brief_invalid"
        assert any(e["field"] == "budget.preferred_max_minor" for e in detail["errors"])

        versions = (await c.get(f"/api/journeys/{journey_id}/brief/versions")).json()
        assert versions == []
    finally:
        await c.aclose()


async def test_stale_row_version_is_rejected() -> None:
    c, journey_id = await _owner()
    try:
        brief = (await c.get(f"/api/journeys/{journey_id}/brief")).json()
        stale = brief["journey"]["row_version"]
        await c.put(
            f"/api/journeys/{journey_id}/brief/draft",
            json={"payload": _valid_payload(), "expected_row_version": stale},
        )
        conflict = await c.put(
            f"/api/journeys/{journey_id}/brief/draft",
            json={"payload": _valid_payload(), "expected_row_version": stale},
        )
        assert conflict.status_code == 409
    finally:
        await c.aclose()


async def test_reset_weights_restores_the_default_split() -> None:
    c, journey_id = await _owner()
    try:
        brief = (await c.get(f"/api/journeys/{journey_id}/brief")).json()
        payload = _valid_payload()
        payload["weights"] = {
            "price": 70,
            "land": 10,
            "location": 10,
            "condition": 10,
            "price_enabled": True,
            "land_enabled": True,
            "location_enabled": True,
            "condition_enabled": False,
        }
        saved = await c.put(
            f"/api/journeys/{journey_id}/brief/draft",
            json={"payload": payload, "expected_row_version": brief["journey"]["row_version"]},
        )
        assert saved.json()["weight_total_enabled"] == 90

        reset = await c.post(f"/api/journeys/{journey_id}/brief/reset-weights")
        weights = reset.json()["draft"]["weights"]
        assert (weights["price"], weights["land"], weights["location"], weights["condition"]) == (
            30,
            30,
            20,
            20,
        )
        assert weights["condition_enabled"] is True
    finally:
        await c.aclose()


async def test_onboarding_is_resumable() -> None:
    c, journey_id = await _owner()
    try:
        journey = (await c.get(f"/api/journeys/{journey_id}")).json()
        assert journey["status"] == "onboarding"
        assert journey["onboarding_step"] == 1

        step = await c.patch(
            f"/api/journeys/{journey_id}",
            json={"onboarding_step": 3, "expected_row_version": journey["row_version"]},
        )
        assert step.json()["onboarding_step"] == 3

        resumed = (await c.get(f"/api/journeys/{journey_id}")).json()
        assert resumed["onboarding_step"] == 3
        assert resumed["onboarding_complete"] is False

        done = await c.post(f"/api/journeys/{journey_id}/complete-onboarding")
        assert done.json()["onboarding_complete"] is True
        assert done.json()["status"] == "active"
    finally:
        await c.aclose()
