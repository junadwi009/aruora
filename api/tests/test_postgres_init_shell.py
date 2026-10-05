"""Protect PostgreSQL's parent entrypoint when it sources a 0644 init script."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "ops/db/init/01-runtime-role.sh"
pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="Bash is required")


def invoke(tmp_path, overrides=None, *, sourced=True, psql_status=0):
    env = {k: v for k, v in os.environ.items() if not k.startswith("POSTGRES_")}
    env.update(POSTGRES_USER="synthetic_owner", POSTGRES_DB="synthetic_db")
    env.update(overrides or {})
    mock = tmp_path / "psql"
    mock.write_text("#!/bin/bash\ncat >/dev/null\necho PSQL_CALLED\nexit " + str(psql_status) + "\n")
    mock.chmod(0o755)
    env["PATH"] = str(tmp_path) + os.pathsep + env["PATH"]
    script = tmp_path / "01-runtime-role.sh"
    script.write_bytes(SCRIPT.read_bytes())
    script.chmod(0o644)
    code = ('. "$1"; echo PARENT_CONTINUED' if sourced else 'bash "$1"; echo PARENT_CONTINUED')
    return subprocess.run(["bash", "-e", "-c", code, "_", str(script)], env=env,
                          capture_output=True, text=True, timeout=5)


@pytest.mark.parametrize("sourced", [True, False])
def test_noop_does_not_exit_the_entrypoint(tmp_path, sourced):
    result = invoke(tmp_path, sourced=sourced)
    assert result.returncode == 0
    assert "PARENT_CONTINUED" in result.stdout
    assert "PSQL_CALLED" not in result.stdout


def test_sourcing_preserves_parent_shell_options(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("POSTGRES_")}
    env.update(POSTGRES_USER="synthetic_owner", POSTGRES_DB="synthetic_db")
    code = 'set +u; set +o pipefail; before=$(set +o); . "$1"; after=$(set +o); test "$before" = "$after"; echo OPTIONS_PRESERVED'
    result = subprocess.run(["bash", "-e", "-c", code, "_", str(SCRIPT)], env=env,
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    assert "OPTIONS_PRESERVED" in result.stdout


@pytest.mark.parametrize("values", [
    {"POSTGRES_RUNTIME_USER": "synthetic_app"},
    {"POSTGRES_RUNTIME_PASSWORD": "synthetic_secret_not_logged"},
])
def test_partial_role_configuration_fails_without_leaking_values(tmp_path, values):
    result = invoke(tmp_path, values)
    assert result.returncode != 0
    assert "PARENT_CONTINUED" not in result.stdout
    assert "PSQL_CALLED" not in result.stdout
    assert "configured together" in result.stderr
    assert "synthetic_secret_not_logged" not in result.stdout + result.stderr


@pytest.mark.parametrize("sourced", [True, False])
def test_configured_role_returns_to_parent_after_psql(tmp_path, sourced):
    result = invoke(tmp_path, {"POSTGRES_RUNTIME_USER": "synthetic_app",
                              "POSTGRES_RUNTIME_PASSWORD": "synthetic_secret_not_logged"},
                    sourced=sourced)
    assert result.returncode == 0
    assert "PSQL_CALLED" in result.stdout
    assert "PARENT_CONTINUED" in result.stdout
    assert "synthetic_secret_not_logged" not in result.stdout + result.stderr


def test_psql_failure_still_aborts_parent_initialization(tmp_path):
    result = invoke(tmp_path, {"POSTGRES_RUNTIME_USER": "synthetic_app",
                              "POSTGRES_RUNTIME_PASSWORD": "synthetic_secret_not_logged"},
                    psql_status=7)
    assert result.returncode == 7
    assert "PARENT_CONTINUED" not in result.stdout
