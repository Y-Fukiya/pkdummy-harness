"""Oral CL basis worklist: trigger logic + resolved end state.

The nine oral drugs whose source clearance used a systemic-style unit (mL/min
family) have had their basis corrected to systemic, so the worklist warning is
now cleared library-wide. These tests pin both the cleared state and the trigger
logic (so the guard still fires if an unresolved apparent/systemic-unit drug is
added later).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.validate_library import oral_basis_warning

ROOT = Path(__file__).resolve().parents[1]


def test_warning_fires_for_unresolved_apparent_on_systemic_unit() -> None:
    msg = oral_basis_warning(
        "demo", basis="apparent", basis_source="", raw_cl="327 mL/min/1.73 m2",
        CL_abs=19.62, CL_sys=1.962, F=0.1,
    )
    assert msg is not None and "systemic-style unit" in msg
    assert "CL/F = 196.2" in msg  # offers the corrected apparent value


def test_warning_silent_once_basis_corrected_to_systemic() -> None:
    assert oral_basis_warning(
        "demo", basis="systemic", basis_source="unit_inferred", raw_cl="327 mL/min",
        CL_abs=19.62, CL_sys=19.62, F=0.1,
    ) is None


def test_warning_silent_when_confirmed_apparent() -> None:
    assert oral_basis_warning(
        "demo", basis="apparent", basis_source="confirmed", raw_cl="500 mL/min",
        CL_abs=30.0, CL_sys=19.5, F=0.65,
    ) is None


def test_warning_silent_for_L_per_h_unit() -> None:
    # L/h is a defensible apparent (CL/F) reading -> not flagged.
    assert oral_basis_warning(
        "demo", basis="apparent", basis_source="", raw_cl="48 L/h",
        CL_abs=48.0, CL_sys=24.0, F=0.5,
    ) is None


def test_library_basis_worklist_is_cleared() -> None:
    proc = subprocess.run(
        [sys.executable, "tools/validate_library.py", "."],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Library validation: OK" in proc.stdout
    # all nine systemic-unit oral drugs resolved -> no basis worklist warnings remain
    assert "uses a systemic-style unit" not in proc.stdout
