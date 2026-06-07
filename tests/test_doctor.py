from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.doctor import run_doctor


ROOT = Path(__file__).resolve().parents[1]


def test_doctor_separates_required_recommended_and_optional_checks() -> None:
    result = run_doctor(
        command_exists=lambda command: command in {"python3", "Rscript"},
        python_package_exists=lambda package: package == "yaml",
        r_package_exists=lambda package: package == "ggplot2",
    )

    assert result.status == "WARN"
    by_name = {check.name: check for check in result.checks}
    assert by_name["python3"].status == "OK"
    assert by_name["python_package:yaml"].status == "OK"
    assert by_name["Rscript"].status == "OK"
    assert by_name["R_package:ggplot2"].status == "OK"
    assert by_name["quarto"].status == "WARN"
    assert by_name["R_package:simpop"].status == "WARN"


def test_doctor_cli_json_outputs_machine_readable_status() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "tools/doctor.py",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode in {0, 2}, completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["purpose"] == "pk_fixture_harness_preflight"
    assert payload["status"] in {"OK", "WARN", "FAILED"}
    assert any(check["name"] == "python3" for check in payload["checks"])
