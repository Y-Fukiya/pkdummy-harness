from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import yaml

from tools.run_harness import run_harness


ROOT = Path(__file__).resolve().parents[1]


def write_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_demo_drug(drugs_dir: Path, slug: str) -> None:
    drug_dir = drugs_dir / slug
    dose_mg = 100.0
    cl = 10.0
    v = 20.0
    half_life_h = math.log(2.0) / (cl / v)
    write_yaml(
        drug_dir / "pk.yml",
        {
            "id": slug,
            "name": slug,
            "route_inferred": "iv",
            "sources": ["fixture"],
            "pk_parsed": {"half_life_h": half_life_h},
            "derived": {
                "CL_abs_L_per_h_at_70kg": cl,
                "V_abs_L_at_70kg": v,
                "ke_1_per_h": cl / v,
            },
        },
    )
    write_yaml(
        drug_dir / "targets.yml",
        {
            "scenario": {"dose": {"value": dose_mg, "unit": "mg"}},
            "targets": {
                "auc": {"value": dose_mg * 1000.0 / cl, "unit": "ng*h/mL"},
                "t_half": {"value": half_life_h, "unit": "h"},
            },
        },
    )
    write_yaml(
        drug_dir / "spec_pk1_iv.yml",
        {
            "study": {"id": f"OSP_{slug}", "title": f"{slug} demo"},
            "population": {"n": 2},
            "regimen": {"route": "iv_bolus", "arms": {"A": {"n": 2, "dose_mg": dose_mg}}},
            "sampling": {"t_end_h": 24.0, "dt_h": 1.0, "include_t0": True},
            "model": {
                "template": "pk1_iv_ode",
                "units": {"conc": "ng/mL", "mult": 1000},
                "theta": {"CL": cl, "V": v},
            },
        },
    )


def write_workflow_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    sim_csv = tmp_path / "sim_full.csv"
    pk_yml = tmp_path / "pk.yml"
    targets_yml = tmp_path / "targets.yml"
    spec_yml = tmp_path / "spec_pk1_iv.yml"
    rows = [
        {"ID": "1", "time": "0", "evid": "0", "CP": "100", "ARM": "A", "WT": "70", "AGE": "40", "SEX_CHAR": "M", "DOSE_MG": "100", "STUDYID": "OSP_test", "USUBJID": "OSP_test-001"},
        {"ID": "1", "time": "1", "evid": "0", "CP": "50", "ARM": "A", "WT": "70", "AGE": "40", "SEX_CHAR": "M", "DOSE_MG": "100", "STUDYID": "OSP_test", "USUBJID": "OSP_test-001"},
        {"ID": "1", "time": "2", "evid": "0", "CP": "25", "ARM": "A", "WT": "70", "AGE": "40", "SEX_CHAR": "M", "DOSE_MG": "100", "STUDYID": "OSP_test", "USUBJID": "OSP_test-001"},
        {"ID": "1", "time": "3", "evid": "0", "CP": "12.5", "ARM": "A", "WT": "70", "AGE": "40", "SEX_CHAR": "M", "DOSE_MG": "100", "STUDYID": "OSP_test", "USUBJID": "OSP_test-001"},
    ]
    write_csv(sim_csv, rows, list(rows[0].keys()))
    expected_auc = 131.25 + 12.5 / math.log(2)
    write_yaml(
        targets_yml,
        {
            "scenario": {"dose": {"value": 100.0, "unit": "mg"}},
            "targets": {
                "auc": {"value": expected_auc, "unit": "ng*h/mL"},
                "t_half": {"value": 1.0, "unit": "h"},
            },
        },
    )
    write_yaml(
        pk_yml,
        {
            "pk_parsed": {"half_life_h": 1.0},
            "derived": {
                "CL_abs_L_per_h_at_70kg": 100.0 * 1000.0 / expected_auc,
                "V_abs_L_at_70kg": 1.0,
            },
        },
    )
    write_yaml(
        spec_yml,
        {
            "study": {"id": "OSP_test", "title": "Test Drug"},
            "regimen": {"route": "iv_bolus", "arms": {"A": {"n": 1, "dose_mg": 100.0}}},
        },
    )
    return sim_csv, pk_yml, targets_yml, spec_yml


