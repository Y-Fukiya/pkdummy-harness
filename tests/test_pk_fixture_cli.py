from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "tools.pk_fixture_cli", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_pk_fixture_cli_help_lists_core_commands() -> None:
    completed = run_cli("--help")

    assert completed.returncode == 0, completed.stdout
    assert "pk-fixture" in completed.stdout
    assert "doctor" in completed.stdout
    assert "run" in completed.stdout
    assert "workflow" in completed.stdout
    assert "validate-simulation" in completed.stdout


def test_pk_fixture_cli_dispatches_doctor_json() -> None:
    completed = run_cli("doctor", "--json")

    assert completed.returncode in {0, 2}, completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["purpose"] == "pk_fixture_harness_preflight"
    assert payload["status"] in {"OK", "WARN", "FAILED"}


def test_pk_fixture_console_script_is_declared() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["build-system"]["build-backend"] == "setuptools.build_meta"
    assert pyproject["project"]["scripts"]["pk-fixture"] == "tools.pk_fixture_cli:main"
    assert "tools*" in pyproject["tool"]["setuptools"]["packages"]["find"]["include"]
