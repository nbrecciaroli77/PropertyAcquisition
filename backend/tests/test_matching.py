"""Pure engine tests for gates_v1 + scoring_v1. Cases required by Prompt 03."""

from typing import Any

from app.schemas.brief import Area, BriefPayload, default_brief
from app.services.matching import (
    EVALUATION_VERSION,
    FactValue,
    PriceInput,
    PropertyInput,
    evaluate,
    input_hash,
)


def fixture_brief() -> BriefPayload:
    b = default_brief()
    b.budget.ceiling_minor = 1_300_000_00
    b.budget.preferred_max_minor = 1_200_000_00
    b.property_profile.types_mode = "hard"
    b.property_profile.types = ["house"]
    b.property_profile.detached_mode = "hard"
    b.property_profile.detached_required = True
    b.beds.mode = "hard"
    b.beds.min = 3
    b.baths.mode = "hard"
    b.baths.min = 1
    b.land_sqm.min = 400
    b.renovation.level = "moderate"
    b.locations.states = ["WA"]
    b.locations.included = [Area(suburb="Example Park", state="WA", postcode=None)]
    return b


def known_int(v: int, src: str = "Original listing") -> FactValue:
    return FactValue("known", v, None, None, src)


def known_text(v: str) -> FactValue:
    return FactValue("known", None, v, None, "Original listing")


def base_facts() -> dict[str, FactValue]:
    return {
        "beds": known_int(4),
        "baths": known_int(2),
        "cars": known_int(2),
        "land_sqm": known_int(690),
        "property_type": known_text("house"),
        "detached": FactValue("known", None, None, True, "Original listing"),
        "condition": known_text("usable_home"),
        "location_tier": known_text("strong_alternative"),
    }


def prop(price: PriceInput, **overrides: FactValue) -> PropertyInput:
    facts = base_facts()
    facts.update(overrides)
    return PropertyInput("Example Park", "WA", price, facts)


FROM_1_1M = PriceInput("from", "From $1,100,000", 1_100_000_00, None, "Original listing")


def gate(result: dict[str, Any], criterion: str) -> dict[str, Any]:
    return next(g for g in result["gates"] if g["criterion"] == criterion)


def test_eligible_high_fit_with_all_gates_passing() -> None:
    r = evaluate(fixture_brief(), prop(FROM_1_1M), 1)
    assert r["verdict"] == "pass"
    assert r["route"] == "eligible"
    assert all(g["outcome"] == "pass" for g in r["gates"])
    assert r["fit"]["state"] == "known" and r["fit"]["pct"] == 94
    assert r["coverage"]["pct"] == 100
    assert "opening guide" in gate(r, "budget")["reason"]


def test_hard_failure_plus_high_fit_is_still_excluded() -> None:
    exact = PriceInput("exact", "$1,050,000", 1_050_000_00, 1_050_000_00, "Original listing")
    r = evaluate(
        fixture_brief(),
        prop(
            exact,
            land_sqm=known_int(318),
            location_tier=known_text("primary"),
            condition=known_text("renovation"),
        ),
        1,
    )
    assert r["verdict"] == "fail"
    assert r["route"] == "excluded_known_failure"
    assert gate(r, "land_sqm")["outcome"] == "fail"
    assert "318 m² is below" in gate(r, "land_sqm")["reason"]
    assert r["fit"]["pct"] == 87  # high fit reported separately, never promotes


def test_unknown_values_are_never_pass_fail_or_zero() -> None:
    r = evaluate(fixture_brief(), prop(FROM_1_1M, land_sqm=FactValue(), condition=FactValue()), 1)
    land = gate(r, "land_sqm")
    assert land["outcome"] == "unknown"
    assert land["observed"] == "Unknown"
    assert r["verdict"] == "unknown"
    assert r["route"] == "verification_required"
    land_component = next(c for c in r["components"] if c["name"] == "land")
    assert land_component["assessed"] is False and land_component["score"] is None
    assert r["coverage"]["pct"] == 50  # price 30 + location 20 assessed of 100
    assert r["fit"]["pct"] == 88  # (30 + 14) / 50 over assessed components only, not dragged to zero


