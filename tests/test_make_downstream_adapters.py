from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import yaml

from tools.make_downstream_adapters import make_downstream_adapters


ROOT = Path(__file__).resolve().parents[1]


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_analysis_inputs(root: Path) -> Path:
    analysis_dir = root / "analysis_inputs"
    write_csv(
        analysis_dir / "ADPC.csv",
        [
            {
                "STUDYID": "OSP_demo",
                "USUBJID": "OSP_demo-001",
                "SUBJID": "001",
                "ARM": "A",
                "AGE": "40",
                "SEX": "M",
                "AVAL": "0",
                "AVALU": "ng/mL",
                "TIME_H": "0",
                "TPT": "Pre-dose",
                "TPTNUM": "1",
                "WT": "70",
                "BSA": "1.8",
                "CREAT_MG_DL": "0.9",
                "DOSE_MG": "100",
                "DOSE_UNIT": "mg",
                "ROUTE": "ORAL",
            },
            {
                "STUDYID": "OSP_demo",
                "USUBJID": "OSP_demo-001",
                "SUBJID": "001",
                "ARM": "A",
                "AGE": "40",
                "SEX": "M",
                "AVAL": "50",
                "AVALU": "ng/mL",
                "TIME_H": "1",
                "TPT": "1 h",
                "TPTNUM": "2",
                "WT": "70",
                "BSA": "1.8",
                "CREAT_MG_DL": "0.9",
                "DOSE_MG": "100",
                "DOSE_UNIT": "mg",
                "ROUTE": "ORAL",
            },
        ],
        [
            "STUDYID",
            "USUBJID",
            "SUBJID",
            "ARM",
            "AGE",
            "SEX",
            "AVAL",
            "AVALU",
            "TIME_H",
            "TPT",
            "TPTNUM",
            "WT",
            "BSA",
            "CREAT_MG_DL",
            "DOSE_MG",
            "DOSE_UNIT",
            "ROUTE",
        ],
    )
    write_csv(
        analysis_dir / "POPPK_INPUT.csv",
        [
            {
                "ID": "1",
                "USUBJID": "OSP_demo-001",
                "TIME": "0",
                "EVID": "1",
                "MDV": "1",
                "AMT": "100",
                "DV": "",
                "CMT": "1",
                "RATE": "0",
                "CENS": "0",
                "LIMIT": "",
                "DOSE_MG": "100",
                "ROUTE": "ORAL",
                "AGE": "40",
                "SEX": "M",
                "WT": "70",
                "BSA": "1.8",
                "CREAT_MG_DL": "0.9",
                "STUDYID": "OSP_demo",
                "ARM": "A",
            },
            {
                "ID": "1",
                "USUBJID": "OSP_demo-001",
                "TIME": "1",
                "EVID": "0",
                "MDV": "0",
                "AMT": "0",
                "DV": "50",
                "CMT": "2",
                "RATE": "0",
                "CENS": "1",
                "LIMIT": "10",
                "DOSE_MG": "100",
                "ROUTE": "ORAL",
                "AGE": "40",
                "SEX": "M",
                "WT": "70",
                "BSA": "1.8",
                "CREAT_MG_DL": "0.9",
                "STUDYID": "OSP_demo",
                "ARM": "A",
            },
        ],
        [
            "ID",
            "USUBJID",
            "TIME",
            "EVID",
            "MDV",
            "AMT",
            "DV",
            "CMT",
            "RATE",
            "CENS",
            "LIMIT",
            "DOSE_MG",
            "ROUTE",
            "AGE",
            "SEX",
            "WT",
            "BSA",
            "CREAT_MG_DL",
            "STUDYID",
            "ARM",
        ],
    )
    return analysis_dir


def test_make_downstream_adapters_creates_nca_and_poppk_tool_csvs(tmp_path: Path) -> None:
    analysis_dir = write_analysis_inputs(tmp_path)
    out_dir = tmp_path / "adapters"

    result = make_downstream_adapters(analysis_dir=analysis_dir, out_dir=out_dir)

    assert result.status == "OK"
    assert (out_dir / "nca_r.csv").exists()
    assert (out_dir / "nca_phoenix.csv").exists()
    assert (out_dir / "poppk_nonmem.csv").exists()
    assert (out_dir / "poppk_nlmixr2.csv").exists()
    assert (out_dir / "MANIFEST.yml").exists()

    r_nca = read_csv(out_dir / "nca_r.csv")
    assert r_nca[1]["ID"] == "OSP_demo-001"
    assert r_nca[1]["TIME"] == "1"
    assert r_nca[1]["CONC"] == "50"

    phoenix = read_csv(out_dir / "nca_phoenix.csv")
    assert phoenix[1]["Subject"] == "OSP_demo-001"
    assert phoenix[1]["Concentration"] == "50"

    nlmixr = read_csv(out_dir / "poppk_nlmixr2.csv")
    assert nlmixr[0]["evid"] == "1"
    assert nlmixr[1]["dv"] == "50"
    assert nlmixr[1]["cens"] == "1"
    assert nlmixr[1]["limit"] == "10"

    nonmem = read_csv(out_dir / "poppk_nonmem.csv")
    assert nonmem[1]["CENS"] == "1"
    assert nonmem[1]["LIMIT"] == "10"

    manifest = yaml.safe_load((out_dir / "MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["purpose"] == "downstream_tool_adapter_fixture"
    assert manifest["targets"] == ["r_nca", "phoenix_nca", "nonmem", "nlmixr2"]


def test_make_downstream_adapters_cli(tmp_path: Path) -> None:
    analysis_dir = write_analysis_inputs(tmp_path)
    out_dir = tmp_path / "adapters"

    completed = subprocess.run(
        [
            sys.executable,
            "tools/make_downstream_adapters.py",
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
    assert "Downstream adapters written: OK" in completed.stdout
    assert (out_dir / "poppk_nonmem.csv").exists()
