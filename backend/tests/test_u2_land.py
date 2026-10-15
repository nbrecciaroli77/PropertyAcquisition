"""U2 acceptance (L01–L12) against the real LAND_FEASIBILITY_V1 engine, intake service and API. Synthetic only."""

import hashlib
import json
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.money import aud_to_minor
from app.db.base import get_sessionmaker
from app.db.models import MatchEvaluation
from app.schemas.brief import Area, BriefPayload, LandFeasibilityBrief, validate_for_publish, validate_land_config
from app.services.land import LAND_ENGINE_VERSION, evaluate_land, rank_key
from app.services.matching import EVALUATION_VERSION, FactValue, PriceInput, PropertyInput, evaluate
from app.services.parser import _parse_money_str
from tests.conftest import login, register_and_verify, unique_email

SUPPORTED = {
    "availability": "available", "title_covenants": "supported", "legal_access": "supported",
    "zoning_dwelling": "supported", "dwelling_pathway": "documented",
}


def land_brief() -> BriefPayload:
    brief = BriefPayload()
    brief.land_feasibility = LandFeasibilityBrief(
        land_price_cap_minor=200_000_00, min_usable_sqm=250, preferred_drive_minutes=240,
        drive_origin_label="Home suburb (synthetic, approximate)",
        priority_towns=[Area(suburb=t, state="WA") for t in ("Harvey", "Bunbury", "Mount Barker")],
        broader_region_label="Mandurah and south", long_drive_exceptions=["Mount Barker"],
    )
    return brief


def prop(facts: dict, *, kind: str = "exact", amount: int | None = None, raw: str = "", suburb: str = "Harvey") -> PropertyInput:
    values = {}
    for key, value in facts.items():
        if isinstance(value, bool):
            values[key] = FactValue("known", bool_value=value, source_label="Synthetic agent listing")
        elif isinstance(value, int):
            values[key] = FactValue("known", int_value=value, source_label="Synthetic agent listing")
        else:
            values[key] = FactValue("known", text_value=value, source_label="Synthetic title search")
    upper = amount if kind == "exact" else None
    return PropertyInput(suburb, "WA", PriceInput(kind, raw or (f"${amount // 100:,}" if amount else "Contact agent"), amount, upper, "Synthetic"), values)


def land(facts: dict, **kw) -> dict:
    return evaluate_land(land_brief(), prop(facts, **kw), 1)["land"]


# ── L01–L03 exact boundaries ────────────────────────────────────────────────


def test_l01_supported_price_at_cap_and_250_usable_is_priority_1() -> None:
    out = land({"land_price_minor": 200_000_00, "usable_sqm": 250, **SUPPORTED})
    assert out["status"] == "SUPPORTED" and out["priority"] == 1 and out["failures"] == []
    assert out["price"]["basis"] == "supported_land_component" and out["price"]["supported_land_price_minor"] == 20_000_000


def test_l02_supported_land_only_price_one_dollar_over_cap_excludes() -> None:
    out = land({"land_price_minor": 200_001_00, "usable_sqm": 600, **SUPPORTED})
    assert out["status"] == "EXCLUDED" and [f["code"] for f in out["failures"]] == ["PRICE_ABOVE_CAP"]
    vacant = land({"land_subtype": "vacant_land", "usable_sqm": 600, **SUPPORTED}, amount=200_001_00)
    assert vacant["status"] == "EXCLUDED" and vacant["price"]["basis"] == "vacant_land_advertised_exact"


def test_l03_usable_249_excludes_and_250_passes() -> None:
    assert [f["code"] for f in land({"land_price_minor": 150_000_00, "usable_sqm": 249, **SUPPORTED})["failures"]] == ["USABLE_AREA_TOO_SMALL"]
    assert land({"land_price_minor": 150_000_00, "usable_sqm": 250, **SUPPORTED})["status"] == "SUPPORTED"


def test_no_maximum_area_by_default() -> None:
    assert land({"land_price_minor": 150_000_00, "usable_sqm": 400_000, **SUPPORTED})["status"] == "SUPPORTED"


# ── L04–L07 provisional evidence ────────────────────────────────────────────


def test_l04_large_lot_with_unknown_usable_area_stays_provisional() -> None:
    out = land({"land_sqm": 1000, "land_price_minor": 150_000_00, **SUPPORTED})
    assert out["status"] == "PROVISIONAL" and out["priority"] == 2
    assert out["area"] == {"usable_sqm": None, "total_sqm": 1000, "min_usable_sqm": 250, "max_usable_sqm": None}
    assert any(g["criterion"] == "usable_area" and "not usable area" in g["reason"] for g in out["gaps"])


