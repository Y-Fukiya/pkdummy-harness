from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tools.build_docs_site import build_bundle
from tools.check_parameter_contract import check_contract
from tools.regen_check import build_index_text
from tools.template_gen import derive_quantities


def make_library(root: Path) -> Path:
    folder = root / "drugs" / "omeprazole"
    folder.mkdir(parents=True)
    pk = {
        "name": "Omeprazole", "route_inferred": "po",
        "sources": [{"id": "source_1", "url": "https://pubmed.ncbi.nlm.nih.gov/2315973/"}],
        "pk_parsed": {
            "clearance": {"value": 37.44, "unit": "L/h"},
            "volume": {"value": 0.23, "unit": "L/kg"},
            "half_life_h": 0.75, "bioavailability_frac": 0.35,
            "clearance_basis": "systemic", "volume_basis": "systemic",
            "weight_ref_kg_for_abs": 70.0,
        },
        "derived": {
            "CL_abs_L_per_h_at_70kg": 37.44, "V_abs_L_at_70kg": 16.1,
            "ke_1_per_h": 37.44 / 16.1,
            "CL_apparent_L_per_h_at_70kg": 37.44 / 0.35,
            "V_apparent_L_at_70kg": 16.1 / 0.35,
            "CL_systemic_L_per_h_at_70kg": 37.44,
            "V_systemic_L_at_70kg": 16.1,
        },
        "value_provenance": {
            "CL_abs_L_per_h_at_70kg": {
                "raw_value": 624, "raw_unit": "mL/min",
                "normalized_value": 37.44, "normalized_unit": "L/h",
                "conversion": {"method": "unit_conversion"},
            },
            "V_abs_L_at_70kg": {
                "raw_value": 0.23, "raw_unit": "L/kg",
                "normalized_value": 16.1, "normalized_unit": "L",
                "conversion": {"method": "body_weight_scaled", "assumptions": {"weight_ref_kg_for_abs": 70}},
            },
        },
    }
    spec = {
        "regimen": {"route": "oral", "units": {"dose": "mg"}, "arms": {"A": {"n": 1, "dose_mg": 20}}},
        "model": {"theta": {"CL": 37.44, "V": 16.1, "KA": 1.2, "F1": 0.35}},
    }
    targets = {"scenario": {"route": "po"}, "targets": {"t_half": {"value": 0.75}}}
    for name, value in (("pk.yml", pk), ("spec_pk1_oral.yml", spec), ("targets.yml", targets)):
        (folder / name).write_text(yaml.safe_dump(value), encoding="utf-8")
    (root / "INDEX.csv").write_text(build_index_text(root), encoding="utf-8")
    return folder


def change_yaml(path: Path, section: str, key: str, value: object) -> None:
    content = yaml.safe_load(path.read_text())
    content[section][key] = value
    path.write_text(yaml.safe_dump(content))


def test_builder_rejects_executable_theta_different_from_canonical(tmp_path: Path) -> None:
    folder = make_library(tmp_path)
    change_yaml(folder / "spec_pk1_oral.yml", "model", "theta", {"CL": 43.56, "V": 16.1, "KA": 1.2, "F1": 0.35})
    with pytest.raises(ValueError, match=r"omeprazole.*theta.CL"):
        build_bundle(tmp_path)


def test_builder_rejects_systemic_oral_f1_one(tmp_path: Path) -> None:
    folder = make_library(tmp_path)
    change_yaml(folder / "spec_pk1_oral.yml", "model", "theta", {"CL": 37.44, "V": 16.1, "KA": 1.2, "F1": 1})
    with pytest.raises(ValueError, match=r"omeprazole.*F1"):
        build_bundle(tmp_path)


def test_builder_checks_arithmetic_even_when_theta_matches_bad_derived_value(tmp_path: Path) -> None:
    folder = make_library(tmp_path)
    pk = yaml.safe_load((folder / "pk.yml").read_text())
    pk["pk_parsed"]["clearance"]["value"] = 43.56
    pk["derived"]["CL_abs_L_per_h_at_70kg"] = 43.56
    pk["derived"]["ke_1_per_h"] = 43.56 / 16.1
    pk["value_provenance"]["CL_abs_L_per_h_at_70kg"]["normalized_value"] = 43.56
    (folder / "pk.yml").write_text(yaml.safe_dump(pk))
    change_yaml(folder / "spec_pk1_oral.yml", "model", "theta", {"CL": 43.56, "V": 16.1, "KA": 1.2, "F1": 0.35})
    with pytest.raises(ValueError, match=r"omeprazole.*37.44"):
        build_bundle(tmp_path)


def test_builder_loads_bibliography_from_repository_root(tmp_path: Path) -> None:
    make_library(tmp_path)
    destination = tmp_path / "site" / "app"
    destination.mkdir(parents=True)
    (destination / "pubmed.json").write_text(json.dumps({"records": {"2315973": {"title": "Omeprazole study"}}}))
    sources = build_bundle(tmp_path)["drugs"][0]["sources"]
    assert sources[0].get("bibliography") == {"title": "Omeprazole study"}


