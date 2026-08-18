"""Schema migration integrity against the real database.

These run `alembic` as a subprocess against the same INTEGRATION_DB_URL the
rest of the suite uses, verifying the migration graph is up to date with the
models and idempotent.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def _alembic_env():
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(_REPO_ROOT))
    return {"cwd": _REPO_ROOT, "env": env}


def _run_alembic(_alembic_env, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True,
        text=True,
        cwd=_alembic_env["cwd"],
        env=_alembic_env["env"],
    )
    return result


class TestMigrationUpToDate:
    def test_upgrade_head_is_idempotent(self, _alembic_env) -> None:
        first = _run_alembic(_alembic_env, "upgrade", "head")
        assert first.returncode == 0, first.stdout + first.stderr

        second = _run_alembic(_alembic_env, "upgrade", "head")
        assert second.returncode == 0, second.stdout + second.stderr

        # A no-op upgrade runs no migrations.
        combined = second.stdout + second.stderr
        assert "Running upgrade" not in combined

    def test_models_match_migrations(self, _alembic_env) -> None:
        result = _run_alembic(_alembic_env, "check")
        assert result.returncode == 0, result.stdout + result.stderr
