from __future__ import annotations

import csv
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


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


def has_ggplot2() -> bool:
    if shutil.which("Rscript") is None:
        return False
    completed = subprocess.run(
        ["Rscript", "-e", "quit(status = ifelse(requireNamespace('ggplot2', quietly = TRUE), 0, 1))"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.returncode == 0


@pytest.mark.skipif(not has_ggplot2(), reason="Rscript with ggplot2 is required")
def test_report_pk_fixture_creates_summaries_markdown_and_plots(tmp_path: Path) -> None:
    adpc = tmp_path / "analysis_inputs" / "ADPC.csv"
    fields = [
        "STUDYID",
        "USUBJID",
        "SUBJID",
        "ARM",
        "ACTARM",
        "AGE",
        "SEX",
        "PARAMCD",
        "PARAM",
        "AVAL",
        "AVALU",
        "TIME_H",
        "NOMTIME_H",
        "TPT",
        "TPTNUM",
        "ADTM",
        "WT",
        "HEIGHT_CM",
        "BMI",
        "BSA",
        "CREAT_MG_DL",
        "EXTRT",
        "DOSE_MG",
        "DOSE_UNIT",
        "ROUTE",
        "PCSEQ",
    ]
    write_csv(
        adpc,
        [
            {
                "STUDYID": "OSP_demo",
                "USUBJID": "OSP_demo-001",
                "SUBJID": "001",
                "ARM": "A",
                "ACTARM": "A",
                "AGE": "40",
                "SEX": "M",
                "PARAMCD": "CONC",
                "PARAM": "Drug concentration",
                "AVAL": "0",
                "AVALU": "ng/mL",
                "TIME_H": "0",
                "NOMTIME_H": "0",
                "TPT": "Pre-dose",
                "TPTNUM": "1",
                "ADTM": "2026-01-01T08:00:00",
                "WT": "70",
                "HEIGHT_CM": "175",
                "BMI": "22.9",
                "BSA": "1.85",
                "CREAT_MG_DL": "0.9",
                "EXTRT": "TEST",
                "DOSE_MG": "100",
                "DOSE_UNIT": "mg",
                "ROUTE": "ORAL",
                "PCSEQ": "1",
            },
            {
                "STUDYID": "OSP_demo",
                "USUBJID": "OSP_demo-001",
                "SUBJID": "001",
                "ARM": "A",
                "ACTARM": "A",
                "AGE": "40",
                "SEX": "M",
                "PARAMCD": "CONC",
                "PARAM": "Drug concentration",
                "AVAL": "50",
                "AVALU": "ng/mL",
                "TIME_H": "1",
                "NOMTIME_H": "1",
                "TPT": "1 h",
                "TPTNUM": "2",
                "ADTM": "2026-01-01T09:00:00",
                "WT": "70",
                "HEIGHT_CM": "175",
                "BMI": "22.9",
                "BSA": "1.85",
                "CREAT_MG_DL": "0.9",
                "EXTRT": "TEST",
                "DOSE_MG": "100",
                "DOSE_UNIT": "mg",
                "ROUTE": "ORAL",
                "PCSEQ": "2",
            },
            {
                "STUDYID": "OSP_demo",
                "USUBJID": "OSP_demo-002",
                "SUBJID": "002",
                "ARM": "A",
                "ACTARM": "A",
                "AGE": "50",
                "SEX": "F",
                "PARAMCD": "CONC",
                "PARAM": "Drug concentration",
                "AVAL": "0",
                "AVALU": "ng/mL",
                "TIME_H": "0",
                "NOMTIME_H": "0",
                "TPT": "Pre-dose",
                "TPTNUM": "1",
                "ADTM": "2026-01-01T08:00:00",
                "WT": "60",
                "HEIGHT_CM": "165",
                "BMI": "22.0",
                "BSA": "1.66",
                "CREAT_MG_DL": "0.8",
                "EXTRT": "TEST",
                "DOSE_MG": "100",
                "DOSE_UNIT": "mg",
                "ROUTE": "ORAL",
                "PCSEQ": "1",
            },
            {
                "STUDYID": "OSP_demo",
                "USUBJID": "OSP_demo-002",
                "SUBJID": "002",
                "ARM": "A",
                "ACTARM": "A",
                "AGE": "50",
                "SEX": "F",
                "PARAMCD": "CONC",
                "PARAM": "Drug concentration",
                "AVAL": "70",
                "AVALU": "ng/mL",
                "TIME_H": "1",
                "NOMTIME_H": "1",
                "TPT": "1 h",
                "TPTNUM": "2",
                "ADTM": "2026-01-01T09:00:00",
                "WT": "60",
                "HEIGHT_CM": "165",
                "BMI": "22.0",
                "BSA": "1.66",
                "CREAT_MG_DL": "0.8",
                "EXTRT": "TEST",
                "DOSE_MG": "100",
                "DOSE_UNIT": "mg",
                "ROUTE": "ORAL",
                "PCSEQ": "2",
            },
        ],
        fields,
    )
    out_dir = tmp_path / "report"

    completed = subprocess.run(
        [
            "Rscript",
            "tools/report_pk_fixture.R",
            "--adpc",
            str(adpc),
            "--out-dir",
            str(out_dir),
            "--title",
            "Demo PK Fixture Report",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "PK fixture report written: OK" in completed.stdout
    assert (out_dir / "REPORT.md").exists()
    assert (out_dir / "subject_numeric_summary.csv").exists()
    assert (out_dir / "subject_categorical_summary.csv").exists()
    assert (out_dir / "concentration_summary.csv").exists()
    assert (out_dir / "concentration_profile_linear.png").exists()
    assert (out_dir / "concentration_profile_log.png").exists()
    assert (out_dir / "REPORT_MANIFEST.yml").exists()

    manifest = yaml.safe_load((out_dir / "REPORT_MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["purpose"] == "pk_fixture_descriptive_report"
    assert manifest["status"] == "OK"
    assert manifest["counts"]["subjects"] == 2

    numeric_summary = read_csv(out_dir / "subject_numeric_summary.csv")
    assert {row["variable"] for row in numeric_summary} >= {"AGE", "WT", "BSA", "CREAT_MG_DL"}
    age_summary = next(row for row in numeric_summary if row["variable"] == "AGE")
    assert age_summary["n"] == "2"
    assert age_summary["mean"] == "45"

    concentration_summary = read_csv(out_dir / "concentration_summary.csv")
    one_hour = next(row for row in concentration_summary if row["TIME_H"] == "1")
    assert one_hour["n"] == "2"
    assert one_hour["mean"] == "60"

    report = (out_dir / "REPORT.md").read_text(encoding="utf-8")
    assert "Demo PK Fixture Report" in report
    assert "concentration_profile_linear.png" in report
    assert "concentration_profile_log.png" in report
