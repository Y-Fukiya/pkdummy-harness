from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib  # type: ignore[no-redef]


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
    assert "python -m tools.pk_fixture_cli" in completed.stdout
    assert "doctor" in completed.stdout
    assert "run" in completed.stdout
    assert "workflow" in completed.stdout
    assert "validate-simulation" in completed.stdout
    assert "audit-library" in completed.stdout


def test_pk_fixture_cli_dispatches_doctor_json() -> None:
    completed = run_cli("doctor", "--json")

    assert completed.returncode in {0, 2}, completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["purpose"] == "pk_fixture_harness_preflight"
    assert payload["status"] in {"OK", "WARN", "FAILED"}


def test_pk_fixture_has_no_console_script_checkout_based() -> None:
    # Policy B: git-checkout / Makefile tool, not pip-distributed. The console
    # script is intentionally absent (an installed pk-fixture could not find the
    # un-shipped data); the CLI is invoked as `python -m tools.pk_fixture_cli`.
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["build-system"]["build-backend"] == "setuptools.build_meta"
    assert "scripts" not in pyproject.get("project", {}), (
        "no console script expected under the checkout-based policy"
    )
    assert "tools*" in pyproject["tool"]["setuptools"]["packages"]["find"]["include"]
