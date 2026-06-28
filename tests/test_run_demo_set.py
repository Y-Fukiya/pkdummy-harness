from __future__ import annotations

import csv
import math
import subprocess
import sys
from pathlib import Path

import yaml

import pytest

from tools.run_demo_set import make_demo_sim_full, run_demo_set


ROOT = Path(__file__).resolve().parents[1]


def write_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_demo_drug(
    drugs_dir: Path,
    slug: str,
    *,
    route: str,
    template: str,
    infusion_h: float | None = None,
) -> None:
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
            "route_inferred": "po" if route == "oral" else "iv",
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
    theta = {"CL": cl, "V": v}
    if route == "oral":
        theta.update({"KA": 1.2, "F1": 1.0, "ALAG1": 0.0})
    arm = {"n": 2, "dose_mg": dose_mg}
    if infusion_h is not None:
        arm["infusion_h"] = infusion_h
    write_yaml(
        drug_dir / f"spec_pk1_{'oral' if route == 'oral' else 'iv'}.yml",
        {
            "study": {"id": f"OSP_{slug}", "title": f"{slug} demo"},
            "population": {"n": 2},
            "regimen": {"route": route, "arms": {"A": arm}},
            "sampling": {"t_end_h": 24.0, "dt_h": 1.0, "include_t0": True},
            "model": {
                "template": template,
                "units": {"conc": "ng/mL", "mult": 1000},
                "theta": theta,
            },
        },
    )


def test_run_demo_set_creates_multi_drug_workflow_outputs(tmp_path: Path) -> None:
    drugs_dir = tmp_path / "drugs"
    write_demo_drug(drugs_dir, "oral_demo", route="oral", template="pk1_oral_ode")
    write_demo_drug(drugs_dir, "iv_demo", route="iv_bolus", template="pk1_iv_ode")
    out_dir = tmp_path / "demo_set"

    result = run_demo_set(
        drugs=["oral_demo", "iv_demo"],
        drugs_dir=drugs_dir,
        out_dir=out_dir,
        sample_times_h=[0, 1, 2, 4, 8, 12, 24],
    )

    assert result.status in {"OK", "WARN"}
    assert result.counts["drugs"] == 2
    assert result.files["summary_csv"].exists()
    assert result.files["summary_md"].exists()
    rows = read_csv(result.files["summary_csv"])
    assert [row["drug"] for row in rows] == ["oral_demo", "iv_demo"]
    assert all(row["analysis_adpc_rows"] == "14" for row in rows)
    assert all(row["analysis_nca_rows"] == "14" for row in rows)
    assert all(row["analysis_poppk_rows"] == "16" for row in rows)
    for slug in ("oral_demo", "iv_demo"):
        assert (out_dir / slug / "raw" / "sim_full.csv").exists()
        assert (out_dir / slug / "workflow" / "analysis_inputs" / "ADPC.csv").exists()
        assert (out_dir / slug / "workflow" / "analysis_inputs" / "NCA_INPUT.csv").exists()
        assert (out_dir / slug / "workflow" / "analysis_inputs" / "POPPK_INPUT.csv").exists()


