from __future__ import annotations

import csv
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tools.run_repeated_oral_demo import run_repeated_oral_demo


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def has_mrgsolve() -> bool:
    if shutil.which("Rscript") is None:
        return False
    completed = subprocess.run(
        [
            "Rscript",
            "-e",
            "quit(status = ifelse(requireNamespace('mrgsolve', quietly=TRUE) && requireNamespace('yaml', quietly=TRUE), 0, 1))",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def test_run_repeated_oral_demo_creates_expected_workflow_shapes(tmp_path: Path) -> None:
    config = yaml.safe_load((ROOT / "harness_examples" / "demo_repeated_oral_trough_ss_50.yml").read_text(encoding="utf-8"))
    config["out_dir"] = str(tmp_path / "out")
    config["simulation"]["n_subjects"] = 2

    result = run_repeated_oral_demo(config=config, out_dir=tmp_path / "out", drugs_dir=ROOT / "drugs")

    assert result.status == "OK"
    assert result.counts["clinical_sample_rows"] == 2 * 15
    assert result.counts["dosing_event_rows"] == 2 * 13
    assert result.counts["trough_rows"] == 2 * 8
    assert result.counts["ss_nca_rows"] == 2 * 9
    assert result.counts["model_qc_rows"] == 2
    assert result.counts["poppk_rows"] == 2 * (13 + 15)

    root = tmp_path / "out" / "apixaban" / "workflow"
    clinical = read_csv(root / "raw" / "clinical_samples.csv")
    assert sum(row["TROUGHFL"] == "Y" for row in clinical) == 2 * 8
    assert sum(row["SSNCAFL"] == "Y" for row in clinical) == 2 * 9

    ex = read_csv(root / "sdtm_like" / "EX.csv")
    assert len(ex) == 26
    assert [row["EXSEQ"] for row in ex[:13]] == [str(i) for i in range(1, 14)]
    assert [float(row["EXTIME_H"]) for row in ex[:3]] == [0.0, 12.0, 24.0]

    pc = read_csv(root / "sdtm_like" / "PC.csv")
    for usubjid in {row["USUBJID"] for row in pc}:
        assert [row["PCSEQ"] for row in pc if row["USUBJID"] == usubjid] == [str(i) for i in range(1, 16)]

    poppk = read_csv(root / "analysis_inputs" / "POPPK_INPUT.csv")
    subject_rows = [row for row in poppk if row["USUBJID"] == "OSP_apixaban_repeat-001"]
    assert subject_rows[0]["TIME"] == "0"
    assert subject_rows[0]["EVID"] == "0"
    assert subject_rows[1]["TIME"] == "0"
    assert subject_rows[1]["EVID"] == "1"
    assert subject_rows[1]["ROW_ORDER"] == "2"

    model_qc = read_csv(root / "analysis_inputs" / "MODEL_QC.csv")
    assert len(model_qc) == 2
    assert {row["QC_STATUS"] for row in model_qc} == {"PASS"}

    manifest = yaml.safe_load((tmp_path / "out" / "DEMO_MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["counts"]["trough_rows"] == 16
    assert manifest["settings"]["dose_count"] == 13
    assert manifest["validation_status"] == "OK"
    workflow = tmp_path / "out" / "apixaban" / "workflow"
    assert (workflow / "MANIFEST.yml").exists()
    assert (workflow / "trace.log").exists()
    assert (workflow / "reports" / "simulation_validation.md").exists()
    workflow_manifest = yaml.safe_load((workflow / "MANIFEST.yml").read_text(encoding="utf-8"))
    assert workflow_manifest["validation_status"] == "OK"
    ss_input = read_csv(workflow / "analysis_inputs" / "NCA_SS_INPUT.csv")
    assert "TIME_H" in ss_input[0]
    assert all(float(row["TIME_H"]) == float(row["TAD_H"]) for row in ss_input)


def test_run_repeated_oral_demo_rejects_explicit_empty_sampling_list(tmp_path: Path) -> None:
    config = yaml.safe_load((ROOT / "harness_examples" / "demo_repeated_oral_trough_ss_50.yml").read_text(encoding="utf-8"))
    config["out_dir"] = str(tmp_path / "out")
    config["sampling"]["trough_times_h"] = []
    with pytest.raises(ValueError, match="trough_times_h must be a non-empty list"):
        run_repeated_oral_demo(config=config, out_dir=tmp_path / "out", drugs_dir=ROOT / "drugs")


@pytest.mark.skipif(not has_mrgsolve(), reason="Rscript with mrgsolve and yaml is required")
def test_run_repeated_oral_demo_mrgsolve_extracts_events_and_runs_nca(tmp_path: Path) -> None:
    config = yaml.safe_load((ROOT / "harness_examples" / "demo_repeated_oral_trough_ss_50.yml").read_text(encoding="utf-8"))
    config["out_dir"] = str(tmp_path / "out")
    config["simulation"]["engine"] = "mrgsolve"
    config["simulation"]["n_subjects"] = 2

    result = run_repeated_oral_demo(config=config, out_dir=tmp_path / "out", drugs_dir=ROOT / "drugs")

    assert result.status == "OK"
    assert result.counts["sim_full_rows"] == 2 * (313 + 13)
    assert result.counts["dosing_event_rows"] == 2 * 13
    assert result.counts["ex_rows"] == 2 * 13
    assert result.counts["pc_rows"] == 2 * 15
    assert result.counts["trough_rows"] == 2 * 8
    assert result.counts["ss_nca_rows"] == 2 * 9
    assert result.counts["model_qc_rows"] == 2

    sim = read_csv(result.files["sim_full"])
    assert sum(row["EVID"] == "1" for row in sim) == 26
    assert len({row["CL_I"] for row in sim if row["EVID"] == "0"}) == 2
    dosing = read_csv(result.files["dosing_events"])
    assert len(dosing) == 26
    assert [row["EXSEQ"] for row in dosing[:13]] == [str(i) for i in range(1, 14)]

    workflow_manifest = yaml.safe_load(
        (tmp_path / "out" / "apixaban" / "workflow" / "MANIFEST.yml").read_text(encoding="utf-8")
    )
    assert workflow_manifest["inputs"]["simulation_engine"] == "mrgsolve"
    assert result.files["mrgsolve_manifest"].exists()
