"""Drift lock for the derived block.

After the Decision 1 (ke = CL/V) + Decision 2 (persist basis) regeneration, the
committed `derived` blocks must round-trip through the current generator. This
test is the regression lock: it fails if any pk.yml drifts from
derive_quantities(pk_parsed) again, and pairs with
`python tools/check_derived_drift.py . --strict` in CI.
"""

from __future__ import annotations

from pathlib import Path

from tools.check_derived_drift import analyze_library, render_report

ROOT = Path(__file__).resolve().parents[1]


def test_library_has_no_derived_drift() -> None:
    drifted = [r["slug"] for r in analyze_library(ROOT) if r["has_drift"]]
    assert not drifted, f"derived drift reintroduced for: {drifted}"


def test_ke_convention_is_cl_over_v_not_ln2_thalf() -> None:
    results = {r["slug"]: r for r in analyze_library(ROOT)}
    # aciclovir's t_half is not attainable from CL/V, so the canonical ke must now
    # read as CL/V (or coincide), never ln2/t_half alone.
    assert results["aciclovir"]["ke_convention_committed"] in {"CL/V", "both_coincide"}


def test_basis_is_persisted_for_all_drugs() -> None:
    # Decision 2: every pk.yml carries an explicit basis after regeneration.
    assert all(r["basis_persisted"] for r in analyze_library(ROOT))


def test_report_renders_convention_summary() -> None:
    report = render_report(analyze_library(ROOT))
    assert "ke convention used by committed pk.yml" in report
    assert "Per-drug drift" in report
