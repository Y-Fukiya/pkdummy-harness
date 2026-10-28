"""Regressions for the source-confirmed 2026-10-28 corrections."""

import math
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


def load(slug, name):
    return yaml.safe_load((ROOT / "drugs" / slug / name).read_text())


@pytest.mark.parametrize(
    "slug,cl,volume,bioavailability",
    [
        ("omeprazole", 624 * 60 / 1000, 0.23 * 70, 0.35),
        ("apixaban", 3.3, 21.0, 0.5),
        ("sildenafil", 41.0, 105.0, 0.41),
        ("montelukast", 30.8 * 60 / 1000, 9.7, 0.61),
    ],
)
def test_systemic_source_values_flow_to_spec_and_auc(slug, cl, volume, bioavailability):
    pk = load(slug, "pk.yml")
    spec = load(slug, "spec_pk1_oral.yml")
    targets = load(slug, "targets.yml")
    parsed = pk["pk_parsed"]
    derived = pk["derived"]
    theta = spec["model"]["theta"]
    assert parsed["clearance_basis"] == "systemic"
    assert parsed["volume_basis"] == "systemic"
    assert derived["CL_systemic_L_per_h_at_70kg"] == pytest.approx(cl)
    assert derived["V_systemic_L_at_70kg"] == pytest.approx(volume)
    assert theta["CL"] == pytest.approx(cl)
    assert theta["V"] == pytest.approx(volume)
    assert theta["F1"] == pytest.approx(bioavailability)
    assert derived["CL_apparent_L_per_h_at_70kg"] == pytest.approx(cl / bioavailability)
    dose = targets["scenario"]["dose"]["value"]
    auc = targets["targets"]["auc"]
    assert auc["value"] == pytest.approx(bioavailability * dose * 1000 / cl)
    assert auc["basis"] == "f_dose_over_cl"
    assert auc["independent_literature_target"] is False


def test_omeprazole_provenance_conversion_is_arithmetically_consistent():
    pk = load("omeprazole", "pk.yml")
    provenance = pk["value_provenance"]["CL_abs_L_per_h_at_70kg"]
    assert provenance["raw_value"] == 624
    assert provenance["raw_unit"] == "mL/min"
    assert provenance["normalized_value"] == pytest.approx(624 * 60 / 1000)
    assert "metabolites" in pk["pk_raw"]["elimination_route"].lower()


def test_terminal_half_life_is_not_recalibrated_to_vss():
    for slug, reported in (("apixaban", 12.0), ("sildenafil", 4.0)):
        pk = load(slug, "pk.yml")
        target = load(slug, "targets.yml")["targets"]["t_half"]
        derived = pk["derived"]
        implied = math.log(2) * derived["V_abs_L_at_70kg"] / derived["CL_abs_L_per_h_at_70kg"]
        assert pk["pk_parsed"]["half_life_h"] == reported
        assert not math.isclose(implied, reported, rel_tol=0.25)
        assert target["used_to_calibrate_cl_v"] is False
        assert target["structural_mismatch"]["acknowledged"] is True


def test_montelukast_population_and_bioavailability_match_elderly_study():
    pk = load("montelukast", "pk.yml")
    targets = load("montelukast", "targets.yml")
    source = pk["value_provenance"]["bioavailability_frac"]
    assert targets["scenario"]["population"]["group"] == "elderly_healthy"
    assert pk["pk_parsed"]["half_life_h"] == 6.7
    assert source["raw_value"] == 61
    assert source["conversion"]["assumptions"]["dose_context"] == "10 mg oral, single-dose bioavailability comparison"


def test_metabolism_and_urinary_excretion_are_not_conflated():
    pk = load("triazolam", "pk.yml")
    elimination = pk["pk_raw"]["elimination_route"]
    assert "CYP3A" in elimination
    assert "glucuronide" in elimination.lower()
    assert "unchanged" in elimination.lower()


@pytest.mark.parametrize("slug", ["omeprazole", "apixaban", "sildenafil", "montelukast", "triazolam"])
def test_source_correction_does_not_imply_clinical_acceptance(slug):
    pk = load(slug, "pk.yml")
    assert pk["simulation_validity"]["status"] == "clinical_hold"
