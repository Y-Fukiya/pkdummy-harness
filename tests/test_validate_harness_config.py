from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tools.validate_harness_config import validate_harness_config


ROOT = Path(__file__).resolve().parents[1]


def write_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")


def test_validate_harness_config_accepts_demo_set_config() -> None:
    issues = validate_harness_config(
        {
            "version": "0.1",
            "mode": "demo_set",
            "drugs_dir": "drugs",
            "out_dir": "outputs/demo_set_config",
            "drugs": ["aciclovir"],
            "simulation": {
                "engine": "analytical_demo",
                "variability": {"iiv_cv": 0.1, "residual_cv": 0.05, "seed": 123},
            },
            "sampling": {"times_h": [0, 1, 2, 4], "method": "log-linear", "predose_mdv1": True},
            "validation": {"allow_failed": True},
        }
    )

    assert issues == []


def test_validate_harness_config_rejects_deprecated_max_loops() -> None:
    issues = validate_harness_config(
        {
            "version": "0.1",
            "mode": "demo_set",
            "drugs_dir": "drugs",
            "out_dir": "outputs/demo_set_config",
            "drugs": ["aciclovir"],
            "sampling": {"times_h": [0, 1, 2, 4]},
            "validation": {"max_loops": 3},
        }
    )

    assert "validation.max_loops is no longer supported; validation is a single deterministic check" in issues


def test_validate_harness_config_rejects_missing_required_fields() -> None:
    issues = validate_harness_config({"version": "0.1", "mode": "post_simulation", "out_dir": "outputs/run"})

    assert "inputs.sim_full_csv is required for post_simulation mode" in issues
    assert "Provide either inputs.drug or all of inputs.pk_yml, inputs.targets_yml, inputs.spec_yml" in issues
    assert "sampling.times_h or sampling.schedule_csv is required" in issues


def test_validate_harness_config_rejects_bad_variability_values() -> None:
    issues = validate_harness_config(
        {
            "version": "0.1",
            "mode": "demo_set",
            "out_dir": "outputs/demo",
            "drugs": ["aciclovir"],
            "simulation": {"engine": "analytical_demo", "variability": {"iiv_cv": -0.1, "residual_cv": "bad"}},
            "sampling": {"times_h": [0, 1]},
        }
    )

    assert "simulation.variability.iiv_cv must be a non-negative number" in issues
    assert "simulation.variability.residual_cv must be a non-negative number" in issues


def test_validate_harness_config_accepts_subject_override() -> None:
    issues = validate_harness_config(
        {
            "version": "0.1",
            "mode": "demo_set",
            "out_dir": "outputs/demo",
            "drugs": ["apixaban"],
            "simulation": {"engine": "analytical_demo", "n_subjects": 50},
            "sampling": {"times_h": [0, 1, 2], "method": "exact", "predose_mdv1": True},
        }
    )

    assert issues == []


def test_validate_harness_config_accepts_repeated_oral_demo() -> None:
    issues = validate_harness_config(
        {
            "version": "0.1",
            "mode": "repeated_oral_demo",
            "out_dir": "outputs/repeated",
            "drugs": ["apixaban"],
            "simulation": {
                "engine": "analytical_demo",
                "n_subjects": 50,
                "t_end_h": 156,
                "dt_h": 0.5,
                "repeated_dosing": {"interval_h": 12, "dose_count": 13, "analysis_dose_number": 13},
            },
            "sampling": {
                "trough_times_h": [0, 24, 48, 72, 96, 120, 144, 156],
                "ss_times_after_dose_h": [0, 0.5, 1, 2, 3, 4, 6, 8, 12],
                "method": "exact",
            },
            "nca": {"integration": "linear-up-log-down", "interval_h": [0, 12]},
        }
    )

    assert issues == []


def test_validate_harness_config_accepts_repeated_oral_mrgsolve_engine() -> None:
    issues = validate_harness_config(
        {
            "version": "0.1",
            "mode": "repeated_oral_demo",
            "out_dir": "outputs/repeated_mrgsolve",
            "drugs": ["apixaban"],
            "simulation": {
                "engine": "mrgsolve",
                "n_subjects": 50,
                "t_end_h": 156,
                "dt_h": 0.5,
                "repeated_dosing": {"interval_h": 12, "dose_count": 13, "analysis_dose_number": 13},
            },
            "sampling": {
                "trough_times_h": [0, 24, 48, 72, 96, 120, 144, 156],
                "ss_times_after_dose_h": [0, 0.5, 1, 2, 3, 4, 6, 8, 12],
                "method": "exact",
            },
            "nca": {"integration": "linear-up-log-down", "interval_h": [0, 12]},
        }
    )

    assert issues == []


