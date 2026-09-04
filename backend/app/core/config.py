import os
from dataclasses import dataclass, field
from enum import StrEnum


class FlagState(StrEnum):
    OFF = "off"
    ON = "on"
    LOCKED_OFF = "locked_off"


DEFAULT_FLAGS: dict[str, FlagState] = {
    "apple_sign_in": FlagState.LOCKED_OFF,
    "google_sign_in": FlagState.OFF,
    "ai_extraction": FlagState.OFF,
    "email_delivery": FlagState.OFF,
    "inbound_email": FlagState.LOCKED_OFF,
    "portal_connectors": FlagState.LOCKED_OFF,
}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Property Acquisition"
    working_name_status: str = "working concept"
    gate: str = "initial private prototype"
    milestone: int = 1
    environment: str = field(default_factory=lambda: os.environ["APP_ENV"])
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(o.strip() for o in os.environ["CORS_ORIGINS"].split(",") if o.strip())
    )
    synthetic_data_only: bool = True
    flags: dict[str, FlagState] = field(default_factory=lambda: dict(DEFAULT_FLAGS))


def get_settings() -> Settings:
    return Settings()
