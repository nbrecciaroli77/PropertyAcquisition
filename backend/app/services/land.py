"""LAND_FEASIBILITY_V1 — pure, deterministic, versioned. No I/O, no score out of 100.

Unknown evidence stays provisional. Only a supported, field-specific failure excludes. Advertised/package
price, supported land component, price kind, seller-ceiling confidence, total area, usable area and the
dwelling pathway are kept distinct. Travel is a soft preference and never excludes.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from app.schemas.brief import BriefPayload, LandFeasibilityBrief
from app.services.matching import FactValue, PriceInput, PropertyInput, _dollars

LAND_ENGINE_VERSION = "land_feasibility_v1"
PROFILE_ID = "LAND_FEASIBILITY_V1"
# Below this an advertised amount is anomalous for a land purchase: verify, never infer rent or a pass.
ANOMALOUS_BELOW_MINOR = 10_000_00
OPENING_GUIDE_KINDS = {"from", "offers_over"}

GATE_LABELS = {
    "land_price": "Land purchase price",
    "usable_area": "Usable land area",
    "availability": "Availability",
    "title_covenants": "Title and covenants",
    "legal_access": "Legal access",
    "zoning_dwelling": "Zoning / dwelling permission",
    "dwelling_pathway": "Dwelling pathway",
}
VERIFICATION_LABELS = {
    "building_envelope": "Building envelope",
    "bushfire": "Bushfire",
    "flood_wetlands": "Flood / wetlands",
    "power": "Power",
    "water": "Water",
    "wastewater": "Wastewater",
    "modular_feasibility": "Prefab / modular / habitable-shed feasibility",
}
EVIDENCE_GATES = ("title_covenants", "legal_access", "zoning_dwelling")
FAILURE_CODES = {
    "land_price": "PRICE_ABOVE_CAP",
    "usable_area": "USABLE_AREA_TOO_SMALL",
    "availability": "NOT_AVAILABLE",
    "title_covenants": "TITLE_UNSUITABLE",
    "legal_access": "ACCESS_UNSUITABLE",
    "zoning_dwelling": "ZONING_UNSUITABLE",
    "dwelling_pathway": "DWELLING_PATHWAY_UNSUITABLE",
}
UNAVAILABLE_STATES = {"sold", "withdrawn"}


@dataclass
class LandGate:
    criterion: str
    label: str
    outcome: str
    brief_value: str
    observed: str
    reason: str
    fact_key: str | None
    source_label: str
    what_would_change: str
    code: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _fact(p: PropertyInput, key: str) -> FactValue:
    return p.facts.get(key) or FactValue()


def _known(f: FactValue) -> bool:
    return f.state == "known"


def _price_gate(cfg: LandFeasibilityBrief, p: PropertyInput) -> tuple[LandGate, dict[str, Any]]:
    cap = int(cfg.land_price_cap_minor or 0)
    price: PriceInput = p.price
    subtype = _fact(p, "land_subtype")
    component = _fact(p, "land_price_minor")
    ceiling_fact = _fact(p, "seller_ceiling")
    advertised = price.lower_minor if price.kind == "exact" else None
    if price.kind in OPENING_GUIDE_KINDS:
        ceiling = "opening_guide_unverified"
    elif _known(ceiling_fact):
        ceiling = str(ceiling_fact.text_value)
    else:
        ceiling = "unverified"
    detail: dict[str, Any] = {
        "advertised_minor": price.lower_minor,
        "advertised_upper_minor": price.upper_minor,
        "advertised_raw": price.raw,
        "price_kind": price.kind,
        "subtype": subtype.text_value if _known(subtype) else None,
        "land_component_minor": component.int_value if _known(component) else None,
        "seller_ceiling": ceiling,
        "supported_land_price_minor": None,
        "basis": None,
        "verification": None,
    }
    brief_value = f"≤ {_dollars(cap)} (inclusive)"
    supported: int | None = None
    source = price.source_label
    if _known(component) and component.int_value is not None:
        supported, detail["basis"], source = component.int_value, "supported_land_component", component.source_label
    elif detail["subtype"] == "vacant_land" and advertised is not None and advertised >= ANOMALOUS_BELOW_MINOR:
        supported, detail["basis"] = advertised, "vacant_land_advertised_exact"
    detail["supported_land_price_minor"] = supported

    def gate(outcome: str, observed: str, reason: str, change: str, code: str | None = None) -> LandGate:
        return LandGate("land_price", GATE_LABELS["land_price"], outcome, brief_value, observed, reason,
                        "land_price_minor", source, change, code)

    if supported is not None:
        if supported <= cap:
            return gate("pass", _dollars(supported), "Supported land price is within the cap.", "A higher supported land price."), detail
        return gate("fail", _dollars(supported), "Supported land price is above the cap.",
                    "A supported land price at or below the cap.", FAILURE_CODES["land_price"]), detail
    amount = price.lower_minor
    if amount is not None and amount < ANOMALOUS_BELOW_MINOR:
        detail["verification"] = "PRICE_ANOMALOUS_VERIFY"
        return gate("unknown", price.raw or _dollars(amount),
                    "Anomalously low advertised amount: verify the price. It is not treated as rent or as a qualifying land price.",
                    "A verified land price."), detail
    if price.kind in OPENING_GUIDE_KINDS:
        detail["verification"] = "OPENING_GUIDE_NOT_CEILING"
        return gate("unknown", price.raw, "An opening guide is not a seller ceiling; the land price is unverified.",
                    "A supported land price or seller ceiling."), detail
    if amount is not None:
        detail["verification"] = "LAND_COMPONENT_UNKNOWN"
        return gate("unknown", price.raw or _dollars(amount),
                    "Advertised or package amount without a supported land component: neither a pass nor a failure.",
                    "A supported land component or confirmation that this is vacant land."), detail
    detail["verification"] = "UNPRICED"
    return gate("unknown", price.raw or "No price", "No supported land price yet.", "A supported land price."), detail


def _area_gate(cfg: LandFeasibilityBrief, p: PropertyInput) -> tuple[LandGate, dict[str, Any]]:
    minimum = int(cfg.min_usable_sqm or 0)
    usable, total = _fact(p, "usable_sqm"), _fact(p, "land_sqm")
    detail = {
        "usable_sqm": usable.int_value if _known(usable) else None,
        "total_sqm": total.int_value if _known(total) else None,
        "min_usable_sqm": minimum,
        "max_usable_sqm": cfg.max_usable_sqm,
    }
    brief_value = f"≥ {minimum} m² usable" + (f", ≤ {cfg.max_usable_sqm} m²" if cfg.max_usable_sqm else ", no maximum")
    if detail["usable_sqm"] is None:
        note = f" Total lot {detail['total_sqm']} m² is not usable area." if detail["total_sqm"] else ""
        return LandGate("usable_area", GATE_LABELS["usable_area"], "unknown", brief_value, "Unknown",
                        "Usable area is unknown." + note, "usable_sqm", usable.source_label,
                        "Evidence of usable area."), detail
    value = int(detail["usable_sqm"])
    too_small = value < minimum
    too_large = cfg.max_usable_sqm is not None and value > cfg.max_usable_sqm
    outcome = "fail" if too_small or too_large else "pass"
    return LandGate("usable_area", GATE_LABELS["usable_area"], outcome, brief_value, f"{value} m²",
                    "Supported usable area " + ("is below the minimum." if too_small else "is above the maximum." if too_large else "meets the requirement."),
                    "usable_sqm", usable.source_label, "Different supported usable-area evidence.",
                    FAILURE_CODES["usable_area"] if too_small else ("USABLE_AREA_TOO_LARGE" if too_large else None)), detail


def _status_gate(key: str, p: PropertyInput, ok_values: set[str], fail_values: set[str], brief_value: str) -> LandGate:
    f = _fact(p, key)
    label = GATE_LABELS.get(key) or VERIFICATION_LABELS[key]
    if not _known(f):
        return LandGate(key, label, "unknown", brief_value, "Unknown", f"{label}: not yet evidenced.", key,
                        f.source_label, f"Evidence for {label.lower()}.")
    value = str(f.text_value)
    if value in fail_values:
        return LandGate(key, label, "fail", brief_value, value, f"{label}: documented as {value}.", key,
                        f.source_label, "Different documented evidence.", FAILURE_CODES.get(key, f"{key.upper()}_UNSUITABLE"))
    if value in ok_values:
        return LandGate(key, label, "pass", brief_value, value, f"{label}: supported.", key, f.source_label,
                        "Contrary documented evidence.")
    return LandGate(key, label, "unknown", brief_value, value, f"{label}: evidence is inconclusive.", key,
                    f.source_label, f"Conclusive evidence for {label.lower()}.")


def _travel(cfg: LandFeasibilityBrief, p: PropertyInput) -> dict[str, Any]:
    f = _fact(p, "drive_minutes")
    preferred = int(cfg.preferred_drive_minutes or 0)
    exception = p.suburb.strip().lower() in {t.strip().lower() for t in cfg.long_drive_exceptions}
    minutes = f.int_value if _known(f) else None
    state = "unknown" if minutes is None else ("met" if minutes <= preferred else "missed")
    return {
        "preferred_minutes": preferred,
        "minutes": minutes,
        "state": state,
        "long_drive_exception": exception,
        "origin": cfg.drive_origin_label,
        "origin_precision": cfg.drive_origin_precision,
        "hard_exclusion": False,
        "note": (
            "Soft preference only; never an exclusion."
            + (" Explicit longer-drive option." if exception else "")
            + (" Origin is approximate (suburb level)." if cfg.drive_origin_precision == "approximate_suburb" else "")
        ),
        "source_label": f.source_label,
    }


def _location(cfg: LandFeasibilityBrief, p: PropertyInput) -> dict[str, Any]:
    towns = {(a.suburb.strip().lower(), a.state) for a in cfg.priority_towns}
    in_town = (p.suburb.strip().lower(), p.state) in towns
    return {
        "suburb": p.suburb,
        "tier": "priority_town" if in_town else ("surrounds_or_broader_region" if cfg.include_surrounds else "outside_priority_towns"),
        "broader_region": cfg.broader_region_label,
        "hard_exclusion": False,
    }


def input_hash(cfg: LandFeasibilityBrief, p: PropertyInput) -> str:
    payload = {
        "land": cfg.model_dump(),
        "property": {
            "suburb": p.suburb, "state": p.state, "price": p.price.__dict__,
            "facts": {k: v.__dict__ for k, v in sorted(p.facts.items())},
        },
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def evaluate_land(brief: BriefPayload, p: PropertyInput, brief_version_no: int) -> dict[str, Any]:
    cfg = brief.land_feasibility
    if cfg is None:
        raise ValueError("CONFIG_PROFILE_INVALID")
    price_gate, price = _price_gate(cfg, p)
    area_gate, area = _area_gate(cfg, p)
    gates = [
        price_gate,
        area_gate,
        _status_gate("availability", p, {"available"}, UNAVAILABLE_STATES, "Available for purchase"),
        *(_status_gate(k, p, {"supported"}, {"unsuitable"}, "Supported") for k in EVIDENCE_GATES),
        _status_gate("dwelling_pathway", p, {"documented"}, {"unsuitable"}, "Documented pathway to an approved dwelling"),
    ]
    checks = [_status_gate(k, p, {"supported"}, {"unsuitable"}, "Supported") for k in VERIFICATION_LABELS]
    shed = _fact(p, "shed_present")
    pathway_known = gates[-1].outcome == "pass"
    shed_note = (
        "A shed or listing claim is not permission to live there; the dwelling pathway needs its own evidence."
        if _known(shed) and shed.bool_value and not pathway_known
        else None
    )
    failures = [g for g in [*gates, *checks] if g.outcome == "fail"]
    gaps = [g for g in [*gates, *checks] if g.outcome == "unknown"]
    if failures:
        status, priority, verdict, route = "EXCLUDED", None, "fail", "excluded_known_failure"
    elif all(g.outcome == "pass" for g in gates):
        status, priority, verdict, route = "SUPPORTED", 1, "pass", "eligible"
    else:
        status, priority, verdict, route = "PROVISIONAL", 2, "unknown", "verification_required"
    travel = _travel(cfg, p)
    assessed = sum(1 for g in [*gates, *checks] if g.outcome != "unknown")
    total = len(gates) + len(checks)
    explanation = {
        "SUPPORTED": "Priority 1: hard gates, availability and dwelling pathway are supported by evidence.",
        "PROVISIONAL": "Priority 2: plausible, with named verification gaps.",
        "EXCLUDED": "Excluded: a documented, field-specific failure.",
    }[status]
    return {
        "evaluation_version": LAND_ENGINE_VERSION,
        "profile": PROFILE_ID,
        "brief_version_no": brief_version_no,
        "input_hash": input_hash(cfg, p),
        "gates": [g.as_dict() for g in gates],
        "verdict": verdict,
        "route": route,
        "fit": {"pct": None, "reason": "Land uses ordinal research priorities; there is no score out of 100."},
        "coverage": {"assessed": assessed, "total": total, "pct": None,
                     "reason": "Count of evidenced gates and checks; not a score."},
        "components": [],
        "land": {
            "status": status,
            "priority": priority,
            "explanation": explanation,
            "price": price,
            "area": area,
            "travel": travel,
            "location": _location(cfg, p),
            "checks": [c.as_dict() for c in checks],
            "failures": [{"criterion": g.criterion, "code": g.code, "reason": g.reason} for g in failures],
            "gaps": [{"criterion": g.criterion, "label": g.label, "reason": g.reason} for g in gaps],
            "shed_note": shed_note,
            "inactive": {"completed_project_budget": "inactive", "airbnb": "inactive"},
        },
    }


def rank_key(land: dict[str, Any], freshness_epoch: float, stable_id: str) -> tuple[Any, ...]:
    """Deterministic: priority, supported price, travel preference, drive minutes, freshness, stable identity."""
    priority = land.get("priority") or 9
    supported = land["price"]["supported_land_price_minor"]
    travel = land["travel"]
    minutes = travel["minutes"]
    return (
        priority,
        supported is None, supported or 0,
        {"met": 0, "missed": 1, "unknown": 2}[travel["state"]],
        minutes is None, minutes or 0,
        -freshness_epoch,
        stable_id,
    )
