from __future__ import annotations

import csv
import math
import subprocess
import sys
from pathlib import Path

import yaml

from tools.validate_simulation import (
    SimulationTolerances,
    compute_subject_metrics,
    render_markdown,
    validate_simulation,
    validate_simulation_loop,
)


ROOT = Path(__file__).resolve().parents[1]


def write_yaml(path: Path, obj: dict) -> None:
    path.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")


def write_sim_csv(path: Path) -> None:
    rows = [
        {"ID": "1", "time": "0", "evid": "0", "CP": "100"},
        {"ID": "1", "time": "1", "evid": "0", "CP": "50"},
        {"ID": "1", "time": "2", "evid": "0", "CP": "25"},
        {"ID": "1", "time": "3", "evid": "0", "CP": "12.5"},
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "time", "evid", "CP"])
        writer.writeheader()
        writer.writerows(rows)


def write_sim_csv_with_unit(path: Path, *, unit: str, scale: float) -> None:
    rows = [
        {"ID": "1", "time": "0", "evid": "0", "CP": str(100 * scale), "CP_UNIT": unit},
        {"ID": "1", "time": "1", "evid": "0", "CP": str(50 * scale), "CP_UNIT": unit},
        {"ID": "1", "time": "2", "evid": "0", "CP": str(25 * scale), "CP_UNIT": unit},
        {"ID": "1", "time": "3", "evid": "0", "CP": str(12.5 * scale), "CP_UNIT": unit},
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "time", "evid", "CP", "CP_UNIT"])
        writer.writeheader()
        writer.writerows(rows)


def test_compute_subject_metrics_recalculates_auc_cmax_tmax_and_half_life() -> None:
    rows = [
        {"ID": "1", "time": "0", "evid": "0", "CP": "100"},
        {"ID": "1", "time": "1", "evid": "0", "CP": "50"},
        {"ID": "1", "time": "2", "evid": "0", "CP": "25"},
        {"ID": "1", "time": "3", "evid": "0", "CP": "12.5"},
    ]

    metrics = compute_subject_metrics(rows)

    assert metrics["1"].cmax == 100.0
    assert metrics["1"].tmax_h == 0.0
    assert math.isclose(metrics["1"].half_life_h, 1.0)
    expected_auc = 131.25 + 12.5 / math.log(2)
    assert math.isclose(metrics["1"].auc0_inf, expected_auc)


def test_validate_simulation_compares_targets_and_pk_yaml(tmp_path: Path) -> None:
    sim_csv = tmp_path / "sim_full.csv"
    pk_yml = tmp_path / "pk.yml"
    targets_yml = tmp_path / "targets.yml"
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

    result = validate_simulation(
        sim_csv,
        pk_yml,
        targets_yml,
        tolerances=SimulationTolerances(warn_rel=0.10, fail_rel=0.20),
    )

    assert result.status == "OK"
    assert result.failures == []
    assert result.summary["n_subjects"] == 1
    assert math.isclose(result.summary["auc0_inf_geomean"], expected_auc)
    assert math.isclose(result.summary["half_life_h_mean"], 1.0)


def test_validate_simulation_uses_input_concentration_unit_for_cl_implied_auc(tmp_path: Path) -> None:
    sim_csv = tmp_path / "sim_full.csv"
    pk_yml = tmp_path / "pk.yml"
    targets_yml = tmp_path / "targets.yml"
    write_sim_csv_with_unit(sim_csv, unit="ug/mL", scale=0.001)

    expected_auc = (131.25 + 12.5 / math.log(2)) * 0.001
    write_yaml(
        targets_yml,
        {
            "scenario": {"dose": {"value": 100.0, "unit": "mg"}},
            "targets": {
                "auc": {"value": expected_auc, "unit": "ug*h/mL", "summary": "geometric_mean"},
                "t_half": {"value": 1.0, "unit": "h", "summary": "arithmetic_mean"},
            },
        },
    )
    write_yaml(
        pk_yml,
        {
            "pk_parsed": {"half_life_h": 1.0},
            "derived": {
                "CL_abs_L_per_h_at_70kg": 100.0 / expected_auc,
                "V_abs_L_at_70kg": 1.0,
            },
        },
    )

    result = validate_simulation(
        sim_csv,
        pk_yml,
        targets_yml,
        tolerances=SimulationTolerances(warn_rel=0.10, fail_rel=0.20),
    )
    report = render_markdown(result, sim_csv, pk_yml, targets_yml)

    assert result.status == "OK"
    assert result.summary["concentration_unit"] == "ug/mL"
    assert result.summary["auc_unit"] == "ug*h/mL"
    assert "ug*h/mL" in report
    assert "ug/mL" in report