def test_l05_package_230000_with_unknown_land_component_is_retained_provisionally() -> None:
    out = land({"usable_sqm": 600, **SUPPORTED}, amount=230_000_00)
    assert out["status"] == "PROVISIONAL" and out["failures"] == []
    assert out["price"]["verification"] == "LAND_COMPONENT_UNKNOWN" and out["price"]["supported_land_price_minor"] is None
    assert out["price"]["advertised_minor"] == 23_000_000


def test_l06_anomalous_950_package_is_price_verification_not_rent_or_land() -> None:
    out = land({"usable_sqm": 600, **SUPPORTED}, amount=950_00)
    assert out["status"] == "PROVISIONAL" and out["price"]["verification"] == "PRICE_ANOMALOUS_VERIFY"
    assert out["price"]["supported_land_price_minor"] is None and "rent" not in json.dumps(out["price"]).lower().replace("not treated as rent", "")
    vacant = land({"land_subtype": "vacant_land", "usable_sqm": 600, **SUPPORTED}, amount=950_00)
    assert vacant["status"] == "PROVISIONAL", "an anomalous amount never becomes a qualifying land price"


def test_l07_opening_guide_is_not_a_seller_ceiling() -> None:
    for amount in (160_000_00, 210_000_00):
        out = land({"land_subtype": "vacant_land", "usable_sqm": 600, **SUPPORTED}, kind="from", amount=amount, raw=f"From ${amount // 100:,}")
        assert out["status"] == "PROVISIONAL" and out["price"]["seller_ceiling"] == "opening_guide_unverified"
        assert out["price"]["verification"] == "OPENING_GUIDE_NOT_CEILING" and out["failures"] == []


# ── L08–L11 travel, shed, configuration, ranking ────────────────────────────


def test_l08_241_minute_drive_is_a_soft_miss_only() -> None:
    out = land({"land_price_minor": 150_000_00, "usable_sqm": 600, "drive_minutes": 241, **SUPPORTED})
    assert out["status"] == "SUPPORTED" and out["travel"]["state"] == "missed" and out["travel"]["hard_exclusion"] is False
    mt = land({"land_price_minor": 150_000_00, "usable_sqm": 600, "drive_minutes": 320, **SUPPORTED}, suburb="Mount Barker")
    assert mt["status"] == "SUPPORTED" and mt["travel"]["long_drive_exception"] is True
    assert "approximate" in out["travel"]["note"]


def test_l09_shed_with_unknown_dwelling_approval_is_provisional() -> None:
    facts = {k: v for k, v in SUPPORTED.items() if k != "dwelling_pathway"}
    out = land({"land_price_minor": 150_000_00, "usable_sqm": 600, "shed_present": True, **facts})
    assert out["status"] == "PROVISIONAL" and "not permission to live there" in out["shed_note"]


def test_documented_unsuitable_title_or_pathway_excludes() -> None:
    for key, code in (("title_covenants", "TITLE_UNSUITABLE"), ("dwelling_pathway", "DWELLING_PATHWAY_UNSUITABLE")):
        out = land({"land_price_minor": 150_000_00, "usable_sqm": 600, **{**SUPPORTED, key: "unsuitable"}})
        assert out["status"] == "EXCLUDED" and [f["code"] for f in out["failures"]] == [code]


def test_l10_missing_configuration_is_rejected_without_archived_defaults() -> None:
    errors = {e.field for e in validate_land_config(BriefPayload())}
    assert errors == {"land_feasibility"}
    empty = BriefPayload(land_feasibility=LandFeasibilityBrief())
    fields = {e.field for e in validate_for_publish(empty, "land")}
    assert {"land_feasibility.land_price_cap_minor", "land_feasibility.min_usable_sqm", "land_feasibility.preferred_drive_minutes"} <= fields
    assert empty.land_feasibility.land_price_cap_minor is None and empty.land_feasibility.preferred_drive_minutes is None
    with pytest.raises(ValueError, match="CONFIG_PROFILE_INVALID"):
        evaluate_land(BriefPayload(), prop({}), 1)


def test_l11_known_failure_with_strong_preferences_is_not_ranked_above_candidates() -> None:
    failed = land({"land_price_minor": 100_000_00, "usable_sqm": 5000, "drive_minutes": 60, **{**SUPPORTED, "legal_access": "unsuitable"}})
    provisional = land({"land_price_minor": 199_000_00, "drive_minutes": 239})
    assert failed["status"] == "EXCLUDED" and failed["priority"] is None
    assert sorted([("f", failed), ("p", provisional)], key=lambda t: rank_key(t[1], 0, t[0]))[0][0] == "p"


