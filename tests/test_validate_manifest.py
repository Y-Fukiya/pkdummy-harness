from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from tools.validate_manifest import validate_manifest_file


ROOT = Path(__file__).resolve().parents[1]


def write_yaml(path: Path, obj: dict) -> None:
    path.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")


def test_validate_manifest_accepts_workflow_manifest_shape(tmp_path: Path) -> None:
    manifest = tmp_path / "MANIFEST.yml"
    write_yaml(
        manifest,
        {
            "purpose": "pk_fixture_post_simulation_workflow",
            "status": "OK",
            "inputs": {"sim_full_csv": "raw/sim_full.csv"},
            "target_metadata": {
                "auc": {"basis": "dose_over_cl", "independent_literature_target": False},
                "t_half": {
                    "attainability_status": "OK",
                    "detected_structural_mismatch": False,
                    "acknowledged_structural_mismatch": False,
                    "relative_error": 0.0,
                },
            },
            "value_provenance_summary": {
                "required_fields": ["CL_abs_L_per_h_at_70kg", "V_abs_L_at_70kg", "t_half_h"],
                "checked_fields": ["CL_abs_L_per_h_at_70kg", "V_abs_L_at_70kg", "t_half_h"],
                "fields_needing_review": [],
                "source_ids": [],
                "mismatch_acknowledged_fields": [],
            },
            "outputs": {"adpc_csv": "analysis_inputs/ADPC.csv"},
            "counts": {"analysis_adpc_rows": 2},
            "warnings": [],
            "safeguards": ["does not modify pk.yml"],
        },
    )

    assert validate_manifest_file(manifest) == []


def test_validate_manifest_reports_missing_required_fields(tmp_path: Path) -> None:
    manifest = tmp_path / "MANIFEST.yml"
    write_yaml(manifest, {"purpose": "pk_fixture_post_simulation_workflow", "outputs": []})

    issues = validate_manifest_file(manifest)

    assert "MANIFEST.yml: missing required field: status" in issues
    assert "MANIFEST.yml: missing required field: target_metadata" in issues
    assert "MANIFEST.yml: missing required field: value_provenance_summary" in issues
    assert "MANIFEST.yml: outputs must be a mapping" in issues


def test_validate_manifest_accepts_sdtm_like_manifest_shape(tmp_path: Path) -> None:
    manifest = tmp_path / "MANIFEST.yml"
    write_yaml(
        manifest,
        {
            "purpose": "workflow_fixture_not_submission_ready_sdtm",
            "domains": ["DM", "PC"],
            "inputs": {"adpc_csv": "analysis_inputs/ADPC.csv"},
        },
    )

    assert validate_manifest_file(manifest) == []


def test_validate_manifest_reports_invalid_target_metadata(tmp_path: Path) -> None:
    manifest = tmp_path / "MANIFEST.yml"
    write_yaml(
        manifest,
        {
            "purpose": "pk_fixture_post_simulation_workflow",
            "status": "WARN",
            "outputs": {},
            "target_metadata": {
                "auc": {
                    "basis": "dose_over_cl",
                    "independent_literature_target": True,
                },
                "t_half": {
                    "attainability_status": "WARN",
                    "detected_structural_mismatch": True,
                    "acknowledged_structural_mismatch": True,
                    "relative_error": 0.4,
                },
            },
        },
    )

    issues = validate_manifest_file(manifest)

    assert "MANIFEST.yml: target_metadata.auc dose_over_cl cannot be an independent literature target" in issues


def test_validate_manifest_requires_target_metadata_shape_when_present(tmp_path: Path) -> None:
    manifest = tmp_path / "MANIFEST.yml"
    write_yaml(
        manifest,
        {
            "purpose": "pk_fixture_post_simulation_workflow",
            "status": "WARN",
            "outputs": {},
            "target_metadata": {
                "auc": {"basis": "dose_over_cl", "independent_literature_target": False},
                "t_half": {"attainability_status": "MAYBE"},
            },
        },
    )

    issues = validate_manifest_file(manifest)

    assert "MANIFEST.yml: target_metadata.t_half.detected_structural_mismatch must be boolean" in issues
    assert "MANIFEST.yml: target_metadata.t_half.acknowledged_structural_mismatch must be boolean" in issues
    assert "MANIFEST.yml: target_metadata.t_half.relative_error must be numeric or null" in issues
    assert "MANIFEST.yml: target_metadata.t_half.attainability_status must be one of ['NA', 'OK', 'WARN']" in issues


def test_validate_manifest_rejects_bad_value_provenance_summary(tmp_path: Path) -> None:
    manifest = tmp_path / "MANIFEST.yml"
    write_yaml(
        manifest,
        {
            "purpose": "pk_fixture_post_simulation_workflow",
            "status": "OK",
            "outputs": {},
            "target_metadata": {
                "auc": {"basis": "dose_over_cl", "independent_literature_target": False},
                "t_half": {
                    "attainability_status": "WARN",
                    "detected_structural_mismatch": True,
                    "acknowledged_structural_mismatch": True,
                    "relative_error": 0.4,
                },
            },
            "value_provenance_summary": {
                "required_fields": ["CL_abs_L_per_h_at_70kg", "V_abs_L_at_70kg", "t_half_h"],
                "checked_fields": ["CL_abs_L_per_h_at_70kg"],
                "fields_needing_review": ["t_half_h"],
                "source_ids": "label_1",
                "mismatch_acknowledged_fields": [],
            },
        },
    )

    issues = validate_manifest_file(manifest)

    assert "MANIFEST.yml: value_provenance_summary.checked_fields must include required_fields" in issues
    assert "MANIFEST.yml: value_provenance_summary.source_ids must be a list" in issues
    assert "MANIFEST.yml: status must be WARN when value_provenance_summary.fields_needing_review is non-empty" in issues


def test_validate_manifest_cli(tmp_path: Path) -> None:
    manifest = tmp_path / "MANIFEST.yml"
    write_yaml(
        manifest,
        {
            "purpose": "analysis_input_smoke_test_fixture",
            "status": "OK",
            "inputs": {},
            "outputs": {},
            "counts": {},
            "warnings": [],
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            "tools/validate_manifest.py",
            str(manifest),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Manifest validation: OK" in completed.stdout
