from __future__ import annotations

import csv
from pathlib import Path

import yaml

from tools.make_parameter_provenance_report import build_report


ROOT = Path(__file__).resolve().parents[1]


def test_parameter_provenance_report_preserves_source_url_and_value_mapping(tmp_path: Path) -> None:
    out_dir = tmp_path / "provenance"
    manifest = build_report(ROOT, out_dir, {"apixaban"})

    assert manifest["summary"]["drug_count"] == 1
    assert (out_dir / "PARAMETER_PROVENANCE.md").exists()
    assert (out_dir / "SOURCES.csv").exists()

    with (out_dir / "PARAMETER_PROVENANCE.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    theta_cl = next(row for row in rows if row["parameter"] == "model.theta.CL")
    theta_f1 = next(row for row in rows if row["parameter"] == "model.theta.F1")
    theta_ka = next(row for row in rows if row["parameter"] == "model.theta.KA")
    assert theta_cl["reference_status"] == "mapped_to_pk_derived"
    assert theta_cl["source_mapping_status"] == "checked"
    assert theta_cl["reference_value"] == "3.3"
    assert theta_cl["source_id"] == "source_1"
    assert "Label:" in theta_cl["pk_raw_excerpt"]
    assert theta_f1["reference_status"] == "fixture_policy_systemic_parameters"
    assert theta_f1["reference_value"] == ""
    assert theta_ka["reference_status"] == "fixture_policy_no_external_source"

    sources = list(csv.DictReader((out_dir / "SOURCES.csv").open(newline="", encoding="utf-8")))
    assert sources[0]["source_url"].startswith("https://dailymed.nlm.nih.gov/")


def test_parameter_provenance_report_covers_all_drugs_and_is_yaml_readable(tmp_path: Path) -> None:
    out_dir = tmp_path / "provenance"
    manifest = build_report(ROOT, out_dir)

    assert manifest["summary"]["drug_count"] == len(list((ROOT / "drugs").glob("*/pk.yml")))
    assert manifest["summary"]["source_count"] > 0
    saved = yaml.safe_load((out_dir / "PARAMETER_PROVENANCE.yml").read_text(encoding="utf-8"))
    assert saved["report_version"] == "1.0"
    assert saved["summary"]["parameter_row_count"] == manifest["summary"]["parameter_row_count"]


def test_parameter_provenance_report_connects_value_level_source_when_pk_yml_has_it(tmp_path: Path) -> None:
    out_dir = tmp_path / "provenance"
    build_report(ROOT, out_dir, {"aciclovir"})
    with (out_dir / "PARAMETER_PROVENANCE.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    half_life = next(row for row in rows if row["parameter"] == "t_half_h" and row["record_type"] == "pk_parameter")
    clearance = next(row for row in rows if row["parameter"] == "clearance" and row["record_type"] == "pk_parameter")
    assert half_life["source_id"] == "source_1"
    assert half_life["source_review_status"] == "checked"
    assert half_life["source_mapping_status"] == "checked"
    assert half_life["source_verification_status"] == ""
    assert half_life["raw_value"] == "2.5-3.3"
    assert clearance["source_review_status"] == "checked"
    assert clearance["source_id"] == "source_4"
    assert clearance["reference_status"] == "value_level_metadata"
    assert clearance["source_mapping_status"] == "checked"
    assert clearance["normalized_value"] == "19.62"