def test_tie_breaks_are_deterministic() -> None:
    a = land({"land_price_minor": 150_000_00, "usable_sqm": 600, "drive_minutes": 200, **SUPPORTED})
    b = land({"land_price_minor": 180_000_00, "usable_sqm": 600, "drive_minutes": 100, **SUPPORTED})
    c = land({"land_price_minor": 150_000_00, "usable_sqm": 600, "drive_minutes": 260, **SUPPORTED})
    order = sorted([("b", b, 5.0), ("c", c, 5.0), ("a", a, 5.0), ("a2", a, 9.0)], key=lambda t: rank_key(t[1], t[2], t[0]))
    assert [o[0] for o in order] == ["a2", "a", "c", "b"], "price, then travel met, then freshness, then identity"


def test_no_score_out_of_100_and_inactive_items() -> None:
    result = evaluate_land(land_brief(), prop({"usable_sqm": 600}), 1)
    assert result["fit"]["pct"] is None and result["coverage"]["pct"] is None and result["components"] == []
    assert result["land"]["inactive"] == {"completed_project_budget": "inactive", "airbnb": "inactive"}
    assert result["evaluation_version"] == LAND_ENGINE_VERSION


# ── L12 house unchanged ─────────────────────────────────────────────────────


def _house_brief() -> BriefPayload:
    brief = BriefPayload()
    brief.budget.ceiling_minor = 1_300_000_00
    brief.land_sqm.min = 400
    brief.property_profile.types_mode = "hard"
    brief.property_profile.types = ["house"]
    return brief


def test_l12_house_rules_and_hash_are_unchanged() -> None:
    p = PropertyInput("Example Park", "WA", PriceInput("exact", "$1,300,000", 1_300_000_00, 1_300_000_00, "Synthetic"),
                      {"land_sqm": FactValue("known", int_value=400, source_label="s"), "property_type": FactValue("known", text_value="house", source_label="s")})
    result = evaluate(_house_brief(), p, 1)
    outcomes = {g["criterion"]: g["outcome"] for g in result["gates"]}
    assert result["evaluation_version"] == EVALUATION_VERSION == "gates_v1+scoring_v1"
    assert outcomes["budget"] == "pass" and outcomes["land_sqm"] == "pass" and result["verdict"] == "pass"
    assert "land" not in result and result["coverage"]["pct"] is not None, "house keeps fit and coverage separate"
    baseline_brief = _house_brief().model_dump(exclude={"land_feasibility"})
    assert "land_feasibility" not in baseline_brief
    expected = hashlib.sha256(json.dumps({"brief": baseline_brief, "property": {
        "suburb": p.suburb, "state": p.state, "price": p.price.__dict__,
        "facts": {k: v.__dict__ for k, v in sorted(p.facts.items())}}}, sort_keys=True, default=str).encode()).hexdigest()
    assert result["input_hash"] == expected, "pre-U2 hash formula: stored house evaluations are not recomputed"


# ── Money ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(("text", "minor"), [
    ("$200,000", 20_000_000), ("200000.00", 20_000_000), ("$200,001", 20_000_100), ("200k", 20_000_000),
    ("1.15m", 115_000_000), ("$950", 95_000), ("0.29", 29), ("1.005k", 100_500), ("$230,000", 23_000_000),
])
def test_money_converts_exactly_to_integer_minor_units(text: str, minor: int) -> None:
    assert aud_to_minor(text) == minor and isinstance(aud_to_minor(text), int)
    assert _parse_money_str(text) == minor


def test_money_rejects_sub_cent_and_garbage() -> None:
    assert aud_to_minor("200000.005") is None and aud_to_minor("abc") is None and aud_to_minor("nan") is None
    assert aud_to_minor(Decimal("0.1") + Decimal("0.2")) == 30 and aud_to_minor(200_000) == 20_000_000


# ── Through the real API (intake → stored evaluation → priority ordering) ───


async def _land_campaign(client: AsyncClient, prefix: str, *, configure: bool = True) -> str:
    await register_and_verify(client, email := unique_email(prefix))
    await login(client, email)
    land_id = (await client.post("/api/journeys", json={"name": "Synthetic land", "timezone": "Australia/Perth", "campaign_kind": "land"})).json()["id"]
    if configure:
        brief = (await client.get(f"/api/journeys/{land_id}/brief")).json()
        draft = brief["draft"]
        draft["land_feasibility"] = land_brief().land_feasibility.model_dump()
        saved = await client.put(f"/api/journeys/{land_id}/brief/draft", json={"payload": draft, "expected_row_version": brief["journey"]["row_version"]})
        published = await client.post(f"/api/journeys/{land_id}/brief/publish", json={"reason": "Synthetic land brief", "expected_row_version": saved.json()["journey"]["row_version"]})
        assert published.status_code == 201, published.text
        assert published.json()["current_version"]["reevaluation_state"] == "completed"
    return land_id