def test_validate_harness_config_rejects_unsampled_partial_auc_boundary() -> None:
    issues = validate_harness_config(
        {
            "version": "0.1",
            "mode": "repeated_oral_demo",
            "out_dir": "outputs/repeated",
            "drugs": ["apixaban"],
            "simulation": {
                "engine": "analytical_demo",
                "n_subjects": 50,
                "t_end_h": 156,
                "dt_h": 0.5,
                "repeated_dosing": {"interval_h": 12, "dose_count": 13, "analysis_dose_number": 13},
            },
            "sampling": {
                "trough_times_h": [0, 24, 48, 72, 96, 120, 144, 156],
                "ss_times_after_dose_h": [0, 0.5, 1, 2, 3, 6, 8, 12],
                "method": "exact",
            },
            "nca": {"integration": "linear-up-log-down", "interval_h": [0, 12], "partial_intervals_h": [[0, 4], [4, 12]]},
        }
    )

    assert "nca.partial_intervals_h boundaries must be present in sampling.ss_times_after_dose_h" in issues


def test_validate_harness_config_rejects_duplicate_or_negative_sampling_times() -> None:
    issues = validate_harness_config(
        {
            "version": "0.1",
            "mode": "demo_set",
            "out_dir": "outputs/demo",
            "drugs": ["apixaban"],
            "simulation": {"engine": "analytical_demo"},
            "sampling": {"times_h": [-1, 1, 1], "method": "exact"},
        }
    )

    assert "sampling.times_h must contain finite non-negative numeric values" in issues
    duplicate_issues = validate_harness_config(
        {
            "version": "0.1",
            "mode": "demo_set",
            "out_dir": "outputs/demo",
            "drugs": ["apixaban"],
            "simulation": {"engine": "analytical_demo"},
            "sampling": {"times_h": [0, 1, 1], "method": "exact"},
        }
    )
    assert "sampling.times_h must not contain duplicate times" in duplicate_issues


def test_validate_harness_config_rejects_repeated_run_that_ends_before_final_interval() -> None:
    config = {
        "version": "0.1",
        "mode": "repeated_oral_demo",
        "out_dir": "outputs/repeated",
        "drugs": ["apixaban"],
        "simulation": {
            "engine": "analytical_demo",
            "n_subjects": 50,
            "t_end_h": 12,
            "dt_h": 0.5,
            "repeated_dosing": {"interval_h": 12, "dose_count": 13, "analysis_dose_number": 13},
        },
        "sampling": {
            "trough_times_h": [0, 120, 144],
            "ss_times_after_dose_h": [0, 12],
            "method": "exact",
        },
        "nca": {"integration": "linear-up-log-down", "interval_h": [0, 12]},
    }
    issues = validate_harness_config(config)
    assert "simulation.t_end_h must cover the final dose time" in issues
    assert "simulation.t_end_h must cover the full final analysis interval" in issues


@pytest.mark.parametrize("value", [0, -1, 1.5, "not-a-number", float("nan"), float("inf"), True])
def test_validate_harness_config_rejects_invalid_subject_override(value: object) -> None:
    issues = validate_harness_config(
        {
            "version": "0.1",
            "mode": "demo_set",
            "out_dir": "outputs/demo",
            "drugs": ["apixaban"],
            "simulation": {"engine": "analytical_demo", "n_subjects": value},
            "sampling": {"times_h": [0, 1]},
        }
    )

    assert "simulation.n_subjects must be a positive integer" in issues


def test_validate_harness_config_cli(tmp_path: Path) -> None:
    config = tmp_path / "harness.yml"
    write_yaml(
        config,
        {
            "version": "0.1",
            "mode": "demo_set",
            "out_dir": str(tmp_path / "out"),
            "drugs": ["aciclovir"],
            "simulation": {"engine": "analytical_demo"},
            "sampling": {"times_h": [0, 1]},
        },
    )

    completed = subprocess.run(
        [sys.executable, "tools/validate_harness_config.py", str(config)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Harness config validation: OK" in completed.stdout


def test_run_harness_rejects_invalid_config_before_dispatch(tmp_path: Path) -> None:
    from tools.run_harness import run_harness

    config = tmp_path / "bad.yml"
    write_yaml(config, {"version": "0.1", "mode": "demo_set", "out_dir": str(tmp_path / "out"), "drugs": []})

    with pytest.raises(ValueError, match="drugs must be a non-empty list"):
        run_harness(config)