def test_run_demo_set_cli(tmp_path: Path) -> None:
    drugs_dir = tmp_path / "drugs"
    write_demo_drug(drugs_dir, "oral_demo", route="oral", template="pk1_oral_ode")
    out_dir = tmp_path / "demo_set"

    completed = subprocess.run(
        [
            sys.executable,
            "tools/run_demo_set.py",
            "--drugs",
            "oral_demo",
            "--drugs-dir",
            str(drugs_dir),
            "--out-dir",
            str(out_dir),
            "--times",
            "0,1,2,4,8,12,24",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Demo set: " in completed.stdout
    assert (out_dir / "summary.csv").exists()
    assert (out_dir / "oral_demo" / "workflow" / "analysis_inputs" / "POPPK_INPUT.csv").exists()


def test_run_demo_set_outputs_validate_recursively(tmp_path: Path) -> None:
    drugs_dir = tmp_path / "drugs"
    write_demo_drug(drugs_dir, "oral_demo", route="oral", template="pk1_oral_ode")
    out_dir = tmp_path / "demo_set"

    run_demo_set(
        drugs=["oral_demo"],
        drugs_dir=drugs_dir,
        out_dir=out_dir,
        sample_times_h=[0, 1, 2, 4, 8, 12, 24],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "tools/validate_manifest.py",
            "--recursive",
            str(out_dir),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout


def test_run_demo_set_can_add_lightweight_iiv_and_residual_variability(tmp_path: Path) -> None:
    drugs_dir = tmp_path / "drugs"
    write_demo_drug(drugs_dir, "iv_demo", route="iv_bolus", template="pk1_iv_ode")
    out_dir = tmp_path / "demo_set"

    run_demo_set(
        drugs=["iv_demo"],
        drugs_dir=drugs_dir,
        out_dir=out_dir,
        sample_times_h=[0, 1, 2, 4],
        variability={"iiv_cv": 0.2, "residual_cv": 0.1, "seed": 123},
    )

    sim_rows = read_csv(out_dir / "iv_demo" / "raw" / "sim_full.csv")
    one_hour = [row for row in sim_rows if row["time"] == "1"]
    assert len(one_hour) == 2
    assert one_hour[0]["CP"] != one_hour[1]["CP"]
    assert all(row["IPRED"] != row["DV"] for row in one_hour)

    manifest = yaml.safe_load((out_dir / "DEMO_MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["settings"]["variability"] == {"iiv_cv": 0.2, "residual_cv": 0.1, "seed": 123}


def test_make_demo_sim_full_uses_iv_infusion_when_infusion_h_is_set(tmp_path: Path) -> None:
    drugs_dir = tmp_path / "drugs"
    write_demo_drug(drugs_dir, "iv_infusion_demo", route="iv", template="pk1_iv_ode", infusion_h=1.0)
    sim_full = tmp_path / "sim_full.csv"

    make_demo_sim_full(
        spec_yml=drugs_dir / "iv_infusion_demo" / "spec_pk1_iv.yml",
        out_csv=sim_full,
    )

    rows = read_csv(sim_full)
    by_time = {float(row["time"]): float(row["CP"]) for row in rows if row["ID"] == "1"}
    assert by_time[0.0] == 0.0
    assert by_time[1.0] > by_time[0.0]
    assert by_time[1.0] > by_time[2.0]
    assert by_time[1.0] < 100.0 / 20.0 * 1000.0


def test_make_demo_sim_full_supports_sc_first_order_absorption(tmp_path: Path) -> None:
    drugs_dir = tmp_path / "drugs"
    write_demo_drug(drugs_dir, "sc_demo", route="sc", template="pk1_iv_ode")
    sim_full = tmp_path / "sim_full.csv"

    make_demo_sim_full(
        spec_yml=drugs_dir / "sc_demo" / "spec_pk1_iv.yml",
        out_csv=sim_full,
    )

    rows = read_csv(sim_full)
    by_time = {float(row["time"]): float(row["CP"]) for row in rows if row["ID"] == "1"}
    assert by_time[0.0] == 0.0
    assert by_time[1.0] > 0.0


def test_make_demo_sim_full_rejects_unknown_route_instead_of_bolus_fallback(tmp_path: Path) -> None:
    drugs_dir = tmp_path / "drugs"
    write_demo_drug(drugs_dir, "unknown_demo", route="topical", template="pk1_iv_ode")

    with pytest.raises(ValueError, match="Unsupported demo route"):
        make_demo_sim_full(
            spec_yml=drugs_dir / "unknown_demo" / "spec_pk1_iv.yml",
            out_csv=tmp_path / "sim_full.csv",
        )
