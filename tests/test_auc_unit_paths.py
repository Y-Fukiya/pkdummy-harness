"""Coverage for the ug/mL (biologic) AUC unit path and long terminal sampling.

Correction to an earlier review note: no committed drug spec uses ug/mL -- every
spec (including the monoclonal antibodies) templates to ng/mL with mult=1000. So
the ug/mL branch of `_auc_multiplier_from_mg_per_l` was dead/untested code. These
tests exercise it directly and end-to-end, and add a long-half-life (days) IV
fixture so the terminal-sampling path is covered beyond the hours-scale examples.
"""

from __future__ import annotations

import math
from pathlib import Path

import yaml

from tools.run_demo_set import make_demo_sim_full
from tools.validate_simulation import (
    _auc_multiplier_from_mg_per_l,
    _auc_unit,
    compute_subject_metrics,
    read_csv_rows,
    validate_simulation,
)


def test_ug_per_ml_multiplier_and_unit() -> None:
    assert _auc_multiplier_from_mg_per_l("ug/mL") == 1.0
    assert _auc_multiplier_from_mg_per_l("mcg/mL") == 1.0
    assert _auc_multiplier_from_mg_per_l("µg/mL") == 1.0  # micro sign normalised
    assert _auc_unit("ug/mL") == "ug*h/mL"


_BIOLOGIC_SPEC = {
    "version": 0.1,
    "study": {"id": "TEST_mab", "title": "long-t1/2 mAb in ug/mL"},
    "population": {"n": 5},
    "regimen": {"route": "iv", "units": {"dose": "mg"},
                "arms": {"A": {"n": 5, "dose_mg": 100.0, "infusion_h": 1.0}}},
    # long terminal: CL/V give t1/2 ~ 9.6 days, sampled out to 28 days
    "sampling": {"t_end_h": 672.0, "dt_h": 6.0, "include_t0": True},
    "model": {"template": "pk1_iv_ode", "units": {"conc": "ug/mL", "mult": 1.0},
              "theta": {"CL": 0.012, "V": 4.0}},
    "iiv": {"eta": {"CL": 0.0, "V": 0.0}, "corr": False},
    "residual": {"type": "prop+add", "prop": 0.0, "add": 0.0},
}


def _write(tmp_path: Path, name: str, obj: dict) -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return p


def test_long_terminal_biologic_recovers_half_life(tmp_path: Path) -> None:
    spec = _write(tmp_path, "spec.yml", _BIOLOGIC_SPEC)
    sim = tmp_path / "sim.csv"
    make_demo_sim_full(spec_yml=spec, out_csv=sim,
                       variability={"iiv_cv": 0.0, "residual_cv": 0.0, "seed": 1})
    m = compute_subject_metrics(read_csv_rows(sim))[sorted(compute_subject_metrics(read_csv_rows(sim)))[0]]
    ke = 0.012 / 4.0
    assert math.isclose(m.half_life_h, math.log(2.0) / ke, rel_tol=1e-3)


def test_validate_simulation_uses_ug_per_ml_path(tmp_path: Path) -> None:
    spec = _write(tmp_path, "spec.yml", _BIOLOGIC_SPEC)
    sim = tmp_path / "sim.csv"
    make_demo_sim_full(spec_yml=spec, out_csv=sim,
                       variability={"iiv_cv": 0.0, "residual_cv": 0.0, "seed": 1})
    # tag the rows with a ug/mL unit column so the validator infers the unit
    header_csv = sim.read_text(encoding="utf-8").splitlines()
    head, *body = header_csv
    sim.write_text(
        head + ",CONC_UNIT\n" + "\n".join(f"{ln},ug/mL" for ln in body) + "\n",
        encoding="utf-8",
    )
    pk = _write(tmp_path, "pk.yml", {
        "route_inferred": "iv",
        "pk_parsed": {"half_life_h": math.log(2.0) / (0.012 / 4.0), "clearance_basis": "systemic"},
        "derived": {"ke_1_per_h": 0.012 / 4.0, "CL_abs_L_per_h_at_70kg": 0.012,
                    "V_abs_L_at_70kg": 4.0, "CL_systemic_L_per_h_at_70kg": 0.012},
    })
    targets = _write(tmp_path, "targets.yml", {
        "scenario": {"dose": {"value": 100.0, "unit": "mg"}},
        "targets": {"auc": {"value": 100.0 * 1.0 / 0.012, "unit": "ug*h/mL", "summary": "geometric_mean"}},
    })
    result = validate_simulation(sim, pk, targets)
    # the ug/mL path must be used: no "unsupported concentration unit" warning
    assert not any("unsupported concentration unit" in w for w in result.warnings)
    assert result.summary["auc_unit"] == "ug*h/mL"
    assert result.summary["concentration_unit"] == "ug/mL"
