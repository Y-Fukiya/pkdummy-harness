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