def test_unpriced_contact_agent_never_becomes_a_number() -> None:
    unpriced = PriceInput("contact_agent", "Contact agent", None, None, "Partial listing")
    r = evaluate(fixture_brief(), prop(unpriced), 1)
    b = gate(r, "budget")
    assert b["outcome"] == "unknown"
    assert "unpriced" in b["reason"].lower()
    price = next(c for c in r["components"] if c["name"] == "price")
    assert price["assessed"] is False
    assert r["coverage"]["pct"] == 70


def test_conflicting_guide_routes_to_verification() -> None:
    conflict = PriceInput("conflicting", "$1.20m index / From $1.35m detail", None, None, "Two sources")
    r = evaluate(fixture_brief(), prop(conflict), 1)
    assert gate(r, "budget")["outcome"] == "unknown"
    assert "different guides" in gate(r, "budget")["reason"]
    assert r["verdict"] == "unknown"


def test_range_straddling_ceiling_is_unknown_not_pass() -> None:
    rng = PriceInput("range", "$1,250,000-$1,400,000", 1_250_000_00, 1_400_000_00, "Original listing")
    assert gate(evaluate(fixture_brief(), prop(rng), 1), "budget")["outcome"] == "unknown"


def test_from_price_above_ceiling_is_a_known_fail() -> None:
    high = PriceInput("from", "From $1,350,000", 1_350_000_00, None, "Original listing")
    assert gate(evaluate(fixture_brief(), prop(high), 1), "budget")["outcome"] == "fail"


def test_fit_unavailable_when_nothing_assessable_is_not_zero() -> None:
    unpriced = PriceInput("expressions_of_interest", "EOI", None, None, "Manual entry")
    r = evaluate(fixture_brief(), PropertyInput("Nowhere", "NSW", unpriced, {}), 1)
    assert r["fit"]["state"] == "unavailable"
    assert r["fit"]["pct"] is None
    assert r["coverage"]["pct"] == 0
    assert "not zero" in r["fit"]["reason"]


def test_excluded_area_fails_location_gate() -> None:
    b = fixture_brief()
    b.locations.excluded = [Area(suburb="Example Park", state="WA", postcode=None)]
    b.locations.included = []
    assert gate(evaluate(b, prop(FROM_1_1M), 1), "locations")["outcome"] == "fail"


def test_score_is_reproducible_for_same_inputs() -> None:
    a = evaluate(fixture_brief(), prop(FROM_1_1M), 3)
    b = evaluate(fixture_brief(), prop(FROM_1_1M), 3)
    assert a == b
    assert a["input_hash"] == input_hash(fixture_brief(), prop(FROM_1_1M))
    assert a["evaluation_version"] == EVALUATION_VERSION
    changed = evaluate(fixture_brief(), prop(FROM_1_1M, beds=known_int(3)), 3)
    assert changed["input_hash"] != a["input_hash"]


def test_disabled_weight_is_excluded_from_coverage_and_fit() -> None:
    b = fixture_brief()
    b.weights.condition_enabled = False
    r = evaluate(b, prop(FROM_1_1M), 1)
    assert r["coverage"]["total_enabled_weight"] == 80
    cond = next(c for c in r["components"] if c["name"] == "condition")
    assert cond["enabled"] is False
    assert r["fit"]["pct"] == round(100 * (30 + 30 + 14) / 80)


def test_no_value_score_anywhere_in_result() -> None:
    r = evaluate(fixture_brief(), prop(FROM_1_1M), 1)
    assert "value_score" not in r and "valuation" not in r
    assert {c["name"] for c in r["components"]} == {"price", "land", "location", "condition"}
    text = " ".join(str(v) for k, v in r.items() if k != "evaluation_version").lower()
    assert "value score" not in text and "valuation" not in text
