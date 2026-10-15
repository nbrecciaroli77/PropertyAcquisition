"""Exact AUD to integer minor-unit (cents) conversion. No binary floating point."""

from decimal import Decimal, InvalidOperation

_MULTIPLIERS = {"": Decimal(1), "k": Decimal(1_000), "m": Decimal(1_000_000)}


def aud_to_minor(value: str | int | Decimal) -> int | None:
    """'$200,000' -> 20000000; '1.15m' -> 115000000. Returns None for unparseable or sub-cent amounts."""
    if isinstance(value, int):
        return value * 100
    text = str(value).strip().lstrip("$").replace(",", "").replace(" ", "").lower()
    suffix = text[-1:] if text[-1:] in ("k", "m") else ""
    number = text[: -1] if suffix else text
    try:
        minor = Decimal(number) * _MULTIPLIERS[suffix] * 100
    except (InvalidOperation, ValueError):
        return None
    if not minor.is_finite() or minor != minor.to_integral_value():
        return None
    return int(minor)
