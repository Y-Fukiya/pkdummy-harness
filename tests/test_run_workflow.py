from __future__ import annotations

import csv
import math
import subprocess
import sys
from pathlib import Path

import yaml

from tools.run_workflow import run_workflow


ROOT = Path(__file__).resolve().parents[1]


def write_yaml(path: Path, obj: dict) -> None:
    path.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")


def write_sim_csv(path: Path) -> None:
    rows = [
        {"ID": "1", "time": "0", "evid": "0", "CP": "100", "ARM": "A", "WT": "70", "AGE": "40", "SEX_CHAR": "M", "DOSE_MG": "100", "STUDYID": "OSP_test", "USUBJID": "OSP_test-001"},
        {"ID": "1", "time": "1", "evid": "0", "CP": "50", "ARM": "A", "WT": "70", "AGE": "40", "SEX_CHAR": "M", "DOSE_MG": "100", "STUDYID": "OSP_test", "USUBJID": "OSP_test-001"},
        {"ID": "1", "time": "2", "evid": "0", "CP": "25", "ARM": "A", "WT": "70", "AGE": "40", "SEX_CHAR": "M", "DOSE_MG": "100", "STUDYID": "OSP_test", "USUBJID": "OSP_test-001"},
        {"ID": "1", "time": "3", "evid": "0", "CP": "12.5", "ARM": "A", "WT": "70", "AGE": "40", "SEX_CHAR": "M", "DOSE_MG": "100", "STUDYID": "OSP_test", "USUBJID": "OSP_test-001"},
    ]
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    sim_csv = tmp_path / "sim_full.csv"
    pk_yml = tmp_path / "pk.yml"
    targets_yml = tmp_path / "targets.yml"
    spec_yml = tmp_path / "spec_pk1_oral.yml"
    write_sim_csv(sim_csv)
    expected_auc = 131.25 + 12.5 / math.log(2)
    write_yaml(
        targets_yml,
        {
            "scenario": {"dose": {"value": 100.0, "unit": "mg"}},
            "targets": {
                "auc": {"value": expected_auc, "unit": "ng*h/mL", "summary": "geometric_mean"},
                "t_half": {"value": 1.0, "unit": "h", "summary": "arithmetic_mean"},
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
            "regimen": {"route": "oral", "arms": {"A": {"n": 1, "dose_mg": 100.0}}},
        },
    )
    return sim_csv, pk_yml, targets_yml, spec_yml


def test_run_workflow_creates_trace_manifest_samples_and_sdtm_like_domains(tmp_path: Path) -> None:
    sim_csv, pk_yml, targets_yml, spec_yml = write_inputs(tmp_path)
    out_dir = tmp_path / "workflow"

    result = run_workflow(
        sim_full_csv=sim_csv,
        out_dir=out_dir,
        pk_yml=pk_yml,
        targets_yml=targets_yml,
        spec_yml=spec_yml,
        times_h=[0, 1, 2, 3],
    )

    assert result.status == "OK"
    assert result.validation_status == "OK"
    assert result.counts["clinical_sample_rows"] == 4
    assert result.counts["sdtm_like_dm_rows"] == 1
    assert result.counts["sdtm_like_vs_rows"] == 4
    assert result.counts["sdtm_like_lb_rows"] == 1
    assert result.counts["sdtm_like_ex_rows"] == 1
    assert result.counts["sdtm_like_pc_rows"] == 4
    assert result.counts["analysis_adpc_rows"] == 4
    assert result.counts["analysis_nca_rows"] == 4
    assert result.counts["analysis_poppk_rows"] == 5
    assert (out_dir / "reports" / "simulation_validation.md").exists()
    assert (out_dir / "raw" / "clinical_samples.csv").exists()
    assert (out_dir / "sdtm_like" / "PC.csv").exists()
    assert (out_dir / "analysis_inputs" / "ADPC.csv").exists()
    assert (out_dir / "analysis_inputs" / "NCA_INPUT.csv").exists()
    assert (out_dir / "analysis_inputs" / "POPPK_INPUT.csv").exists()
    assert "VALIDATE status=OK" in (out_dir / "trace.log").read_text(encoding="utf-8")
    assert "ANALYSIS_INPUTS status=OK" in (out_dir / "trace.log").read_text(encoding="utf-8")
    manifest = yaml.safe_load((out_dir / "MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["purpose"] == "pk_fixture_post_simulation_workflow"
    assert manifest["status"] == "OK"
    assert manifest["validation"]["status"] == "OK"


def test_run_workflow_propagates_concentration_unit_and_poppk_cmt_convention(tmp_path: Path) -> None:
    sim_csv, pk_yml, targets_yml, spec_yml = write_inputs(tmp_path)
    out_dir = tmp_path / "workflow"

    run_workflow(
        sim_full_csv=sim_csv,
        out_dir=out_dir,
        pk_yml=pk_yml,
        targets_yml=targets_yml,
        spec_yml=spec_yml,
        times_h=[0, 1, 2, 3],
        pc_conc_unit="ug/mL",
        dose_cmt="10",
        observation_cmt="20",
    )

    pc = list(csv.DictReader((out_dir / "sdtm_like" / "PC.csv").open(encoding="utf-8", newline="")))
    poppk = list(csv.DictReader((out_dir / "analysis_inputs" / "POPPK_INPUT.csv").open(encoding="utf-8", newline="")))
    assert {row["PCSTRESU"] for row in pc} == {"ug/mL"}
    assert poppk[0]["CMT"] == "10"
    assert {row["CMT"] for row in poppk[1:]} == {"20"}


def test_run_workflow_can_mark_predose_observation_mdv1(tmp_path: Path) -> None:
    sim_csv, pk_yml, targets_yml, spec_yml = write_inputs(tmp_path)
    out_dir = tmp_path / "workflow"

    run_workflow(
        sim_full_csv=sim_csv,
        out_dir=out_dir,
        pk_yml=pk_yml,
        targets_yml=targets_yml,
        spec_yml=spec_yml,
        times_h=[0, 1],
        predose_mdv1=True,
    )

    poppk = list(csv.DictReader((out_dir / "analysis_inputs" / "POPPK_INPUT.csv").open(encoding="utf-8", newline="")))
    predose = poppk[1]
    assert predose["TIME"] == "0"
    assert predose["EVID"] == "0"
    assert predose["MDV"] == "1"


def test_run_workflow_accepts_existing_domain_csvs_and_fills_pc_skeleton(tmp_path: Path) -> None:
    sim_csv, pk_yml, targets_yml, spec_yml = write_inputs(tmp_path)
    dm_csv = tmp_path / "DM_existing.csv"
    pc_csv = tmp_path / "PC_skeleton.csv"
    with dm_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["STUDYID", "DOMAIN", "USUBJID", "CUSTOMDM"])
        writer.writeheader()
        writer.writerow({"STUDYID": "OSP_test", "DOMAIN": "DM", "USUBJID": "OSP_test-001", "CUSTOMDM": "keep"})
    with pc_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["STUDYID", "DOMAIN", "USUBJID", "PCTPTNUM", "PCSTRESN", "PCORRES"])
        writer.writeheader()
        writer.writerow({"STUDYID": "OSP_test", "DOMAIN": "PC", "USUBJID": "OSP_test-001", "PCTPTNUM": "2", "PCSTRESN": "", "PCORRES": ""})
    out_dir = tmp_path / "workflow"

    result = run_workflow(
        sim_full_csv=sim_csv,
        out_dir=out_dir,
        pk_yml=pk_yml,
        targets_yml=targets_yml,
        spec_yml=spec_yml,
        times_h=[0, 1, 2, 3],
        dm_csv=dm_csv,
        pc_csv=pc_csv,
    )

    assert result.status == "OK"
    dm = list(csv.DictReader((out_dir / "sdtm_like" / "DM.csv").open(encoding="utf-8", newline="")))
    pc = list(csv.DictReader((out_dir / "sdtm_like" / "PC.csv").open(encoding="utf-8", newline="")))
    assert dm[0]["CUSTOMDM"] == "keep"
    assert pc[0]["PCSTRESN"] == "50"
    sdtm_manifest = yaml.safe_load((out_dir / "sdtm_like" / "MANIFEST.yml").read_text(encoding="utf-8"))
    assert sdtm_manifest["domain_sources"]["DM"] == "existing_csv"
    assert sdtm_manifest["domain_sources"]["PC"] == "existing_pc_skeleton_filled"


def test_run_workflow_stops_before_sampling_on_validation_failed_by_default(tmp_path: Path) -> None:
    sim_csv, pk_yml, targets_yml, spec_yml = write_inputs(tmp_path)
    write_yaml(targets_yml, {"targets": {"auc": {"value": 1.0, "unit": "ng*h/mL"}}})
    out_dir = tmp_path / "workflow"

    result = run_workflow(
        sim_full_csv=sim_csv,
        out_dir=out_dir,
        pk_yml=pk_yml,
        targets_yml=targets_yml,
        spec_yml=spec_yml,
        times_h=[0, 1, 2, 3],
        warn_rel=0.01,
        fail_rel=0.02,
    )

    assert result.status == "FAILED"
    assert result.validation_status == "FAILED"
    assert not (out_dir / "raw" / "clinical_samples.csv").exists()
    assert "STOP validation_failed" in (out_dir / "trace.log").read_text(encoding="utf-8")


def test_run_workflow_can_continue_after_validation_failed_but_marks_warn(tmp_path: Path) -> None:
    sim_csv, pk_yml, targets_yml, spec_yml = write_inputs(tmp_path)
    write_yaml(targets_yml, {"targets": {"auc": {"value": 1.0, "unit": "ng*h/mL"}}})
    out_dir = tmp_path / "workflow"

    result = run_workflow(
        sim_full_csv=sim_csv,
        out_dir=out_dir,
        pk_yml=pk_yml,
        targets_yml=targets_yml,
        spec_yml=spec_yml,
        times_h=[0, 1, 2, 3],
        warn_rel=0.01,
        fail_rel=0.02,
        allow_validation_failed=True,
    )

    assert result.status == "WARN"
    assert result.validation_status == "FAILED"
    assert any(warning.startswith("validation failure allowed:") for warning in result.warnings)
    assert (out_dir / "raw" / "clinical_samples.csv").exists()


def test_run_workflow_cli(tmp_path: Path) -> None:
    sim_csv, pk_yml, targets_yml, spec_yml = write_inputs(tmp_path)
    out_dir = tmp_path / "workflow"

    completed = subprocess.run(
        [
            sys.executable,
            "tools/run_workflow.py",
            "--sim-full",
            str(sim_csv),
            "--pk",
            str(pk_yml),
            "--targets",
            str(targets_yml),
            "--spec",
            str(spec_yml),
            "--times",
            "0,1,2,3",
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Workflow: OK" in completed.stdout
    assert (out_dir / "MANIFEST.yml").exists()