def test_run_harness_executes_demo_set_from_config(tmp_path: Path) -> None:
    drugs_dir = tmp_path / "drugs"
    write_demo_drug(drugs_dir, "iv_demo")
    config = tmp_path / "harness.yml"
    out_dir = tmp_path / "harness_out"
    write_yaml(
        config,
        {
            "version": "0.1",
            "mode": "demo_set",
            "drugs_dir": str(drugs_dir),
            "out_dir": str(out_dir),
            "drugs": ["iv_demo"],
            "simulation": {"engine": "analytical_demo"},
            "sampling": {"times_h": [0, 1, 2, 4, 8, 12, 24]},
            "validation": {"allow_failed": True},
        },
    )

    result = run_harness(config)

    assert result.status == "OK"
    assert result.mode == "demo_set"
    assert result.files["manifest"].exists()
    assert result.files["status_json"].exists()
    assert (out_dir / "summary.csv").exists()
    rows = read_csv(out_dir / "summary.csv")
    assert rows[0]["drug"] == "iv_demo"
    manifest = yaml.safe_load(result.files["manifest"].read_text(encoding="utf-8"))
    assert manifest["mode"] == "demo_set"
    assert manifest["simulation_engine"] == "analytical_demo"
    status = json.loads(result.files["status_json"].read_text(encoding="utf-8"))
    assert status["status"] == "OK"
    assert status["mode"] == "demo_set"
    assert status["outputs"]["summary_csv"].endswith("summary.csv")
    assert status["counts"]["drugs"] == 1


def test_run_harness_executes_post_simulation_workflow_from_config(tmp_path: Path) -> None:
    sim_csv, pk_yml, targets_yml, spec_yml = write_workflow_inputs(tmp_path)
    config = tmp_path / "harness.yml"
    out_dir = tmp_path / "workflow"
    write_yaml(
        config,
        {
            "version": "0.1",
            "mode": "post_simulation",
            "out_dir": str(out_dir),
            "inputs": {
                "sim_full_csv": str(sim_csv),
                "pk_yml": str(pk_yml),
                "targets_yml": str(targets_yml),
                "spec_yml": str(spec_yml),
            },
            "sampling": {"times_h": [0, 1, 2, 3]},
            "validation": {"allow_failed": False},
        },
    )

    result = run_harness(config)

    assert result.status == "OK"
    assert result.mode == "post_simulation"
    assert (out_dir / "analysis_inputs" / "ADPC.csv").exists()
    manifest = yaml.safe_load(result.files["manifest"].read_text(encoding="utf-8"))
    assert manifest["mode"] == "post_simulation"
    assert manifest["outputs"]["workflow_manifest"].endswith("MANIFEST.yml")
    assert result.files["status_json"].exists()
    status = json.loads(result.files["status_json"].read_text(encoding="utf-8"))
    assert status["mode"] == "post_simulation"
    assert status["status"] == "OK"
    assert status["outputs"]["adpc_csv"].endswith("ADPC.csv")
    assert status["counts"]["analysis_adpc_rows"] == 4


def test_run_harness_cli(tmp_path: Path) -> None:
    drugs_dir = tmp_path / "drugs"
    write_demo_drug(drugs_dir, "iv_demo")
    out_dir = tmp_path / "harness_out"
    config = tmp_path / "harness.yml"
    write_yaml(
        config,
        {
            "version": "0.1",
            "mode": "demo_set",
            "drugs_dir": str(drugs_dir),
            "out_dir": str(out_dir),
            "drugs": ["iv_demo"],
            "simulation": {"engine": "analytical_demo"},
            "sampling": {"times_h": [0, 1, 2, 4, 8, 12, 24]},
        },
    )

    completed = subprocess.run(
        [sys.executable, "tools/run_harness.py", str(config)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Harness: OK" in completed.stdout
    assert (out_dir / "HARNESS_MANIFEST.yml").exists()
    assert (out_dir / "HARNESS_STATUS.json").exists()
    assert "status_json:" in completed.stdout
