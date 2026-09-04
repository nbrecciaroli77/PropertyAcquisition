"""Brief schema v1 and publication validation.

Every criterion is Hard rule, Preference, Disabled or Unknown. Unknown is a first-class value and is
never coerced to zero, false, pass or fail. Money is stored as integer minor units with a currency;
areas are canonical square metres.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Mode = Literal["hard", "preference", "disabled", "unknown"]
StateTerritory = Literal["WA", "SA", "NT", "QLD", "NSW", "ACT", "VIC", "TAS"]
PropertyType = Literal["house", "townhouse", "villa", "unit", "apartment", "land", "acreage"]
RenovationLevel = Literal["none", "cosmetic", "moderate", "structural"]
TimingHorizon = Literal["asap", "3_months", "6_months", "12_months", "exploring"]
Policy = Literal["include", "exclude", "flag"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NumericRule(Strict):
    mode: Mode = "preference"
    min: int | None = None
    max: int | None = None


class BudgetRule(Strict):
    mode: Mode = "hard"
    ceiling_minor: int | None = None
    preferred_min_minor: int | None = None
    preferred_max_minor: int | None = None


class PropertyProfile(Strict):
    types_mode: Mode = "preference"
    types: list[PropertyType] = Field(default_factory=list)
    detached_mode: Mode = "preference"
    detached_required: bool | None = None


class RenovationRule(Strict):
    mode: Mode = "preference"
    level: RenovationLevel | None = None


class TimingRule(Strict):
    mode: Mode = "preference"
    horizon: TimingHorizon | None = None


class Area(Strict):
    suburb: str = Field(min_length=1, max_length=80)
    state: StateTerritory
    postcode: str | None = Field(default=None, max_length=4)


class Anchor(Strict):
    label: str = Field(min_length=1, max_length=80)
    address: str = Field(min_length=1, max_length=200)
    max_minutes: int | None = None


class Locations(Strict):
    mode: Mode = "hard"
    states: list[StateTerritory] = Field(default_factory=list)
    included: list[Area] = Field(default_factory=list)
    excluded: list[Area] = Field(default_factory=list)
    radius_km: int | None = None
    anchors: list[Anchor] = Field(default_factory=list)


class Policies(Strict):
    unpriced: Policy = "flag"
    early_access: Policy = "flag"


class Weights(Strict):
    price: int = 30
    land: int = 30
    location: int = 20
    condition: int = 20
    price_enabled: bool = True
    land_enabled: bool = True
    location_enabled: bool = True
    condition_enabled: bool = True


DEFAULT_WEIGHTS = Weights()


class BriefPayload(Strict):
    schema_version: Literal[1] = 1
    currency: Literal["AUD"] = "AUD"
    budget: BudgetRule = Field(default_factory=BudgetRule)
    property_profile: PropertyProfile = Field(default_factory=PropertyProfile)
    beds: NumericRule = Field(default_factory=NumericRule)
    baths: NumericRule = Field(default_factory=NumericRule)
    parking: NumericRule = Field(default_factory=NumericRule)
    land_sqm: NumericRule = Field(default_factory=lambda: NumericRule(mode="hard"))
    floor_sqm: NumericRule = Field(default_factory=NumericRule)
    renovation: RenovationRule = Field(default_factory=RenovationRule)
    timing: TimingRule = Field(default_factory=TimingRule)
    locations: Locations = Field(default_factory=Locations)
    policies: Policies = Field(default_factory=Policies)
    weights: Weights = Field(default_factory=Weights)


class FieldError(Strict):
    field: str
    message: str


_NUMERIC_LABELS = {
    "beds": "Bedrooms",
    "baths": "Bathrooms",
    "parking": "Parking",
    "land_sqm": "Land area",
    "floor_sqm": "Floor area",
}


def default_brief() -> BriefPayload:
    return BriefPayload()


def validate_for_publish(brief: BriefPayload) -> list[FieldError]:
    """Field-linked publication blockers. Unknown and Disabled criteria never block."""
    errors: list[FieldError] = []
    b = brief.budget

    if b.mode == "hard" and b.ceiling_minor is None:
        errors.append(FieldError(field="budget.ceiling_minor", message="A hard budget rule needs a ceiling."))
    if b.preferred_min_minor is not None and b.preferred_max_minor is not None:
        if b.preferred_min_minor > b.preferred_max_minor:
            errors.append(
                FieldError(
                    field="budget.preferred_max_minor",
                    message="The preferred maximum cannot be below the preferred minimum.",
                )
            )
    if (
        b.ceiling_minor is not None
        and b.preferred_max_minor is not None
        and b.preferred_max_minor > b.ceiling_minor
    ):
        errors.append(
            FieldError(
                field="budget.preferred_max_minor",
                message="The preferred maximum cannot exceed the budget ceiling.",
            )
        )
    if b.ceiling_minor is not None and b.ceiling_minor <= 0:
        errors.append(FieldError(field="budget.ceiling_minor", message="Enter a budget ceiling above zero."))

    for name, label in _NUMERIC_LABELS.items():
        rule: NumericRule = getattr(brief, name)
        if rule.mode in ("disabled", "unknown"):
            continue
        if rule.min is not None and rule.max is not None and rule.min > rule.max:
            errors.append(
                FieldError(field=f"{name}.max", message=f"{label} maximum cannot be below the minimum.")
            )
        if rule.mode == "hard" and rule.min is None and rule.max is None:
            errors.append(
                FieldError(field=f"{name}.min", message=f"{label} is a hard rule, so it needs a value.")
            )
        for bound in ("min", "max"):
            value = getattr(rule, bound)
            if value is not None and value < 0:
                errors.append(FieldError(field=f"{name}.{bound}", message=f"{label} cannot be negative."))

    p = brief.property_profile
    if p.types_mode == "hard" and not p.types:
        errors.append(
            FieldError(
                field="property_profile.types", message="A hard property-type rule needs at least one type."
            )
        )
    if p.detached_mode == "hard" and p.detached_required is None:
        errors.append(
            FieldError(
                field="property_profile.detached_required",
                message="Choose whether detached is required, or set this criterion to Unknown.",
            )
        )

    if brief.renovation.mode == "hard" and brief.renovation.level is None:
        errors.append(
            FieldError(field="renovation.level", message="A hard renovation rule needs a tolerance level.")
        )
    if brief.timing.mode == "hard" and brief.timing.horizon is None:
        errors.append(
            FieldError(field="timing.horizon", message="A hard timing rule needs a purchase horizon.")
        )

    loc = brief.locations
    if loc.mode == "hard" and not loc.states and not loc.included:
        errors.append(
            FieldError(
                field="locations.states", message="A hard location rule needs a state or an included area."
            )
        )
    included_keys = {(a.suburb.strip().lower(), a.state) for a in loc.included}
    for area in loc.excluded:
        if (area.suburb.strip().lower(), area.state) in included_keys:
            errors.append(
                FieldError(
                    field="locations.excluded",
                    message=f"{area.suburb}, {area.state} is both included and excluded.",
                )
            )
    if loc.radius_km is not None and loc.radius_km <= 0:
        errors.append(
            FieldError(field="locations.radius_km", message="Enter a radius above zero, or leave it blank.")
        )
    for index, anchor in enumerate(loc.anchors):
        if anchor.max_minutes is not None and anchor.max_minutes <= 0:
            errors.append(
                FieldError(
                    field=f"locations.anchors.{index}.max_minutes",
                    message=(
                        "Travel minutes must be above zero. "
                        "Travel time stays Unknown until provider data exists."
                    ),
                )
            )

    w = brief.weights
    for name in ("price", "land", "location", "condition"):
        weight: int = getattr(w, name)
        if weight < 0 or weight > 100:
            errors.append(
                FieldError(field=f"weights.{name}", message="Weights are whole numbers from 0 to 100.")
            )
    if enabled_weight_total(w) == 0:
        errors.append(
            FieldError(
                field="weights",
                message="At least one preference weight must be enabled with a value above zero.",
            )
        )
    return errors


def enabled_weight_total(w: Weights) -> int:
    total = 0
    for name in ("price", "land", "location", "condition"):
        if getattr(w, f"{name}_enabled"):
            total += int(getattr(w, name))
    return total
