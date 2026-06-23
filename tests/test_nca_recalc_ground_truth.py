"""Differential / ground-truth anchor for the simulation-validation NCA recalc.

Why this test exists
--------------------
`tools/validate_simulation.compute_subject_metrics` is the trust anchor of the
harness: the README sells "AUC/Cmax/Tmax/t1/2 recalculation". The other NCA
tests assert the recalc against its *own* prior output (regression), not against
an independent oracle. This module adds the missing piece: an independent
closed-form 1-compartment oracle, evaluated on the two committed example specs,
with documented tolerances. It needs no external tools (no PKNCA/Phoenix/R), so
it runs in CI. For a generator whose sim is itself analytic, closed form is a
stronger and exact anchor than a second numerical NCA.

Findings this test pins (measured on the dt=0.5 h example grids):

  * terminal t1/2 recalc matches the analytic ke essentially exactly -> the
    last-3-point slope is fine ON DENSE fixture data, even though it is not a
    formal best-fit lambda_z.

  * AUC0-inf recalc on the full dense profile is accurate (<~1.2%), and its bias
    is NOT a structural overestimate: the absorption/infusion rise (concave ->
    trapezoid under-estimates) offsets the decline (convex -> trapezoid
    over-estimates). For lagged oral absorption the net is slightly NEGATIVE.
    The textbook "linear trapezoid overestimates AUC" applies to the DECLINE
    phase, which `test_decline_phase_trapezoid_bias_is_material` isolates and
    shows is large (>20%) on sparse declining data -- i.e. the method choice
    (linear vs linear-up/log-down) matters for sparse AUClast, not for dense
    full-profile AUC0-inf.

  * Cmax recalc UNDER-estimates the true peak for oral drugs whose true Tmax
    falls between grid points (sampling effect), and is near-exact when Tmax
    lands on a sample (IV infusion ending on the grid).
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pytest
import yaml

from tools.run_demo_set import make_demo_sim_full
from tools.validate_simulation import compute_subject_metrics, read_csv_rows

ROOT = Path(__file__).resolve().parents[1]


# --- Independent closed-form 1-compartment oracle (no harness code reused) -----

def _analytic_iv_infusion(*, dose_mg: float, cl: float, v: float, t_inf: float, mult: float) -> dict:
    ke = cl / v
    return {
        "auc0_inf": dose_mg / cl * mult,
        "cmax": dose_mg / (cl * t_inf) * (1.0 - math.exp(-ke * t_inf)) * mult,
        "tmax_h": t_inf,
        "half_life_h": math.log(2.0) / ke,
    }


def _analytic_oral_first_order(
    *, dose_mg: float, cl: float, v: float, ka: float, f1: float, alag: float, mult: float
) -> dict:
    ke = cl / v
    tmax_rel = math.log(ka / ke) / (ka - ke)
    cmax = (
        f1 * dose_mg * ka / (v * (ka - ke))
        * (math.exp(-ke * tmax_rel) - math.exp(-ka * tmax_rel))
        * mult
    )
    return {
        "auc0_inf": f1 * dose_mg / cl * mult,
        "cmax": cmax,
        "tmax_h": alag + tmax_rel,
        "half_life_h": math.log(2.0) / ke,
    }


def _typical_subject_metrics(spec_rel: str, tmp_path: Path):
    """Deterministic, IIV-free, residual-free dense sim -> recalc for subject 1."""
    spec_path = ROOT / spec_rel
    sim_csv = tmp_path / f"{spec_path.parent.name}_sim_full.csv"
    make_demo_sim_full(
        spec_yml=spec_path,
        out_csv=sim_csv,
        variability={"iiv_cv": 0.0, "residual_cv": 0.0, "seed": 1},
    )
    metrics = compute_subject_metrics(read_csv_rows(sim_csv))
    assert metrics, "no subject metrics computed from generated sim"
    return metrics[sorted(metrics)[0]]


def _spec(spec_rel: str) -> dict:
    return yaml.safe_load((ROOT / spec_rel).read_text(encoding="utf-8"))


# --- Tests --------------------------------------------------------------------

def test_oral_aciclovir_recalc_matches_closed_form(tmp_path: Path) -> None:
    spec = _spec("drugs/aciclovir/spec_pk1_oral.yml")
    theta = spec["model"]["theta"]
    truth = _analytic_oral_first_order(
        dose_mg=float(spec["regimen"]["arms"]["A"]["dose_mg"]),
        cl=float(theta["CL"]), v=float(theta["V"]), ka=float(theta["KA"]),
        f1=float(theta.get("F1", 1.0)), alag=float(theta.get("ALAG1", 0.0)),
        mult=float(spec["model"]["units"]["mult"]),
    )
    m = _typical_subject_metrics("drugs/aciclovir/spec_pk1_oral.yml", tmp_path)

    assert math.isclose(m.half_life_h, truth["half_life_h"], rel_tol=1e-3)

    # Dense full-profile AUC0-inf is accurate; sign is profile-dependent, so we
    # bound magnitude only.
    assert abs(m.auc0_inf - truth["auc0_inf"]) / truth["auc0_inf"] < 0.02

    # True Tmax (~1.79 h) is off the 0.5 h grid -> sampled peak under-estimates.
    assert m.cmax <= truth["cmax"] * (1.0 + 1e-9)
    assert (truth["cmax"] - m.cmax) / truth["cmax"] < 0.05


def test_iv_infusion_albuterol_recalc_matches_closed_form(tmp_path: Path) -> None:
    spec = _spec("drugs/albuterol/spec_pk1_iv.yml")
    theta = spec["model"]["theta"]
    arm = spec["regimen"]["arms"]["A"]
    truth = _analytic_iv_infusion(
        dose_mg=float(arm["dose_mg"]), cl=float(theta["CL"]), v=float(theta["V"]),
        t_inf=float(arm["infusion_h"]), mult=float(spec["model"]["units"]["mult"]),
    )
    m = _typical_subject_metrics("drugs/albuterol/spec_pk1_iv.yml", tmp_path)

    assert math.isclose(m.half_life_h, truth["half_life_h"], rel_tol=1e-3)
    assert abs(m.auc0_inf - truth["auc0_inf"]) / truth["auc0_inf"] < 0.02
    # Infusion ends exactly on a sample (t_inf=1.0, dt=0.5) -> Cmax/Tmax near-exact.
    assert math.isclose(m.cmax, truth["cmax"], rel_tol=1e-6)
    assert math.isclose(m.tmax_h, truth["tmax_h"], abs_tol=1e-9)


def test_decline_phase_trapezoid_bias_is_material() -> None:
    """Isolate WHERE the linear-trapezoid method actually diverges.

    On a sparse declining-only grid (mono-exponential), the linear trapezoid
    over-estimates the area materially versus the exact (log-linear) integral.
    This is the concrete evidence for adopting linear-up/log-down (or at least
    documenting the method) when fixtures are sampled sparsely in the tail.
    """
    ke = 19.62 / 42.0  # aciclovir ke
    c0 = 1000.0
    grid = [0.0, 4.0, 8.0, 12.0, 16.0, 20.0]  # 4 h spacing, decline only
    def c(t: float) -> float:
        return c0 * math.exp(-ke * t)
    trap = sum(
        0.5 * (c(grid[i]) + c(grid[i + 1])) * (grid[i + 1] - grid[i])
        for i in range(len(grid) - 1)
    )
    exact = (c(grid[0]) - c(grid[-1])) / ke  # exact integral of mono-exp
    bias = (trap - exact) / exact
    # decline-only bias is positive (chord above curve) and large on a sparse grid
    assert bias > 0.20, f"expected material decline-phase over-estimation, got {bias:.3g}"


def test_measured_biases_are_recorded(tmp_path: Path) -> None:
    """Living documentation: surface both biases in -s output for reviewers."""
    spec = _spec("drugs/aciclovir/spec_pk1_oral.yml")
    theta = spec["model"]["theta"]
    truth = _analytic_oral_first_order(
        dose_mg=float(spec["regimen"]["arms"]["A"]["dose_mg"]),
        cl=float(theta["CL"]), v=float(theta["V"]), ka=float(theta["KA"]),
        f1=float(theta.get("F1", 1.0)), alag=float(theta.get("ALAG1", 0.0)),
        mult=float(spec["model"]["units"]["mult"]),
    )
    m = _typical_subject_metrics("drugs/aciclovir/spec_pk1_oral.yml", tmp_path)
    dense_bias = (m.auc0_inf - truth["auc0_inf"]) / truth["auc0_inf"]
    print(
        f"\n[aciclovir] dense full-profile AUC0-inf bias = {dense_bias*100:+.3f}% "
        f"(recalc {m.auc0_inf:.2f} vs closed form {truth['auc0_inf']:.2f})"
    )
    assert math.isfinite(dense_bias)


@pytest.mark.skipif(
    importlib.util.find_spec("rpy2") is None,
    reason="PKNCA differential comparison requires R + PKNCA via rpy2 (not bundled).",
)
def test_pknca_differential(tmp_path: Path) -> None:  # pragma: no cover - opt-in
    """Opt-in hook for a PKNCA cross-check when R + PKNCA are available.

    Generate a sampled fixture, run PKNCA, and assert AUClast/Cmax/Tmax agree
    with the harness recalc within a documented band. Skipped by default since
    the repo intentionally does not bundle external tools.
    """
    pytest.skip("Wire up PKNCA via rpy2 here to enable the differential comparison.")
