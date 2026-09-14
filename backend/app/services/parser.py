"""Deterministic text parser for M4.1 pasted listing intake.

Rules:
- NO AI, NO HTTP, NO external services.
- Unknown facts stay Unknown — never coerced to 0, false, or None.
- Ambiguous values (e.g. "low/mid/high $1m's") are flagged as review_reasons.
- Parser version is embedded in every result for future reproducibility.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

PARSER_VERSION = "1.0"

# Australian states / territories
_AU_STATES = {"WA", "SA", "NT", "QLD", "NSW", "ACT", "VIC", "TAS"}

# ── Compiled patterns ────────────────────────────────────────────────────────

# Beds/baths/cars  – captures the three numbers from formats like:
#   3x2x2   3 x 2 x 2   3/2/2
_BBB_COMPACT = re.compile(
    r"(?<!\d)(\d{1,2})\s*[x×/]\s*(\d{1,2})\s*[x×/]\s*(\d{1,2})(?!\d)"
)

# Individual "N bed|bedroom|br" patterns
_BED_RE = re.compile(r"(?<!\d)(\d{1,2})\s*(?:bed(?:room)?s?|br)(?!\w)", re.IGNORECASE)
_BATH_RE = re.compile(
    r"(?<!\d)(\d{1,2})\s*(?:bath(?:room)?s?|ba)(?!\w)", re.IGNORECASE
)
_CAR_RE = re.compile(
    r"(?<!\d)(\d{1,2})\s*"
    r"(?:car(?:s|port)?s?|garage(?:s)?|parking\s+space(?:s)?|lock[- ]up(?:s)?)(?!\w)",
    re.IGNORECASE,
)

# Land / floor area
_LAND_LABEL = re.compile(
    r"land(?:\s+(?:area|size|content))?[\s:]*", re.IGNORECASE
)
_FLOOR_LABEL = re.compile(
    r"(?:floor|internal|living|house)(?:\s+(?:area|size|space))?[\s:]*",
    re.IGNORECASE,
)
# Numeric area value with units (m², m2, sqm, hectares, acres)
_AREA_VAL = re.compile(
    r"(?<!\d)(\d[\d\s,]*)(?:\s*)"
    r"(m²|m2|sqm|sq\.?\s*m(?:etres?)?|ha|hectares?|acres?)(?!\w)",
    re.IGNORECASE,
)

# Property type keywords
_TYPE_MAP = [
    (re.compile(r"\btownhouse\b", re.IGNORECASE), "townhouse"),
    (re.compile(r"\bvilla\b", re.IGNORECASE), "villa"),
    (re.compile(r"\bduplex\b", re.IGNORECASE), "house"),
    (re.compile(r"\bapartment\b|\bapt\b", re.IGNORECASE), "apartment"),
    (re.compile(r"\bunit\b(?!\s+\d)", re.IGNORECASE), "unit"),  # "unit 2" is an address, not a type
    (re.compile(r"\bacreage\b|\bfarm\b|\brural\b", re.IGNORECASE), "acreage"),
    # "land" as a type only when NOT immediately followed by a measurement label
    (re.compile(r"\bland\b(?!\s*[:/]|\s+area|\s+size|\s+sqm|\s+m²|\s+\d)", re.IGNORECASE), "land"),
    (re.compile(r"\bblock\b|\bvacant\b", re.IGNORECASE), "land"),
    (re.compile(r"\bhouse\b|\bhome\b|\bdwelling\b|\bbungalow\b", re.IGNORECASE), "house"),
]

# Price patterns – ordered from most-specific to least-specific
_PRICE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Ambiguous band text – must come before other $ patterns
    (
        re.compile(
            r"(?:low|mid|mid-?high|high)\s*\$[\d,.]+[mk]?'?s?\b",
            re.IGNORECASE,
        ),
        "ambiguous",
    ),
    (
        re.compile(
            r"\$[\d,.]+[mk]?'?s\b",  # "$1m's", "$850k's"
            re.IGNORECASE,
        ),
        "ambiguous",
    ),
    # Auction — check before contact_agent so "Auction — contact agent" → auction
    (re.compile(r"\bauction\b", re.IGNORECASE), "auction"),
    # Contact agent / POA
    (
        re.compile(r"\bcontact\s+agent\b|\bprice\s+on\s+application\b|\bPOA\b", re.IGNORECASE),
        "contact_agent",
    ),    # EOI / Expressions of interest
    (
        re.compile(r"\bexpressions?\s+of\s+interest\b|\bEOI\b", re.IGNORECASE),
        "expressions_of_interest",
    ),
    # Offers over / above / from
    (
        re.compile(
            r"(?:offers?\s+(?:over|above|from)|from)\s+\$[\d,.]+[mk]?",
            re.IGNORECASE,
        ),
        "offers_over",
    ),
    # Range: $X - $Y or $X to $Y
    (
        re.compile(
            r"\$[\d,.]+[mk]?\s*(?:[-–—]|to)\s*\$[\d,.]+[mk]?",
            re.IGNORECASE,
        ),
        "range",
    ),
    # Exact: $1,250,000 or $1.25m or $850k
    (
        re.compile(r"\$[\d,.]+(?:\.\d+)?[mk]?\b", re.IGNORECASE),
        "exact",
    ),
]

_AU_STREET_TYPES = (
    r"(?:Street|St|Road|Rd|Drive|Dr|Avenue|Ave|Way|Close|Cl|Court|Ct|Place|Pl"
    r"|Boulevard|Blvd|Crescent|Cres|Grove|Gr|Lane|Ln|Circuit|Cct|Highway|Hwy"
    r"|Parade|Pde|Terrace|Tce|Loop|Mews|Rise|Ridge|Glen|Green|Outlook|Walk|Alley)"
)

# Address: try to find a canonical Australian address in the first 8 non-empty lines
# Matches "N[A] Street Type[,] Suburb STATE POSTCODE" or "N/N Street Type Suburb STATE"
_ADDR_RE = re.compile(
    r"(?P<number>\d+[A-Za-z]?(?:/\d+)?)\s+"
    r"(?P<street>[A-Za-z][A-Za-z '\-]{1,35}?\s+" + _AU_STREET_TYPES + r")[\s,]+"
    r"(?P<suburb>[A-Za-z][A-Za-z '\-]{1,40}?)\s+"
    r"(?P<state>WA|SA|NT|QLD|NSW|ACT|VIC|TAS)\s*"
    r"(?P<postcode>\d{4})?",
    re.IGNORECASE,
)

# Postcode anywhere in text
_POSTCODE_RE = re.compile(r"\b(\d{4})\b")
# State anywhere in text
_STATE_RE = re.compile(
    r"\b(WA|SA|NT|QLD|NSW|ACT|VIC|TAS)\b(?:\s+(\d{4}))?",
    re.IGNORECASE,
)


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class ParsedPrice:
    price_kind: str
    raw_price: str
    lower_minor: int | None = None
    upper_minor: int | None = None


@dataclass
class ParseResult:
    address_line: str | None = None
    suburb: str | None = None
    state: str | None = None
    postcode: str | None = None

    beds: int | None = None
    baths: int | None = None
    cars: int | None = None
    land_sqm: int | None = None
    floor_sqm: int | None = None
    property_type: str | None = None

    price: ParsedPrice | None = None

    review_reasons: list[str] = field(default_factory=list)
    parser_version: str = PARSER_VERSION


# ── Helper functions ─────────────────────────────────────────────────────────


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _parse_money_str(text: str) -> int | None:
    """Convert price string fragment to minor units (cents).  Returns None on failure."""
    t = text.strip().lstrip("$").replace(",", "").lower()
    try:
        if t.endswith("m"):
            return round(float(t[:-1]) * 1_000_000 * 100)
        if t.endswith("k"):
            return round(float(t[:-1]) * 1_000 * 100)
        return round(float(t) * 100)
    except (ValueError, OverflowError):
        return None


def _area_to_sqm(value_str: str, unit: str) -> int | None:
    """Convert an area string + unit to integer square metres.  Returns None on error."""
    try:
        val = float(value_str.replace(" ", "").replace(",", ""))
    except ValueError:
        return None
    unit_lower = unit.lower()
    if "ha" in unit_lower or "hectare" in unit_lower:
        return round(val * 10_000)
    if "acre" in unit_lower:
        return round(val * 4_046.856)
    return round(val)  # already sqm


def _parse_area_near(text: str, label_re: re.Pattern[str]) -> int | None:
    """Find a labelled area (e.g. 'Land: 450m²') and return sqm."""
    for m_label in label_re.finditer(text):
        tail = text[m_label.end() : m_label.end() + 50]
        m_val = _AREA_VAL.search(tail)
        if m_val:
            return _area_to_sqm(m_val.group(1), m_val.group(2))
    return None


def _extract_beds_baths_cars(text: str) -> tuple[int | None, int | None, int | None]:
    # Compact 3x2x2 format takes highest priority
    m = _BBB_COMPACT.search(text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))

    # Individual patterns
    m_bed = _BED_RE.search(text)
    m_bath = _BATH_RE.search(text)
    m_car = _CAR_RE.search(text)
    beds = int(m_bed.group(1)) if m_bed else None
    baths = int(m_bath.group(1)) if m_bath else None
    cars = int(m_car.group(1)) if m_car else None
    return beds, baths, cars


def _extract_areas(text: str) -> tuple[int | None, int | None]:
    """Returns (land_sqm, floor_sqm).  Both may be None."""
    land = _parse_area_near(text, _LAND_LABEL)
    floor_ = _parse_area_near(text, _FLOOR_LABEL)

    # Fallback: scan all area mentions and use position heuristics
    if land is None or floor_ is None:
        mentions: list[tuple[int, int, int | None]] = []  # (pos, sqm, sqm)
        for m in _AREA_VAL.finditer(text):
            sqm = _area_to_sqm(m.group(1), m.group(2))
            mentions.append((m.start(), sqm or 0, sqm))
        if mentions:
            # Sort by value descending — larger area is typically land
            by_val = sorted(mentions, key=lambda x: x[1], reverse=True)
            if land is None and len(by_val) >= 1 and by_val[0][2]:
                land = by_val[0][2]
            if floor_ is None and len(by_val) >= 2 and by_val[1][2]:
                floor_ = by_val[1][2]
            elif floor_ is None and len(by_val) == 1 and by_val[0][2]:
                # Only one area value — could be either; leave floor as Unknown
                pass

    return land, floor_


def _extract_price(text: str) -> tuple[ParsedPrice | None, bool]:
    """Returns (ParsedPrice | None, needs_review).  needs_review=True for ambiguous text."""
    for pattern, kind in _PRICE_PATTERNS:
        m = pattern.search(text)
        if m:
            raw = _clean(m.group(0))
            if kind == "ambiguous":
                return (
                    ParsedPrice(price_kind="contact_agent", raw_price=raw),
                    True,
                )
            if kind == "contact_agent":
                return ParsedPrice(price_kind="contact_agent", raw_price=raw), False
            if kind == "auction":
                return ParsedPrice(price_kind="auction", raw_price=raw), False
            if kind == "expressions_of_interest":
                return ParsedPrice(price_kind="expressions_of_interest", raw_price=raw), False
            if kind == "offers_over":
                # Extract the numeric value
                num_match = re.search(r"\$[\d,.]+[mk]?", raw, re.IGNORECASE)
                lower = _parse_money_str(num_match.group(0)) if num_match else None
                return (
                    ParsedPrice(price_kind="offers_over", raw_price=raw, lower_minor=lower),
                    False,
                )
            if kind == "range":
                nums = re.findall(r"\$[\d,.]+[mk]?", raw, re.IGNORECASE)
                lower = _parse_money_str(nums[0]) if nums else None
                upper = _parse_money_str(nums[1]) if len(nums) > 1 else None
                return (
                    ParsedPrice(price_kind="range", raw_price=raw, lower_minor=lower, upper_minor=upper),
                    False,
                )
            if kind == "exact":
                val = _parse_money_str(raw)
                return (
                    ParsedPrice(price_kind="exact", raw_price=raw, lower_minor=val, upper_minor=val),
                    False,
                )
    return None, False


def _extract_address(text: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Returns (address_line, suburb, state, postcode).  Any field may be None."""
    lines = [l.strip() for l in text.splitlines() if l.strip()][:8]
    for line in lines:
        m = _ADDR_RE.search(line)
        if m:
            number = m.group("number")
            street = _clean(m.group("street"))
            suburb = _clean(m.group("suburb")).title()
            state = m.group("state").upper()
            postcode = m.group("postcode")
            address_line = f"{number} {street}"
            return address_line, suburb, state, postcode

    # Partial extraction: state + postcode
    state: str | None = None
    postcode: str | None = None
    m_state = _STATE_RE.search(text)
    if m_state:
        state = m_state.group(1).upper()
        if m_state.group(2):
            postcode = m_state.group(2)
    if postcode is None:
        m_pc = _POSTCODE_RE.search(text)
        if m_pc:
            postcode = m_pc.group(1)

    return None, None, state, postcode


def _extract_property_type(text: str) -> str | None:
    for pattern, kind in _TYPE_MAP:
        if pattern.search(text):
            return kind
    return None


# ── Public API ───────────────────────────────────────────────────────────────


def parse(raw_text: str) -> ParseResult:
    """Parse a free-form listing snippet.  Returns a ParseResult; no exceptions raised."""
    result = ParseResult()
    text = raw_text

    beds, baths, cars = _extract_beds_baths_cars(text)
    result.beds = beds
    result.baths = baths
    result.cars = cars

    land, floor_ = _extract_areas(text)
    result.land_sqm = land
    result.floor_sqm = floor_

    result.property_type = _extract_property_type(text)

    price, price_ambiguous = _extract_price(text)
    result.price = price
    if price_ambiguous:
        result.review_reasons.append("price_ambiguous")

    addr_line, suburb, state, postcode = _extract_address(text)
    result.address_line = addr_line
    result.suburb = suburb
    result.state = state
    result.postcode = postcode

    if addr_line is None or suburb is None or state is None:
        result.review_reasons.append("address_incomplete")

    return result
