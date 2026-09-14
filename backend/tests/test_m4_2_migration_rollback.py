"""Migration rollback verification for M4.2.

This test is intentionally guarded so it can only run against the disposable
database prepared by the verification command, never the configured Supabase
database.
"""
from __future__ import annotations

import os
import subprocess


def _alembic(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python", "-m", "alembic", "--config", "alembic.ini", *args],
        check=False,
        capture_output=True,
        text=True,
        cwd="/app/backend",
    )


def test_m4_2_rollback_and_reupgrade_on_disposable_database() -> None:
    assert os.environ.get("M4_2_VERIFY_ISOLATED_DB") == "1"
    before = _alembic("current")
    assert before.returncode == 0, before.stderr
    assert "a8d2e3f4b5c6" in before.stdout

    rollback = _alembic("downgrade", "f3c9b21a5d8e")
    assert rollback.returncode == 0, rollback.stderr
    at_previous = _alembic("current")
    assert at_previous.returncode == 0 and "f3c9b21a5d8e" in at_previous.stdout

    reupgrade = _alembic("upgrade", "head")
    assert reupgrade.returncode == 0, reupgrade.stderr
    final = _alembic("heads")
    assert final.returncode == 0 and final.stdout.count("a8d2e3f4b5c6") == 1