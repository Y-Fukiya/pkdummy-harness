from __future__ import annotations

import csv
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def has_ggplot2() -> bool:
    if shutil.which("Rscript") is None:
        return False
    completed = subprocess.run(
        ["Rscript", "-e", "quit(status = ifelse(requireNamespace('ggplot2', quietly=TRUE), 0, 1))"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.returncode == 0


def run_adnca(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["Rscript", "tools/make_adnca.R", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


@pytest.mark.skipif(not has_ggplot2(), reason="Rscript with ggplot2 is required")
def test_make_adnca_single_mode_creates_long_wide_and_plots(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis_inputs"
    fields = ["STUDYID", "USUBJID", "SUBJID", "PARAMCD", "AVAL", "AVALU", "TIME_H", "MDV", "BLQ", "DOSE_MG", "DOSE_UNIT", "ROUTE"]
    rows: list[dict[str, object]] = []
    for subject, values in [("S-001", [0, 10, 20, 10, 5]), ("S-002", [0, 8, 16, 8, 4])]:
        for time, conc in zip([0, 1, 2, 4, 6], values):
            rows.append(
                {
                    "STUDYID": "OSP_test",
                    "USUBJID": subject,
                    "SUBJID": subject[-3:],
                    "PARAMCD": "CONC",
                    "AVAL": conc,
                    "AVALU": "ng/mL",
                    "TIME_H": time,
                    "MDV": "0",
                    "BLQ": "0",
                    "DOSE_MG": 10,
                    "DOSE_UNIT": "mg",
                    "ROUTE": "ORAL",
                }
            )
    write_csv(analysis / "ADPC.csv", rows, fields)
    out_dir = tmp_path / "adnca"

    completed = run_adnca(["--analysis-dir", str(analysis), "--out-dir", str(out_dir), "--title", "Single ADNCA"])

    assert completed.returncode == 0, completed.stdout
    assert "ADNCA fixture written: OK" in completed.stdout
    adnca = read_csv(out_dir / "ADNCA.csv")
    assert {row["PARAMCD"] for row in adnca} >= {"AUC0TL", "CMAX", "TMAX", "AUC0INF", "HL_LAMZ"}
    assert {row["AVALU"] for row in adnca if row["PARAMCD"] in {"AUC0TL", "AUC0INF"}} == {"ng*h/mL"}
    assert {row["AVALU"] for row in adnca if row["PARAMCD"] == "CMAX"} == {"ng/mL"}
    assert {row["AVALU"] for row in adnca if row["PARAMCD"] == "AUCEXTRAP"} == {"%"}
    assert len({row["USUBJID"] for row in adnca}) == 2
    wide = read_csv(out_dir / "ADNCA_WIDE.csv")
    assert len(wide) == 2
    assert "CMAX" in wide[0]
    assert (out_dir / "concentration_profile_linear.png").exists()
    assert (out_dir / "concentration_profile_log.png").exists()
    assert (out_dir / "ADNCA_MANIFEST.yml").exists()

    gap_analysis = tmp_path / "gap_analysis"
    gap_rows = []
    for time, conc in zip([0, 1, 2, 3, 4, 5], [10, 0, 9, 8, 0, 7]):
        gap_rows.append(
            {
                "STUDYID": "OSP_gap",
                "USUBJID": "OSP_gap-001",
                "SUBJID": "001",
                "PARAMCD": "CONC",
                "AVAL": conc,
                "AVALU": "ng/mL",
                "TIME_H": time,
                "MDV": "0",
                "BLQ": "0",
                "DOSE_MG": 10,
                "DOSE_UNIT": "mg",
                "ROUTE": "ORAL",
            }
        )
    write_csv(gap_analysis / "ADPC.csv", gap_rows, fields)
    gap_out = tmp_path / "gap_out"
    gap_completed = run_adnca(["--analysis-dir", str(gap_analysis), "--out-dir", str(gap_out)])
    assert gap_completed.returncode == 0, gap_completed.stdout
    gap_adnca = read_csv(gap_out / "ADNCA.csv")
    assert next(row["AVAL"] for row in gap_adnca if row["PARAMCD"] == "HL_LAMZ") == ""

    rows[1]["AVAL"] = -1
    write_csv(analysis / "ADPC.csv", rows, fields)
    negative = run_adnca(["--analysis-dir", str(analysis), "--out-dir", str(tmp_path / "negative_adpc")])
    assert negative.returncode != 0
    assert "negative concentrations" in negative.stdout


@pytest.mark.skipif(not has_ggplot2(), reason="Rscript with ggplot2 is required")
def test_make_adnca_repeated_mode_uses_ss_and_trough_summaries(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis_inputs"
    adpc_fields = ["STUDYID", "USUBJID", "SUBJID", "PARAMCD", "AVAL", "AVALU", "TIME_H", "MDV", "BLQ", "DOSE_MG", "DOSE_UNIT", "ROUTE"]
    adpc_rows = []
    for subject in ["S-001", "S-002"]:
        for time, conc in [(0, 0), (1, 10), (2, 20), (4, 8)]:
            adpc_rows.append({"STUDYID": "OSP_repeat", "USUBJID": subject, "SUBJID": subject[-3:], "PARAMCD": "CONC", "AVAL": conc, "AVALU": "ng/mL", "TIME_H": time, "MDV": "0", "BLQ": "0", "DOSE_MG": 10, "DOSE_UNIT": "mg", "ROUTE": "ORAL"})
    write_csv(analysis / "ADPC.csv", adpc_rows, adpc_fields)

    ss_fields = ["STUDYID", "USUBJID", "AUC0_4_SS", "AUC4_12_SS", "AUCTAU_SS", "CMAX_SS", "TMAX_SS_H", "CPREDOSE_SS", "CTROUGH_SS", "CMIN_SS", "CAVG_SS", "FLUCT_PCT_SS", "N_POINTS", "AUC_UNIT"]
    ss_rows = []
    for subject in ["S-001", "S-002"]:
        ss_rows.append({"STUDYID": "OSP_repeat", "USUBJID": subject, "AUC0_4_SS": 30, "AUC4_12_SS": 15, "AUCTAU_SS": 45, "CMAX_SS": 20, "TMAX_SS_H": 1, "CPREDOSE_SS": 10, "CTROUGH_SS": 5, "CMIN_SS": 5, "CAVG_SS": 11.25, "FLUCT_PCT_SS": 133.3, "N_POINTS": 4, "AUC_UNIT": "ng*h/mL"})
    write_csv(analysis / "NCA_SS_SUMMARY.csv", ss_rows, ss_fields)
    write_csv(analysis / "TROUGH_SUMMARY.csv", [{"STUDYID": "OSP_repeat", "USUBJID": subject, "DV_TROUGH_0H": 0, "DV_TROUGH_24H": 5} for subject in ["S-001", "S-002"]], ["STUDYID", "USUBJID", "DV_TROUGH_0H", "DV_TROUGH_24H"])
    ss_input_fields = ["STUDYID", "USUBJID", "ABS_TIME_H", "TAD_H", "DV", "IPRED", "CONC_UNIT", "MDV", "SSNCAFL", "DOSESEQ_REF"]
    ss_input_rows = []
    for subject in ["S-001", "S-002"]:
        for tad, conc in [(0, 10), (1, 20), (2, 10), (4, 5)]:
            ss_input_rows.append({"STUDYID": "OSP_repeat", "USUBJID": subject, "ABS_TIME_H": 100 + tad, "TAD_H": tad, "DV": conc, "IPRED": conc, "CONC_UNIT": "ng/mL", "MDV": 0, "SSNCAFL": "Y", "DOSESEQ_REF": 3})
    write_csv(analysis / "NCA_SS_INPUT.csv", ss_input_rows, ss_input_fields)
    out_dir = tmp_path / "adnca"

    completed = run_adnca(["--analysis-dir", str(analysis), "--out-dir", str(out_dir)])

    assert completed.returncode == 0, completed.stdout
    adnca = read_csv(out_dir / "ADNCA.csv")
    assert len(adnca) == 24
    assert {row["PARAMCD"] for row in adnca} >= {"AUC0_4SS", "AUCTAUSS", "CMAXSS", "TRG0H", "TRG24H"}
    assert {row["SOURCE_MODE"] for row in adnca} == {"repeated"}
    assert {row["ANL01FL"] for row in adnca if row["PARAMCD"] == "TRG0H"} == {"N"}
    assert (out_dir / "steady_state_profile_linear.png").exists()
    assert (out_dir / "steady_state_profile_log.png").exists()

    unit_analysis = tmp_path / "unit_analysis"
    shutil.copytree(analysis, unit_analysis)
    unit_adpc = read_csv(unit_analysis / "ADPC.csv")
    for row in unit_adpc:
        row["AVALU"] = "mg/L"
    write_csv(unit_analysis / "ADPC.csv", unit_adpc, adpc_fields)
    unit_ss = read_csv(unit_analysis / "NCA_SS_SUMMARY.csv")
    for row in unit_ss:
        row["AUC_UNIT"] = "mg*h/L"
    write_csv(unit_analysis / "NCA_SS_SUMMARY.csv", unit_ss, ss_fields)
    unit_ss_input = read_csv(unit_analysis / "NCA_SS_INPUT.csv")
    for row in unit_ss_input:
        row["CONC_UNIT"] = "mg/L"
    write_csv(unit_analysis / "NCA_SS_INPUT.csv", unit_ss_input, ss_input_fields)
    unit_out = tmp_path / "unit_adnca"
    unit_completed = run_adnca(["--analysis-dir", str(unit_analysis), "--out-dir", str(unit_out)])
    assert unit_completed.returncode == 0, unit_completed.stdout
    unit_adnca = read_csv(unit_out / "ADNCA.csv")
    assert {row["AVALU"] for row in unit_adnca if row["PARAMCD"] in {"CMAXSS", "TRG24H"}} == {"mg/L"}

    ss_input_rows[0]["DV"] = -1
    write_csv(analysis / "NCA_SS_INPUT.csv", ss_input_rows, ss_input_fields)
    negative_plot = run_adnca(["--analysis-dir", str(analysis), "--out-dir", str(tmp_path / "negative_plot")])
    assert negative_plot.returncode != 0
    assert "negative plot values" in negative_plot.stdout
    ss_input_rows[0]["DV"] = 10
    write_csv(analysis / "NCA_SS_INPUT.csv", ss_input_rows, ss_input_fields)

    ss_rows[0]["CMAX_SS"] = ""
    write_csv(analysis / "NCA_SS_SUMMARY.csv", ss_rows, ss_fields)
    invalid = run_adnca(["--analysis-dir", str(analysis), "--out-dir", str(tmp_path / "invalid")])
    assert invalid.returncode != 0
    assert "missing/non-finite values in CMAX_SS" in invalid.stdout

    (analysis / "TROUGH_SUMMARY.csv").unlink()
    incomplete = run_adnca(["--analysis-dir", str(analysis), "--out-dir", str(tmp_path / "incomplete")])
    assert incomplete.returncode != 0
    assert "artifacts are incomplete" in incomplete.stdout