def test_contract_detects_stale_atlas_without_changing_it(tmp_path: Path) -> None:
    make_library(tmp_path)
    destination = tmp_path / "site" / "app" / "drugs.json"
    destination.parent.mkdir(parents=True)
    bundle = build_bundle(tmp_path)
    bundle["drugs"][0]["spec"]["model"]["theta"]["CL"] = 43.56
    destination.write_text(json.dumps(bundle))
    before = destination.read_bytes()
    assert any("site/app/drugs.json differs" in issue for issue in check_contract(tmp_path))
    assert destination.read_bytes() == before


def test_contract_detects_stale_index(tmp_path: Path) -> None:
    make_library(tmp_path)
    destination = tmp_path / "INDEX.csv"
    destination.write_text(destination.read_text().replace("37.44", "43.56"))
    assert any("INDEX.csv differs" in issue for issue in check_contract(tmp_path, check_atlas=False))


def test_regenerated_atlas_and_index_satisfy_contract(tmp_path: Path) -> None:
    make_library(tmp_path)
    destination = tmp_path / "site" / "app" / "drugs.json"
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(build_bundle(tmp_path)))
    assert check_contract(tmp_path) == []


def test_unknown_source_conversion_is_not_invented(tmp_path: Path) -> None:
    folder = make_library(tmp_path)
    pk = yaml.safe_load((folder / "pk.yml").read_text())
    pk["value_provenance"]["CL_abs_L_per_h_at_70kg"]["raw_unit"] = "unknown source-specific unit"
    (folder / "pk.yml").write_text(yaml.safe_dump(pk))
    assert check_contract(tmp_path, check_atlas=False) == []


def test_contract_rejects_metadata_only_clearance_correction(tmp_path: Path) -> None:
    folder = make_library(tmp_path)
    pk = yaml.safe_load((folder / "pk.yml").read_text())
    pk["pk_parsed"]["clearance"]["value"] = 43.56
    pk["derived"] = derive_quantities(pk["pk_parsed"])
    (folder / "pk.yml").write_text(yaml.safe_dump(pk))
    change_yaml(folder / "spec_pk1_oral.yml", "model", "theta", {
        "CL": 43.56, "V": 16.1, "KA": 1.2, "F1": 0.35,
    })
    (tmp_path / "INDEX.csv").write_text(build_index_text(tmp_path))
    issues = check_contract(tmp_path, check_atlas=False)
    assert any("value_provenance.CL_abs_L_per_h_at_70kg" in issue
               and "37.44" in issue and "43.56" in issue for issue in issues), issues


@pytest.mark.parametrize("parameter,unit", [("clearance", "L/day"), ("volume", "mL")])
def test_generator_rejects_unknown_normalized_units(tmp_path: Path, parameter: str, unit: str) -> None:
    folder = make_library(tmp_path)
    pk = yaml.safe_load((folder / "pk.yml").read_text())
    pk["pk_parsed"][parameter]["unit"] = unit
    with pytest.raises(ValueError, match=parameter):
        derive_quantities(pk["pk_parsed"])


@pytest.mark.parametrize("parameter,unit", [("clearance", "L/day"), ("volume", "mL")])
def test_contract_rejects_unknown_normalized_units(tmp_path: Path, parameter: str, unit: str) -> None:
    folder = make_library(tmp_path)
    pk = yaml.safe_load((folder / "pk.yml").read_text())
    pk["pk_parsed"][parameter]["unit"] = unit
    (folder / "pk.yml").write_text(yaml.safe_dump(pk))
    issues = check_contract(tmp_path, check_atlas=False)
    assert any(parameter in issue and unit in issue for issue in issues), issues


@pytest.mark.parametrize("field,value,unit", [
    ("V_abs_L_at_70kg", 17.0, "L"),
    ("t_half_h", 1.0, "h"),
    ("bioavailability_frac", 0.5, "fraction"),
])
def test_provenance_core_values_match_selected_values(tmp_path: Path, field: str, value: float, unit: str) -> None:
    folder = make_library(tmp_path)
    pk = yaml.safe_load((folder / "pk.yml").read_text())
    pk["value_provenance"][field] = {
        "raw_value": value, "raw_unit": unit,
        "normalized_value": value, "normalized_unit": unit,
        "conversion": {"method": "direct"},
    }
    (folder / "pk.yml").write_text(yaml.safe_dump(pk))
    issues = check_contract(tmp_path, check_atlas=False)
    assert any(f"value_provenance.{field}" in issue and "selected canonical value" in issue
               for issue in issues), issues


def test_unrelated_provenance_is_not_bound_to_selected_clearance(tmp_path: Path) -> None:
    folder = make_library(tmp_path)
    pk = yaml.safe_load((folder / "pk.yml").read_text())
    pk["value_provenance"]["historical_study_clearance"] = {
        "raw_value": 1.0, "raw_unit": "L/h",
        "normalized_value": 1.0, "normalized_unit": "L/h",
        "role": "check_only", "conversion": {"method": "direct"},
    }
    (folder / "pk.yml").write_text(yaml.safe_dump(pk))
    assert check_contract(tmp_path, check_atlas=False) == []
