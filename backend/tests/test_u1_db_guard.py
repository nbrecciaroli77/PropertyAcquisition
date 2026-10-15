"""U1 closeout: the preview fails closed instead of falling back to a live database.

Isolated: fake `.invalid` hosts and a non-existent local database only. Nothing here contacts Supabase.
"""

import os
import subprocess
import sys

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.core import db_guard
from app.core.db_guard import (
    DatabaseTargetError,
    check_target,
    evaluate_revisions,
    expected_revision,
    inspect_schema,
)

FAKE_REMOTE = "postgresql://synthetic:synthetic@pooler.supabase-guard.invalid:5432/postgres"
LOCAL = "postgresql://synthetic:synthetic@127.0.0.1:5433/pa_u1_disposable"
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"DATABASE_URL": LOCAL}, "must be set"),
        ({"DATABASE_URL": LOCAL, "DATABASE_TARGET": "staging"}, "must be set"),
        ({"DATABASE_TARGET": "disposable"}, "DATABASE_URL is not set"),
        ({"DATABASE_URL": FAKE_REMOTE, "DATABASE_TARGET": "disposable"}, "non-loopback"),
        ({"DATABASE_URL": LOCAL, "DATABASE_TARGET": "live"}, "loopback host"),
    ],
)
def test_missing_or_mismatched_target_is_refused(env: dict, message: str) -> None:
    with pytest.raises(DatabaseTargetError, match=message):
        check_target(env)


def test_valid_targets_are_accepted() -> None:
    assert check_target({"DATABASE_URL": LOCAL, "DATABASE_TARGET": "disposable"}) == "disposable"
    assert check_target({"DATABASE_URL": FAKE_REMOTE, "DATABASE_TARGET": "live"}) == "live"


def _run(code: str, env_overrides: dict[str, str | None]) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in env_overrides}
    env.update({k: v for k, v in env_overrides.items() if v is not None})
    cmd = [sys.executable, "-c", code]
    return subprocess.run(cmd, cwd=BACKEND, env=env, capture_output=True, text=True, timeout=60)


def test_reset_supervisor_config_makes_backend_refuse_to_start() -> None:
    # Simulates a reset: the disposable override is gone and a remote URL is all that is left.
    result = _run("import server", {"DATABASE_URL": FAKE_REMOTE, "DATABASE_TARGET": "disposable"})
    assert result.returncode != 0
    assert "DatabaseTargetError" in result.stderr and "refusing to start" in result.stderr
    assert "synthetic:synthetic" not in result.stderr, "credentials are never echoed"


def test_alembic_refuses_remote_url_under_disposable_target() -> None:
    result = _run(
        "import sys; from alembic.config import main; main(argv=['current'])",
        {"DATABASE_URL": FAKE_REMOTE, "DATABASE_TARGET": "disposable"},
    )
    assert result.returncode != 0 and "DatabaseTargetError" in result.stderr


def test_revision_evaluation() -> None:
    head = expected_revision()
    assert head == "e7b2a9c4f1d6"
    assert evaluate_revisions([head], head).ok
    assert evaluate_revisions(["c8d5e2f9a4b1"], head).reason == "schema_incompatible"
    assert evaluate_revisions([], head).reason == "schema_missing"


async def test_missing_disposable_database_is_unavailable_not_migrated() -> None:
    url = "postgresql+asyncpg://synthetic:synthetic@127.0.0.1:5433/pa_guard_absent"
    engine = create_async_engine(url, connect_args={"ssl": "require"})
    try:
        state = await inspect_schema(engine)
    finally:
        await engine.dispose()
    assert not state.ok and state.reason == "database_unavailable"


async def test_current_disposable_schema_is_compatible() -> None:
    assert (await db_guard.schema_state(force=True)).reason == "schema_compatible"


@pytest.mark.parametrize("reason", ["schema_incompatible", "schema_missing", "database_unavailable"])
async def test_blocked_guard_returns_503_except_probes(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    blocked = db_guard.SchemaState(False, reason, 0.0)

    async def fake_inspect(_engine):  # type: ignore[no-untyped-def]
        return blocked

    monkeypatch.setattr(db_guard, "inspect_schema", fake_inspect)
    monkeypatch.setattr(db_guard, "_state", blocked)
    for path in ("/api/auth/me", "/api/journeys", "/api/meta"):
        r = await client.get(path)
        assert r.status_code == 503 and r.json()["reason"] == reason, path
    r = await client.post("/api/auth/login", json={"email": "nobody@example.invalid", "password": "x"})
    assert r.status_code == 503
    ready = await client.get("/api/readiness")
    assert ready.status_code == 503 and ready.json() == {"status": "not_ready", "reason": reason}
    assert (await client.get("/api/health")).status_code in (200, 503)
    monkeypatch.setattr(db_guard, "_state", None)