def test_validate_simulation_reports_failed_target_mismatch(tmp_path: Path) -> None:
    sim_csv = tmp_path / "sim_full.csv"
    pk_yml = tmp_path / "pk.yml"
    targets_yml = tmp_path / "targets.yml"
    write_sim_csv(sim_csv)
    write_yaml(targets_yml, {"targets": {"auc": {"value": 10.0, "unit": "ng*h/mL"}}})
    write_yaml(pk_yml, {"pk_parsed": {}, "derived": {}})

    result = validate_simulation(
        sim_csv,
        pk_yml,
        targets_yml,
        tolerances=SimulationTolerances(warn_rel=0.10, fail_rel=0.20),
    )

    assert result.status == "FAILED"
    assert any("targets.auc" in failure for failure in result.failures)


def test_validate_simulation_loop_repeats_warn_or_failed_results_three_times_by_default(tmp_path: Path) -> None:
    sim_csv = tmp_path / "sim_full.csv"
    pk_yml = tmp_path / "pk.yml"
    targets_yml = tmp_path / "targets.yml"
    write_sim_csv(sim_csv)
    write_yaml(targets_yml, {"targets": {"auc": {"value": 10.0, "unit": "ng*h/mL"}}})
    write_yaml(pk_yml, {"pk_parsed": {}, "derived": {}})

    loop = validate_simulation_loop(
        sim_csv,
        pk_yml,
        targets_yml,
        tolerances=SimulationTolerances(warn_rel=0.10, fail_rel=0.20),
    )

    assert loop.max_loops == 3
    assert loop.final_result.status == "FAILED"
    assert [attempt.status for attempt in loop.attempts] == ["FAILED", "FAILED", "FAILED"]


def test_validate_simulation_report_describes_loop_as_recheck_not_calibration(tmp_path: Path) -> None:
    sim_csv = tmp_path / "sim_full.csv"
    pk_yml = tmp_path / "pk.yml"
    targets_yml = tmp_path / "targets.yml"
    write_sim_csv(sim_csv)
    write_yaml(targets_yml, {"targets": {"auc": {"value": 10.0, "unit": "ng*h/mL"}}})
    write_yaml(pk_yml, {"pk_parsed": {}, "derived": {}})

    loop = validate_simulation_loop(
        sim_csv,
        pk_yml,
        targets_yml,
        tolerances=SimulationTolerances(warn_rel=0.10, fail_rel=0.20),
    )

    report = render_markdown(loop.final_result, sim_csv, pk_yml, targets_yml, loop=loop)

    assert "Validation rechecks repeat the same calculation only" in report
    assert "No optimization or calibration is performed" in report


def test_validate_simulation_loop_stops_after_one_ok_result(tmp_path: Path) -> None:
    sim_csv = tmp_path / "sim_full.csv"
    pk_yml = tmp_path / "pk.yml"
    targets_yml = tmp_path / "targets.yml"
    write_sim_csv(sim_csv)
    expected_auc = 131.25 + 12.5 / math.log(2)
    write_yaml(targets_yml, {"targets": {"auc": {"value": expected_auc, "unit": "ng*h/mL"}}})
    write_yaml(pk_yml, {"pk_parsed": {"half_life_h": 1.0}, "derived": {}})

    loop = validate_simulation_loop(sim_csv, pk_yml, targets_yml)

    assert loop.final_result.status == "OK"
    assert len(loop.attempts) == 1


def test_validate_simulation_cli_writes_markdown_report(tmp_path: Path) -> None:
    sim_csv = tmp_path / "sim_full.csv"
    pk_yml = tmp_path / "pk.yml"
    targets_yml = tmp_path / "targets.yml"
    report_md = tmp_path / "simulation_validation.md"
    write_sim_csv(sim_csv)
    expected_auc = 131.25 + 12.5 / math.log(2)
    write_yaml(targets_yml, {"targets": {"auc": {"value": expected_auc, "unit": "ng*h/mL"}}})
    write_yaml(pk_yml, {"pk_parsed": {"half_life_h": 1.0}, "derived": {}})

    completed = subprocess.run(
        [
            sys.executable,
            "tools/validate_simulation.py",
            str(sim_csv),
            "--pk",
            str(pk_yml),
            "--targets",
            str(targets_yml),
            "--out-md",
            str(report_md),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Simulation validation: OK" in completed.stdout
    assert "AUC0-inf" in report_md.read_text(encoding="utf-8")
