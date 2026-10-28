from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from tools.build_docs_site import build_drug
from tools.check_parameter_contract import check_source_contract
from tools.template_gen import make_pk_yml, make_targets_yml

ROOT = Path(__file__).resolve().parents[1]


def test_every_canonical_drug_declares_clinical_assessment():
    missing = []
    for path in (ROOT / "drugs").glob("*/pk.yml"):
        pk = yaml.safe_load(path.read_text(encoding="utf-8"))
        if (pk.get("simulation_validity") or {}).get("status") not in {"not_assessed", "clinical_hold"}:
            missing.append(path.parent.name)
    assert missing == []


def test_public_projection_separates_screening_from_manual_status():
    drug = build_drug(ROOT / "drugs/abciximab/pk.yml")
    assert drug["simulation_validity"]["status"] == "not_assessed"
    screening = drug["fixture_assessment"]["half_life_check"]
    assert screening["evaluated"] is True
    assert screening["hold_candidate"] is True
    assert screening["ratio"] == pytest.approx(15.271964109386333)
    assert drug["fixture_assessment"]["dose_context"]["clinical_dose_verified"] is False
    assert drug["fixture_assessment"]["dose_context"]["arms"]["A"]["dose_mg"] == 100


def test_contract_rejects_missing_or_unknown_assessment(tmp_path):
    from tests.test_parameter_contract import make_library

    folder = make_library(tmp_path)
    path = folder / "pk.yml"
    pk = yaml.safe_load(path.read_text(encoding="utf-8"))
    pk.pop("simulation_validity", None)
    path.write_text(yaml.safe_dump(pk), encoding="utf-8")
    assert any("simulation_validity.status" in issue for issue in check_source_contract(tmp_path))
    pk["simulation_validity"] = {"status": "approved", "reasons": []}
    path.write_text(yaml.safe_dump(pk), encoding="utf-8")
    assert any("simulation_validity.status" in issue for issue in check_source_contract(tmp_path))


def fixture_pk(ratio=1.0):
    return {
        "pk_parsed": {"half_life_h": math.log(2)},
        "derived": {"CL_abs_L_per_h_at_70kg": 1.0, "V_abs_L_at_70kg": ratio},
    }


@pytest.mark.parametrize("ratio, expected", [(1.0, False), (1.5, False), (1 / 1.5, False), (1.500001, True), (1 / 1.500001, True)])
def test_half_life_screen_is_symmetric_with_strict_boundary(ratio, expected):
    from tools.simulation_assessment import assess_fixture

    result = assess_fixture(fixture_pk(ratio), {}, {})["half_life_check"]
    assert result["ratio"] == pytest.approx(ratio)
    assert result["hold_candidate"] is expected


@pytest.mark.parametrize("bad_value", [None, 0, -1, float("nan"), float("inf"), True])
def test_unavailable_or_invalid_half_life_is_not_a_pass(bad_value):
    from tools.simulation_assessment import assess_fixture

    pk = fixture_pk()
    pk["pk_parsed"]["half_life_h"] = bad_value
    result = assess_fixture(pk, {}, {})["half_life_check"]
    assert result["evaluated"] is False
    assert result["hold_candidate"] is None
    assert result["ratio"] is None


def test_circular_fixture_is_not_independent_validation():
    from tools.simulation_assessment import assess_fixture

    pk = fixture_pk()
    pk["value_provenance"] = {"V_abs_L_at_70kg": {"conversion": {"method": "derived_formula"}, "selection": {"depends_on": ["CL_abs_L_per_h_at_70kg", "t_half_h"]}}}
    result = assess_fixture(pk, {}, {})["half_life_check"]
    assert result["circular"] is True
    assert result["hold_candidate"] is False
    inulin = build_drug(ROOT / "drugs/inulin/pk.yml")
    assert inulin["fixture_assessment"]["half_life_check"]["circular"] is True
    assert inulin["simulation_validity"]["status"] == "not_assessed"


def test_real_library_has_ten_symmetric_screen_candidates():
    candidates = []
    for path in sorted((ROOT / "drugs").glob("*/pk.yml")):
        drug = build_drug(path)
        if drug["fixture_assessment"]["half_life_check"]["hold_candidate"]:
            candidates.append(drug["slug"])
    assert candidates == ["abciximab", "aciclovir", "apixaban", "cimetidine", "clarithromycin", "dapagliflozin", "felodipine", "montelukast", "omeprazole", "sildenafil"]


