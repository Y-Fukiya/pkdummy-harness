from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import yaml

from tools.export_fixture_context import context_columns
from tools.run_demo_set import make_demo_sim_full
from tools.run_harness import run_harness


ROOT = Path(__file__).resolve().parents[1]


def read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def run_config(tmp_path: Path, config: dict):
    config_path = tmp_path / "harness.yml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return run_harness(config_path)


def demo_config(out_dir: Path, drugs_dir: Path, drugs: list[str]) -> dict:
    return {
        "version": "0.1",
        "mode": "demo_set",
        "out_dir": str(out_dir),
        "drugs_dir": str(drugs_dir),
        "drugs": drugs,
        "simulation": {"engine": "analytical_demo", "n_subjects": 2},
        "sampling": {"times_h": [0, 0.5, 1, 2, 4, 8, 12, 24]},
        "validation": {"allow_failed": True},
    }


def test_demo_top_level_preserves_mixed_drug_contexts(tmp_path: Path) -> None:
    output = tmp_path / "mixed"
    result = run_config(tmp_path, demo_config(output, ROOT / "drugs", ["triazolam", "albuterol"]))
    rows = read_csv(result.files["summary_csv"])

    assert [row.get("CLINICAL_ASSESSMENT") for row in rows] == ["clinical_hold", "not_assessed"]
    contexts = {
        drug: read_yaml(output / drug / "workflow" / "MANIFEST.yml")["fixture_context"]
        for drug in ("triazolam", "albuterol")
    }
    for row in rows:
        assert {key: row[key] for key in context_columns(contexts[row["drug"]])} == context_columns(contexts[row["drug"]])
    for name in ("DEMO_MANIFEST.yml", "HARNESS_MANIFEST.yml"):
        assert read_yaml(output / name).get("fixture_contexts") == contexts
    status = json.loads(result.files["status_json"].read_text(encoding="utf-8"))
    assert status.get("fixture_contexts") == contexts
    summary = result.files["summary_md"].read_text(encoding="utf-8")
    for value in ("Clinical", "Dose purpose", "clinical_hold", "not_assessed", "not_approved", "computational_stress_test"):
        assert value in summary


def test_failed_demo_still_reports_clinical_hold(tmp_path: Path) -> None:
    drugs_dir = tmp_path / "drugs"
    shutil.copytree(ROOT / "drugs" / "triazolam", drugs_dir / "triazolam")
    targets_path = drugs_dir / "triazolam" / "targets.yml"
    targets = read_yaml(targets_path)
    targets["targets"]["auc"]["value"] *= 100
    targets_path.write_text(yaml.safe_dump(targets), encoding="utf-8")
    output = tmp_path / "failed"
    config = demo_config(output, drugs_dir, ["triazolam"])
    config["validation"]["allow_failed"] = False
    result = run_config(tmp_path, config)

    assert result.status == "FAILED"
    assert not (output / "triazolam" / "workflow" / "analysis_inputs" / "ADPC.csv").exists()
    row = read_csv(result.files["summary_csv"])[0]
    assert row.get("CLINICAL_ASSESSMENT") == "clinical_hold"
    child_context = read_yaml(output / "triazolam" / "workflow" / "MANIFEST.yml")["fixture_context"]
    assert read_yaml(result.files["manifest"]).get("fixture_contexts") == {"triazolam": child_context}


def test_post_simulation_wrapper_preserves_child_context(tmp_path: Path) -> None:
    spec = ROOT / "drugs" / "triazolam" / "spec_pk1_oral.yml"
    simulation = tmp_path / "sim_full.csv"
    make_demo_sim_full(spec_yml=spec, out_csv=simulation, n_subjects_override=2)
    result = run_config(tmp_path, {
        "version": "0.1", "mode": "post_simulation", "out_dir": str(tmp_path / "post"),
        "inputs": {"sim_full_csv": str(simulation), "drug": "triazolam", "drugs_dir": str(ROOT / "drugs")},
        "sampling": {"times_h": [0, 0.5, 1, 2, 4, 8, 12, 24]},
        "validation": {"allow_failed": True},
    })
    child_context = read_yaml(result.files["workflow_manifest"])["fixture_context"]

    assert read_yaml(result.files["manifest"]).get("fixture_context") == child_context
    status = json.loads(result.files["status_json"].read_text(encoding="utf-8"))
    assert status.get("fixture_context") == child_context


def test_repeated_summary_and_wrapper_preserve_child_context(tmp_path: Path) -> None:
    config = read_yaml(ROOT / "harness_examples" / "demo_repeated_oral_trough_ss_50.yml")
    config["out_dir"] = str(tmp_path / "repeated")
    config["drugs_dir"] = str(ROOT / "drugs")
    config["simulation"]["n_subjects"] = 2
    result = run_config(tmp_path, config)
    child_context = read_yaml(result.files["demo_manifest"])["fixture_context"]

    assert read_yaml(result.files["manifest"]).get("fixture_context") == child_context
    status = json.loads(result.files["status_json"].read_text(encoding="utf-8"))
    assert status.get("fixture_context") == child_context
    row = read_csv(result.files["summary_csv"])[0]
    assert {key: row[key] for key in context_columns(child_context)} == context_columns(child_context)
    summary = result.files["summary_md"].read_text(encoding="utf-8")
    for value in ("clinical_hold", "not_approved", "computational_stress_test"):
        assert value in summary
