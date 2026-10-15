"""Fail-closed database target and schema guard. Never migrates anything."""

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
TARGETS = frozenset({"disposable", "live"})
EXEMPT_PATHS = frozenset({"/api/health", "/api/readiness"})
_OK_TTL_SECONDS = 30.0
_BLOCKED_TTL_SECONDS = 5.0
_ALEMBIC_DIR = Path(__file__).resolve().parents[2] / "alembic"


class DatabaseTargetError(RuntimeError):
    pass


def check_target(env: Mapping[str, str] = os.environ) -> str:
    """Validates DATABASE_TARGET against the DATABASE_URL host before any connection is made."""
    target = env.get("DATABASE_TARGET", "").strip()
    if target not in TARGETS:
        raise DatabaseTargetError("DATABASE_TARGET must be set to 'disposable' or 'live'; refusing to start.")
    url = env.get("DATABASE_URL", "").strip()
    if not url:
        raise DatabaseTargetError("DATABASE_URL is not set; refusing to start.")
    host = urlparse(url.replace("+asyncpg", "", 1)).hostname
    if target == "disposable" and host not in LOOPBACK_HOSTS:
        raise DatabaseTargetError(
            "DATABASE_TARGET=disposable but DATABASE_URL points at a non-loopback host; refusing to start. "
            "The disposable configuration is missing or was reset (see docs/uplift/U1-report.md §12)."
        )
    if target == "live" and host in LOOPBACK_HOSTS:
        raise DatabaseTargetError(
            "DATABASE_TARGET=live but DATABASE_URL points at a loopback host; refusing to start."
        )
    return target


@lru_cache(maxsize=1)
def expected_revision() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config()
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    head = ScriptDirectory.from_config(cfg).get_current_head()
    assert head is not None
    return head


@dataclass(frozen=True)
class SchemaState:
    ok: bool
    reason: str
    checked_at: float


def evaluate_revisions(revisions: list[str], head: str) -> SchemaState:
    if revisions == [head]:
        return SchemaState(True, "schema_compatible", time.monotonic())
    if not revisions:
        return SchemaState(False, "schema_missing", time.monotonic())
    return SchemaState(False, "schema_incompatible", time.monotonic())


async def inspect_schema(engine: AsyncEngine) -> SchemaState:
    try:
        async with engine.connect() as conn:
            revisions = list((await conn.execute(text("select version_num from alembic_version"))).scalars())
    except ProgrammingError:
        return SchemaState(False, "schema_missing", time.monotonic())
    except Exception:
        return SchemaState(False, "database_unavailable", time.monotonic())
    return evaluate_revisions(revisions, expected_revision())


_state: SchemaState | None = None


async def schema_state(force: bool = False) -> SchemaState:
    global _state
    from app.db.base import get_engine

    now = time.monotonic()
    ttl = _OK_TTL_SECONDS if _state is not None and _state.ok else _BLOCKED_TTL_SECONDS
    if force or _state is None or now - _state.checked_at > ttl:
        _state = await inspect_schema(get_engine())
    return _state
