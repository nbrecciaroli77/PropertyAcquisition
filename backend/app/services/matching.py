"""gates_v1 and scoring_v1 — pure, deterministic, versioned. No I/O.

Unknown is a first-class value: it is never coerced to zero, false, Pass or Fail. Hard gates and the
preference fit are computed and reported separately, and evidence coverage is reported beside fit.
There is no Value Score and no valuation anywhere in this module.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from app.schemas.brief import BriefPayload, NumericRule

EVALUATION_VERSION = "gates_v1+scoring_v1"

Outcome = Literal["pass", "fail", "unknown"]
ValueState = Literal["known", "unknown", "not_applicable", "conflict"]

# Unpriced and aggregator kinds are never converted into numbers.
NUMERIC_PRICE_KINDS = {"exact", "range", "from", "offers_over", "auction"}
OPENING_GUIDE_KINDS = {"from", "offers_over"}

CONDITION_ORDER = {"move_in_ready": 0, "usable_home": 1, "renovation": 2, "structural": 3}
TOLERANCE_ORDER = {"none": 0, "cosmetic": 1, "moderate": 2, "structural": 3}
LOCATION_TIER_SCORE = {"primary": 100, "strong_alternative": 70, "conditional": 40}

GATE_LABELS = {
    "budget": "Budget ceiling",
    "property_type": "Property type",
    "detached": "Detached",
    "beds": "Bedrooms",
    "baths": "Bathrooms",
    "parking": "Parking",
    "land_sqm": "Land area",
    "floor_sqm": "Floor area",
    "renovation": "Renovation tolerance",
    "locations": "Location",
}


@dataclass(frozen=True)
class FactValue:
    state: ValueState = "unknown"
    int_value: int | None = None
    text_value: str | None = None
    bool_value: bool | None = None
    source_label: str = ""
    conflict_note: str | None = None


@dataclass(frozen=True)
class PriceInput:
    kind: str
    raw: str
    lower_minor: int | None
    upper_minor: int | None
    source_label: str


@dataclass(frozen=True)
class PropertyInput:
    suburb: str
    state: str
    price: PriceInput
    facts: dict[str, FactValue] = field(default_factory=dict)


@dataclass
class GateResult:
    criterion: str
    label: str
    outcome: Outcome
    brief_value: str
    observed: str
    reason: str
    fact_key: str | None
    source_label: str
    what_would_change: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class Component:
    name: str
    weight: int
    enabled: bool
    assessed: bool
    score: int | None
    points: float
    max_points: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _fact(p: PropertyInput, key: str) -> FactValue:
    return p.facts.get(key, FactValue())


def _observed_text(f: FactValue, suffix: str = "") -> str:
    if f.state == "conflict":
        return "Conflicting"
    if f.state == "not_applicable":
        return "Not applicable"
    if f.state != "known":
        return "Unknown"
    if f.int_value is not None:
        return f"{f.int_value}{suffix}"
    if f.bool_value is not None:
        return "Yes" if f.bool_value else "No"
    return (f.text_value or "").replace("_", " ").capitalize()


def _dollars(minor: int) -> str:
    return f"${minor // 100:,.0f}"


def _numeric_gate(name: str, rule: NumericRule, p: PropertyInput, fact_key: str, suffix: str) -> GateResult:
    f = _fact(p, fact_key)
    label = GATE_LABELS[name]
    parts = []
    if rule.min is not None:
        parts.append(f"≥ {rule.min}{suffix}")
    if rule.max is not None:
        parts.append(f"≤ {rule.max}{suffix}")
    brief_value = " and ".join(parts)
    observed = _observed_text(f, suffix)
    if f.state != "known" or f.int_value is None:
        return GateResult(
            name,
            label,
            "unknown",
            brief_value,
            observed,
            f"{label} is {observed.lower()} for this property, so the rule cannot be assessed.",
            fact_key,
            f.source_label,
            f"A verified {label.lower()} would decide this rule.",
        )
    v = f.int_value
    if rule.min is not None and v < rule.min:
        return GateResult(
            name,
            label,
            "fail",
            brief_value,
            observed,
            f"{observed} is below the {label.lower()} rule of {rule.min}{suffix}.",
            fact_key,
            f.source_label,
            "Only a corrected source fact could change a known failure.",
        )
    if rule.max is not None and v > rule.max:
        return GateResult(
            name,
            label,
            "fail",
            brief_value,
            observed,
            f"{observed} is above the {label.lower()} rule of {rule.max}{suffix}.",
            fact_key,
            f.source_label,
            "Only a corrected source fact could change a known failure.",
        )
    return GateResult(
        name,
        label,
        "pass",
        brief_value,
        observed,
        f"{observed} meets the {label.lower()} rule.",
        fact_key,
        f.source_label,
        "—",
    )


def _budget_gate(brief: BriefPayload, p: PropertyInput) -> GateResult:
    ceiling = brief.budget.ceiling_minor or 0
    brief_value = f"≤ {_dollars(ceiling)}"
    price = p.price
    observed = f"{price.raw} ({price.kind.replace('_', ' ')})"
    if price.kind not in NUMERIC_PRICE_KINDS or price.lower_minor is None:
        why = {
            "contact_agent": "The listing is unpriced (Contact agent).",
            "expressions_of_interest": "Expressions of interest carry no stated guide.",
            "conflicting": "Two sources state different guides; neither is trusted until verified.",
            "auction": "Auction with no stated guide.",
        }.get(price.kind, "No numeric guide is stated.")
        return GateResult(
            "budget",
            GATE_LABELS["budget"],
            "unknown",
            brief_value,
            observed,
            f"{why} No bound is inferred, so the budget rule cannot be assessed.",
            None,
            price.source_label,
            "A stated guide from the agent or a verified source would decide this rule.",
        )
    lower = price.lower_minor
    if lower > ceiling:
        return GateResult(
            "budget",
            GATE_LABELS["budget"],
            "fail",
            brief_value,
            observed,
            f"The stated guide starts at {_dollars(lower)}, above the ceiling of {_dollars(ceiling)}.",
            None,
            price.source_label,
            "Only a revised advertised guide could change a known failure.",
        )
    if price.kind == "range" and price.upper_minor is not None and price.upper_minor > ceiling:
        return GateResult(
            "budget",
            GATE_LABELS["budget"],
            "unknown",
            brief_value,
            observed,
            f"The range straddles the ceiling: {_dollars(lower)} to {_dollars(price.upper_minor)}.",
            None,
            price.source_label,
            "A narrower guide or agent confirmation would decide this rule.",
        )
    caveat = (
        " A From price is an opening guide, not a seller ceiling."
        if price.kind in OPENING_GUIDE_KINDS
        else ""
    )
    return GateResult(
        "budget",
        GATE_LABELS["budget"],
        "pass",
        brief_value,
        observed,
        f"The stated guide of {_dollars(lower)} is within the ceiling of {_dollars(ceiling)}.{caveat}",
        None,
        price.source_label,
        "—",
    )


def _location_gate(brief: BriefPayload, p: PropertyInput) -> GateResult:
    loc = brief.locations
    key = (p.suburb.strip().lower(), p.state)
    observed = f"{p.suburb} {p.state}"
    included = {(a.suburb.strip().lower(), a.state) for a in loc.included}
    excluded = {(a.suburb.strip().lower(), a.state) for a in loc.excluded}
    parts = []
    if loc.states:
        parts.append(", ".join(loc.states))
    if loc.included:
        parts.append(f"{len(loc.included)} included area(s)")
    if loc.excluded:
        parts.append(f"{len(loc.excluded)} excluded")
    brief_value = " · ".join(parts)
    label = GATE_LABELS["locations"]
    if key in excluded:
        return GateResult(
            "locations",
            label,
            "fail",
            brief_value,
            observed,
            f"{observed} is an excluded area.",
            "address",
            "Address",
            "Only a corrected address could change a known failure.",
        )
    if loc.states and p.state not in loc.states:
        return GateResult(
            "locations",
            label,
            "fail",
            brief_value,
            observed,
            f"{p.state} is outside the states in the brief.",
            "address",
            "Address",
            "Only a corrected address could change a known failure.",
        )
    if included and key not in included:
        return GateResult(
            "locations",
            label,
            "fail",
            brief_value,
            observed,
            f"{observed} is not one of the included areas.",
            "address",
            "Address",
            "Adding this area to the brief would change the result for every property.",
        )
    return GateResult(
        "locations",
        label,
        "pass",
        brief_value,
        observed,
        f"{observed} is inside the brief's areas.",
        "address",
        "Address",
        "—",
    )


def _text_gate(
    name: str, brief_value: str, p: PropertyInput, fact_key: str, ok: bool | None, f: FactValue
) -> GateResult:
    label = GATE_LABELS[name]
    observed = _observed_text(f)
    if ok is None:
        return GateResult(
            name,
            label,
            "unknown",
            brief_value,
            observed,
            f"{label} is {observed.lower()} for this property.",
            fact_key,
            f.source_label,
            f"A verified {label.lower()} would decide this rule.",
        )
    if ok:
        return GateResult(
            name,
            label,
            "pass",
            brief_value,
            observed,
            f"{observed} meets the rule.",
            fact_key,
            f.source_label,
            "—",
        )
    return GateResult(
        name,
        label,
        "fail",
        brief_value,
        observed,
        f"{observed} does not meet the rule.",
        fact_key,
        f.source_label,
        "Only a corrected source fact could change a known failure.",
    )


def evaluate_gates(brief: BriefPayload, p: PropertyInput) -> list[GateResult]:
    """Every enabled hard rule returns Pass, Fail or Unknown with a fact reference and reason."""
    gates: list[GateResult] = []
    if brief.budget.mode == "hard" and brief.budget.ceiling_minor is not None:
        gates.append(_budget_gate(brief, p))
    pp = brief.property_profile
    if pp.types_mode == "hard" and pp.types:
        f = _fact(p, "property_type")
        ok = None if f.state != "known" else (f.text_value in pp.types)
        gates.append(_text_gate("property_type", ", ".join(pp.types), p, "property_type", ok, f))
    if pp.detached_mode == "hard" and pp.detached_required is not None:
        f = _fact(p, "detached")
        ok = None if f.state != "known" or f.bool_value is None else (f.bool_value == pp.detached_required)
        gates.append(
            _text_gate(
                "detached", "Required" if pp.detached_required else "Not required", p, "detached", ok, f
            )
        )
    for name, key, suffix in (
        ("beds", "beds", ""),
        ("baths", "baths", ""),
        ("parking", "cars", ""),
        ("land_sqm", "land_sqm", " m²"),
        ("floor_sqm", "floor_sqm", " m²"),
    ):
        rule: NumericRule = getattr(brief, name)
        if rule.mode == "hard" and (rule.min is not None or rule.max is not None):
            gates.append(_numeric_gate(name, rule, p, key, suffix))
    if brief.renovation.mode == "hard" and brief.renovation.level is not None:
        f = _fact(p, "condition")
        tol = TOLERANCE_ORDER[brief.renovation.level]
        cond = CONDITION_ORDER.get(f.text_value or "") if f.state == "known" else None
        ok = None if cond is None else cond <= tol
        gates.append(_text_gate("renovation", f"Up to {brief.renovation.level}", p, "condition", ok, f))
    if brief.locations.mode == "hard" and (brief.locations.states or brief.locations.included):
        gates.append(_location_gate(brief, p))
    return gates


def verdict_from_gates(gates: list[GateResult]) -> Outcome:
    if any(g.outcome == "fail" for g in gates):
        return "fail"
    if any(g.outcome == "unknown" for g in gates):
        return "unknown"
    return "pass"


def _price_score(brief: BriefPayload, p: PropertyInput) -> tuple[int | None, str]:
    price = p.price
    if price.kind not in NUMERIC_PRICE_KINDS or price.lower_minor is None:
        return None, f"No numeric guide ({price.kind.replace('_', ' ')}); nothing is inferred."
    b = brief.budget
    lower = price.lower_minor
    pref_max = b.preferred_max_minor
    ceiling = b.ceiling_minor
    if pref_max is None and ceiling is None:
        return None, "The brief has no preferred maximum or ceiling to score against."
    if pref_max is not None and lower <= pref_max:
        if b.preferred_min_minor is not None and lower < b.preferred_min_minor:
            return 85, f"{_dollars(lower)} is below the preferred range; scored 85."
        return 100, f"{_dollars(lower)} is within the preferred range."
    top = ceiling if ceiling is not None else pref_max
    assert top is not None
    if lower > top:
        return 0, f"{_dollars(lower)} is above the ceiling."
    if pref_max is None:
        return 100, f"{_dollars(lower)} is within the ceiling."
    span = max(top - pref_max, 1)
    score = round(100 * (top - lower) / span)
    return score, f"{_dollars(lower)} sits between the preferred maximum and the ceiling; scored {score}."


def _land_score(brief: BriefPayload, p: PropertyInput) -> tuple[int | None, str]:
    rule = brief.land_sqm
    f = _fact(p, "land_sqm")
    if rule.mode in ("disabled", "unknown") or rule.min is None:
        return None, "The brief has no land target."
    if f.state != "known" or f.int_value is None:
        return None, f"Land area is {_observed_text(f).lower()}."
    target = rule.min
    if f.int_value < target:
        score = round(70 * f.int_value / target)
        return score, f"{f.int_value} m² is below the {target} m² target; 70 points at the target."
    score = min(100, round(70 + 30 * (f.int_value - target) / (target / 2)))
    return score, f"{f.int_value} m² against a {target} m² target; 100 points at {round(target * 1.5)} m²."


def _location_score(brief: BriefPayload, p: PropertyInput) -> tuple[int | None, str]:
    f = _fact(p, "location_tier")
    if f.state == "known" and f.text_value in LOCATION_TIER_SCORE:
        return LOCATION_TIER_SCORE[
            f.text_value
        ], f"Location tier '{f.text_value.replace('_', ' ')}' from {f.source_label}."
    loc = brief.locations
    key = (p.suburb.strip().lower(), p.state)
    if any((a.suburb.strip().lower(), a.state) == key for a in loc.included):
        return 100, f"{p.suburb} is an included area."
    if loc.states and p.state in loc.states:
        return 50, f"{p.state} is in the brief but {p.suburb} is not an included area."
    return None, "No location tier is recorded and the brief has no areas to compare."


def _condition_score(brief: BriefPayload, p: PropertyInput) -> tuple[int | None, str]:
    f = _fact(p, "condition")
    if brief.renovation.mode in ("disabled", "unknown") or brief.renovation.level is None:
        return None, "The brief has no renovation tolerance."
    if f.state != "known" or f.text_value not in CONDITION_ORDER:
        return None, f"Condition is {_observed_text(f).lower()}."
    gap = CONDITION_ORDER[f.text_value] - TOLERANCE_ORDER[brief.renovation.level]
    if gap <= 0:
        return 100, f"'{f.text_value.replace('_', ' ')}' is within your '{brief.renovation.level}' tolerance."
    return max(
        0, 100 - 50 * gap
    ), f"'{f.text_value.replace('_', ' ')}' exceeds your tolerance by {gap} level(s)."


def score_preferences(
    brief: BriefPayload, p: PropertyInput
) -> tuple[list[Component], dict[str, Any], dict[str, Any]]:
    """fit = achieved / max achievable assessed; coverage = assessed enabled weight / total enabled weight."""
    w = brief.weights
    scorers = {
        "price": _price_score,
        "land": _land_score,
        "location": _location_score,
        "condition": _condition_score,
    }
    components: list[Component] = []
    total_enabled = 0
    assessed_weight = 0
    achieved = 0.0
    max_achievable = 0.0
    for name, fn in scorers.items():
        weight = int(getattr(w, name))
        enabled = bool(getattr(w, f"{name}_enabled")) and weight > 0
        if not enabled:
            components.append(Component(name, weight, False, False, None, 0, 0, "Disabled in the brief."))
            continue
        total_enabled += weight
        score, reason = fn(brief, p)
        if score is None:
            components.append(Component(name, weight, True, False, None, 0, 0, reason))
            continue
        assessed_weight += weight
        points = weight * score / 100
        achieved += points
        max_achievable += weight
        components.append(Component(name, weight, True, True, score, round(points, 2), weight, reason))
    coverage = {
        "state": "known" if total_enabled else "unknown",
        "pct": round(100 * assessed_weight / total_enabled) if total_enabled else None,
        "assessed_weight": assessed_weight,
        "total_enabled_weight": total_enabled,
    }
    if max_achievable == 0:
        fit: dict[str, Any] = {
            "state": "unavailable",
            "pct": None,
            "achieved": 0,
            "max_achievable": 0,
            "reason": "No enabled preference could be assessed. Fit is unavailable, not zero.",
        }
    else:
        fit = {
            "state": "known",
            "pct": round(100 * achieved / max_achievable),
            "achieved": round(achieved, 2),
            "max_achievable": max_achievable,
            "reason": "Achieved points over the maximum achievable for assessed components.",
        }
    return components, fit, coverage


def input_hash(brief: BriefPayload, p: PropertyInput) -> str:
    payload = {
        "brief": brief.model_dump(),
        "property": {
            "suburb": p.suburb,
            "state": p.state,
            "price": p.price.__dict__,
            "facts": {k: v.__dict__ for k, v in sorted(p.facts.items())},
        },
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def evaluate(brief: BriefPayload, p: PropertyInput, brief_version_no: int) -> dict[str, Any]:
    gates = evaluate_gates(brief, p)
    verdict = verdict_from_gates(gates)
    components, fit, coverage = score_preferences(brief, p)
    route = {"pass": "eligible", "fail": "excluded_known_failure", "unknown": "verification_required"}[
        verdict
    ]
    return {
        "evaluation_version": EVALUATION_VERSION,
        "brief_version_no": brief_version_no,
        "input_hash": input_hash(brief, p),
        "gates": [g.as_dict() for g in gates],
        "verdict": verdict,
        "route": route,
        "fit": fit,
        "coverage": coverage,
        "components": [c.as_dict() for c in components],
    }
