from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import yaml

from tools.run_downstream_smoke import run_downstream_smoke

from tests.test_make_downstream_adapters import write_analysis_inputs


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_run_downstream_smoke_executes_adapter_nca_and_poppk_contract(tmp_path: Path) -> None:
    analysis_dir = write_analysis_inputs(tmp_path)
    out_dir = tmp_path / "downstream_smoke"

    result = run_downstream_smoke(analysis_dir=analysis_dir, out_dir=out_dir)

    assert result.status == "OK"
    assert result.counts["nca_subjects"] == 1
    assert result.counts["poppk_subjects"] == 1
    assert result.files["nca_summary_csv"].exists()
    assert result.files["nonmem_control_template"].exists()
    assert result.files["nlmixr2_model_template"].exists()

    nca = read_csv(result.files["nca_summary_csv"])
    assert nca[0]["USUBJID"] == "OSP_demo-001"
    assert nca[0]["CMAX"] == "50"
    assert nca[0]["TMAX_H"] == "1"
    assert nca[0]["AUCLAST"] == "25"

    manifest = yaml.safe_load((out_dir / "DOWNSTREAM_SMOKE_MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["purpose"] == "downstream_e2e_smoke_fixture"
    assert manifest["adapter_validation"]["status"] == "OK"
    assert "not a certified Phoenix, NONMEM, or nlmixr2 validation" in " ".join(manifest["limitations"])


def test_run_downstream_smoke_cli(tmp_path: Path) -> None:
    analysis_dir = write_analysis_inputs(tmp_path)
    out_dir = tmp_path / "downstream_smoke"

    completed = subprocess.run(
        [
            sys.executable,
            "tools/run_downstream_smoke.py",
            "--analysis-dir",
            str(analysis_dir),
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
    assert "Downstream smoke: OK" in completed.stdout
    assert (out_dir / "nca_smoke" / "NCA_SUMMARY.csv").exists()
