import os
import re
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


def _database_url() -> str:
    """Normalise the owner-supplied Supabase URL to the asyncpg driver."""
    raw = os.environ["DATABASE_URL"]
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql://", 1)
    if raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw.split("?", 1)[0]


@dataclass(frozen=True)
class Settings:
    app_name: str = "Property Acquisition"
    working_name_status: str = "working concept"
    gate: str = "initial private prototype"
    milestone: int = 2
    environment: str = field(default_factory=lambda: os.environ["APP_ENV"])
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(o.strip() for o in os.environ["CORS_ORIGINS"].split(",") if o.strip())
    )
    cors_origin_regex: str = field(default_factory=lambda: os.environ["CORS_ORIGIN_REGEX"])
    database_url: str = field(default_factory=_database_url)
    jwt_secret: str = field(default_factory=lambda: os.environ["JWT_SECRET"])
    app_base_url: str = field(default_factory=lambda: os.environ["APP_BASE_URL"].rstrip("/"))
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    verification_token_hours: int = 24
    reset_token_hours: int = 1
    login_lockout_attempts: int = 5
    login_lockout_ip_attempts: int = 20
    login_lockout_minutes: int = 15
    synthetic_data_only: bool = True
    # Explicitly opt-in to expose dev/inspection routes.  Must be set to "true" in
    # the process environment; the .env file must NOT enable this outside a local
    # developer workstation or an in-process test runner.
    dev_routes_enabled: bool = field(
        default_factory=lambda: os.environ.get("DEV_ROUTES_ENABLED", "false").strip().lower() == "true"
    )
    # Public sign-up gate: set to "false" for a private MVP with invitation-only access.
    signup_enabled: bool = field(
        default_factory=lambda: os.environ.get("SIGNUP_ENABLED", "true").strip().lower() != "false"
    )
    flags: dict[str, FlagState] = field(default_factory=lambda: dict(DEFAULT_FLAGS))

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    def allows_origin(self, origin: str) -> bool:
        if origin in self.cors_origins:
            return True
        return bool(self.cors_origin_regex) and re.match(self.cors_origin_regex, origin) is not None


def get_settings() -> Settings:
    return Settings()
