from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def remove_runtime_junk() -> None:
    for pattern in ("__pycache__", ".pytest_cache"):
        for path in ROOT.rglob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)


def run_command(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_checked_in_library_validates() -> None:
    result = run_command("tools/validate_library.py", ".")
    assert result.returncode == 0, result.stdout + result.stderr


def test_codex_harness_check_passes() -> None:
    remove_runtime_junk()
    result = run_command("tools/codex_harness_check.py", ".")
    assert result.returncode == 0, result.stdout + result.stderr
