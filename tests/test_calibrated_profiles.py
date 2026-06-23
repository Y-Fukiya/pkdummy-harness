"""F-corrected oral profiles (systemic-basis drugs): drift lock + exposure check.

These profiles live under profiles/ (outside drugs/, so they never trip the
"exactly one spec_pk1_*.yml per drug" rule). The only change vs the default spec
is theta.F1 -> bioavailability, so simulated exposure becomes F*Dose/CL_systemic.
"""

from __future__ import annotations

import math
from pathlib import Path

import yaml

from tools.make_calibrated_oral_spec import _eligible, _profile_path, generate_text
from tools.run_demo_set import make_demo_sim_full
from tools.validate_simulation import compute_subject_metrics, read_csv_rows

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DRUGS = {
    "aciclovir", "alprazolam", "cimetidine", "felodipine", "itraconazole",
    "montelukast", "omeprazole", "triazolam", "verapamil",
}


def test_eligible_set_is_the_nine_systemic_basis_oral_drugs() -> None:
    assert set(_eligible(ROOT)) == EXPECTED_DRUGS


def test_committed_profiles_match_generator() -> None:
    drifted = []
    for slug in _eligible(ROOT):
        path = _profile_path(ROOT, slug)
        if not path.exists() or path.read_text(encoding="utf-8") != generate_text(ROOT, slug):
            drifted.append(slug)
    assert not drifted, f"calibrated profile drift for: {drifted}"


def test_profile_only_changes_F1() -> None:
    for slug in _eligible(ROOT):
        default = yaml.safe_load((ROOT / "drugs" / slug / "spec_pk1_oral.yml").read_text())
        profile = yaml.safe_load(_profile_path(ROOT, slug).read_text())
        f = yaml.safe_load((ROOT / "drugs" / slug / "pk.yml").read_text())["pk_parsed"]["bioavailability_frac"]
        dt, pt = default["model"]["theta"], profile["model"]["theta"]
        assert pt["F1"] == float(f) and dt["F1"] == 1.0
        for k in ("CL", "V", "KA", "ALAG1"):
            assert dt.get(k) == pt.get(k)  # nothing else moved


def test_profile_exposure_equals_F_times_systemic(tmp_path: Path) -> None:
    for slug in _eligible(ROOT):
        pk = yaml.safe_load((ROOT / "drugs" / slug / "pk.yml").read_text())
        cl_sys = pk["derived"]["CL_systemic_L_per_h_at_70kg"]
        f = float(pk["pk_parsed"]["bioavailability_frac"])
        profile_path = _profile_path(ROOT, slug)
        default_path = ROOT / "drugs" / slug / "spec_pk1_oral.yml"
        profile = yaml.safe_load(profile_path.read_text())
        dose = float(profile["regimen"]["arms"]["A"]["dose_mg"])
        mult = float(profile["model"]["units"]["mult"])

        def _auc(spec_path: Path) -> float:
            sim = tmp_path / f"{slug}_{spec_path.stem}.csv"
            make_demo_sim_full(spec_yml=spec_path, out_csv=sim,
                               variability={"iiv_cv": 0.0, "residual_cv": 0.0, "seed": 1})
            m = compute_subject_metrics(read_csv_rows(sim))
            return m[sorted(m)[0]].auc0_inf

        auc_profile, auc_default = _auc(profile_path), _auc(default_path)

        # Exact: F1 scales concentrations linearly, so the recalc AUC scales by F
        # exactly (drug-independent; trapezoid bias cancels between the two specs).
        assert math.isclose(auc_profile, f * auc_default, rel_tol=1e-9), slug

        # Loose closed-form sanity: profile exposure ~ F * Dose / CL_systemic
        # (within the per-drug trapezoid bias of the dense grid).
        expected = f * dose * mult / float(cl_sys)
        assert abs(auc_profile - expected) / expected < 0.05, (slug, auc_profile, expected)