def _intake(address: str, facts: dict, raw: str, kind: str, amount: int | None, suburb: str = "Harvey") -> dict:
    return {"mode": "structured_form", "structured": {
        "address_line": address, "suburb": suburb, "state": "WA", "facts": {"property_type": "land", **facts},
        "price": {"price_kind": kind, "raw_price": raw, "lower_minor": amount, "upper_minor": amount if kind == "exact" else None}}}


async def test_api_land_campaign_assesses_ranks_and_isolates(client: AsyncClient) -> None:
    land_id = await _land_campaign(client, "u2-api")
    cases = {
        "Lot 1 Alpha Road": ({"land_price_minor": 200_000_00, "usable_sqm": 250, **SUPPORTED}, "$200,000", "exact", 200_000_00),
        "Lot 2 Beta Road": ({"land_price_minor": 200_001_00, "usable_sqm": 600, **SUPPORTED}, "$200,001", "exact", 200_001_00),
        "Lot 3 Gamma Road": ({"usable_sqm": 600, **SUPPORTED}, "$230,000", "exact", 230_000_00),
        "Lot 4 Delta Road": ({"usable_sqm": 600}, "$950", "exact", 950_00),
        "Lot 5 Echo Road": ({"land_price_minor": 150_000_00, "usable_sqm": 600, "drive_minutes": 241, **SUPPORTED}, "$150,000", "exact", 150_000_00),
    }
    for address, (facts, raw, kind, amount) in cases.items():
        r = await client.post(f"/api/journeys/{land_id}/intake", json=_intake(address, facts, raw, kind, amount))
        assert r.status_code == 200 and r.json()["state"] == "completed", r.text
    rows = (await client.get(f"/api/journeys/{land_id}/properties?sort=priority")).json()
    by = {r["address_line"]: r["evaluation"] for r in rows}
    assert {a: e["land"]["status"] for a, e in by.items()} == {
        "Lot 1 Alpha Road": "SUPPORTED", "Lot 2 Beta Road": "EXCLUDED", "Lot 3 Gamma Road": "PROVISIONAL",
        "Lot 4 Delta Road": "PROVISIONAL", "Lot 5 Echo Road": "SUPPORTED",
    }
    assert [r["address_line"] for r in rows][:2] == ["Lot 5 Echo Road", "Lot 1 Alpha Road"], "cheaper supported price first"
    assert rows[-1]["address_line"] == "Lot 2 Beta Road", "excluded rows never outrank candidates"
    assert all(e["evaluation_version"] == LAND_ENGINE_VERSION and e["fit"]["pct"] is None for e in by.values())
    detail = (await client.get(f"/api/journeys/{land_id}/properties/{rows[0]['id']}")).json()
    assert detail["facts"]["usable_sqm"]["source_label"] and detail["evaluation"]["land"]["travel"]["state"] == "missed"
    async with get_sessionmaker()() as db:
        evs = (await db.execute(select(MatchEvaluation).where(MatchEvaluation.journey_id == uuid.UUID(land_id)))).scalars().all()
    assert len(evs) == 5 and all(e.fit_pct is None for e in evs)


async def test_api_missing_land_configuration_fails_closed(client: AsyncClient) -> None:
    land_id = await _land_campaign(client, "u2-noconfig", configure=False)
    setting = (await client.get(f"/api/journeys/{land_id}/campaign")).json()["settings"]["assessment_profile"]
    assert setting["state"] == "unavailable" and setting["config_state"] == "CONFIG_PROFILE_INVALID"
    assert "land_feasibility" in setting["config_errors"][0]
    r = await client.post(f"/api/journeys/{land_id}/intake", json=_intake("Lot 8 Zeta Road", {"usable_sqm": 600}, "$150,000", "exact", 150_000_00))
    assert r.status_code == 200
    async with get_sessionmaker()() as db:
        count = len((await db.execute(select(MatchEvaluation).where(MatchEvaluation.journey_id == uuid.UUID(land_id)))).scalars().all())
    assert count == 0, "no assessment and no borrowed defaults while configuration is missing"


async def test_api_land_evidence_is_tenant_isolated(client: AsyncClient) -> None:
    land_id = await _land_campaign(client, "u2-tenant-a")
    prop_id = (await client.post(f"/api/journeys/{land_id}/intake", json=_intake("Lot 6 Kappa Road", {"usable_sqm": 600}, "$150,000", "exact", 150_000_00))).json()["property_id"]
    await _land_campaign(client, "u2-tenant-b")
    assert (await client.get(f"/api/journeys/{land_id}/properties/{prop_id}")).status_code == 404
    assert (await client.get(f"/api/journeys/{land_id}/properties?sort=priority")).status_code == 404