@pytest.mark.parametrize("field, value", [("purpose", "clinical_trial"), ("clinical_dose_verified", True)])
def test_contract_rejects_clinical_regimen_claims(tmp_path, field, value):
    from tests.test_parameter_contract import make_library

    folder = make_library(tmp_path)
    path = folder / "targets.yml"
    target = yaml.safe_load(path.read_text(encoding="utf-8"))
    target["scenario"][field] = value
    path.write_text(yaml.safe_dump(target), encoding="utf-8")
    assert any(f"scenario.{field}" in issue for issue in check_source_contract(tmp_path))


def test_contract_rejects_dose_disagreement_and_empty_hold_reason(tmp_path):
    from tests.test_parameter_contract import make_library

    folder = make_library(tmp_path)
    path = folder / "targets.yml"
    target = yaml.safe_load(path.read_text(encoding="utf-8"))
    target["scenario"]["dose"]["value"] = 100
    path.write_text(yaml.safe_dump(target), encoding="utf-8")
    path = folder / "pk.yml"
    pk = yaml.safe_load(path.read_text(encoding="utf-8"))
    pk["simulation_validity"] = {"status": "clinical_hold", "reasons": []}
    path.write_text(yaml.safe_dump(pk), encoding="utf-8")
    issues = check_source_contract(tmp_path)
    assert any("dose_mg disagrees" in issue for issue in issues)
    assert any("reasons must explain clinical_hold" in issue for issue in issues)


def test_generator_defaults_are_computational_and_not_assessed():
    pk = make_pk_yml("Example", "iv", [], {}, {"clearance": {"value": 1, "unit": "L/h"}, "volume": {"value": 1, "unit": "L"}})
    assert pk["simulation_validity"] == {"status": "not_assessed", "reasons": []}
    targets = make_targets_yml("Example", "iv", 100, 1, 1)
    assert targets["scenario"]["purpose"] == "computational_stress_test"
    assert targets["scenario"]["clinical_dose_verified"] is False


def test_contract_rejects_missing_selection_and_unresolved_limitation(tmp_path):
    from tests.test_parameter_contract import make_library

    folder = make_library(tmp_path)
    path = folder / "pk.yml"
    pk = yaml.safe_load(path.read_text(encoding="utf-8"))
    pk["value_provenance"]["CL_abs_L_per_h_at_70kg"].pop("selection")
    pk["fixture_limitations"] = [{"code": "missing_source", "statement": "Unresolved", "source_id": "absent", "source_locator": "Abstract"}]
    path.write_text(yaml.safe_dump(pk), encoding="utf-8")
    issues = check_source_contract(tmp_path)
    assert any("selection requires" in issue for issue in issues)
    assert any("fixture_limitations require" in issue for issue in issues)


def test_source_constraints_are_published_without_clinical_approval():
    for slug in ("carbamazepine", "clarithromycin", "fluvoxamine", "aciclovir", "efavirenz", "verapamil", "felodipine"):
        drug = build_drug(ROOT / "drugs" / slug / "pk.yml")
        assert drug["fixture_limitations"], slug
        assert drug["simulation_validity"]["status"] in {"not_assessed", "clinical_hold"}
        assert all(item["source_locator"] and item["source_id"] for item in drug["fixture_limitations"])
        if slug == "felodipine":
            assert any("blood" in item["statement"] for item in drug["fixture_limitations"])


def test_censored_bound_is_not_circular_half_life_validation():
    drug = build_drug(ROOT / "drugs/itraconazole/pk.yml")
    assert drug["fixture_assessment"]["half_life_check"]["circular"] is False


@pytest.mark.parametrize("dependencies", [["typo"], "t_half_h", [42], None])
def test_contract_rejects_invalid_derived_input_names(tmp_path, dependencies):
    from tests.test_parameter_contract import make_library

    folder = make_library(tmp_path)
    path = folder / "pk.yml"
    pk = yaml.safe_load(path.read_text(encoding="utf-8"))
    pk["value_provenance"]["CL_abs_L_per_h_at_70kg"]["selection"].update({"rule": "derived_value", "depends_on": dependencies})
    path.write_text(yaml.safe_dump(pk), encoding="utf-8")
    assert any("depends_on must list recognized" in issue for issue in check_source_contract(tmp_path))
