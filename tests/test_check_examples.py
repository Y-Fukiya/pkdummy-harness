from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.check_examples import check_examples


ROOT = Path(__file__).resolve().parents[1]


def test_check_examples_regenerates_versioned_minimal_examples() -> None:
    result = check_examples(ROOT / "examples")

    assert result.status == "OK"
    assert result.checked_examples == ["minimal_aciclovir", "minimal_albuterol_iv"]
    assert result.warnings == []


def test_check_examples_cli() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "tools/check_examples.py",
            "examples",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Examples check: OK" in completed.stdout
    assert "minimal_aciclovir" in completed.stdout
    assert "minimal_albuterol_iv" in completed.stdout
