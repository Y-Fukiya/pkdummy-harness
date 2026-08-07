from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tools.make_repeated_nca import make_repeated_nca


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_make_repeated_nca_writes_trough_and_partial_auc_outputs(tmp_path: Path) -> None:
    clinical = tmp_path / "clinical_samples.csv"
    rows = []
    values = {
        0.0: 2.0,
        120.0: 9.6,
        144.0: 10.0,
        12.0: 10.0,
        13.0: 20.0,
        14.0: 10.0,
        16.0: 5.0,
    }
    trough_times = {0.0, 120.0, 144.0}
    ss_times = {12.0, 13.0, 14.0, 16.0}
    for time_h, concentration in values.items():
        rows.append(
            {
                "STUDYID": "OSP_test",
                "USUBJID": "OSP_test-001",
                "TIME_H": str(time_h),
                "DV": str(concentration),
                "IPRED": str(concentration),
                "DV_UNIT": "ng/mL",
                "MDV": "0",
                "TROUGHFL": "Y" if time_h in trough_times else "N",
                "SSNCAFL": "Y" if time_h in ss_times else "N",
                "TAD_H": str(time_h - 12.0) if time_h in ss_times else "",
                "DOSESEQ_REF": "3" if time_h in ss_times else "",
            }
        )
    write_csv(clinical, rows, list(rows[0]))

    result = make_repeated_nca(
        clinical_samples_csv=clinical,
        out_dir=tmp_path / "nca",
        analysis_dose_time_h=12.0,
        interval_h=4.0,
        trough_times_h=[0.0, 120.0, 144.0],
        ss_times_after_dose_h=[0.0, 1.0, 2.0, 4.0],
        partial_intervals_h=[(0.0, 2.0), (2.0, 4.0)],
    )

    assert result.status == "OK"
    assert result.counts == {
        "subjects": 1,
        "trough_rows": 3,
        "ss_nca_rows": 4,
        "trough_summary_rows": 1,
        "ss_nca_summary_rows": 1,
    }
    assert len(read_csv(result.files["TROUGH_INPUT"])) == 3
    assert len(read_csv(result.files["NCA_SS_INPUT"])) == 4
    summary = read_csv(result.files["NCA_SS_SUMMARY"])[0]
    assert summary["N_POINTS"] == "4"
    assert summary["AUC_UNIT"] == "ng*h/mL"
    assert float(summary["AUCTAU_SS"]) == float(summary["AUC0_2_SS"]) + float(summary["AUC2_4_SS"])
    assert float(summary["CMAX_SS"]) == 20.0
    assert float(summary["TMAX_SS_H"]) == 1.0
    assert float(summary["CPREDOSE_SS"]) == 10.0
    assert float(summary["CTROUGH_SS"]) == 5.0


def test_make_repeated_nca_rejects_gap_in_partial_intervals(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="contiguous"):
        make_repeated_nca(
            clinical_samples_csv=tmp_path / "not_read.csv",
            out_dir=tmp_path / "nca",
            analysis_dose_time_h=12.0,
            interval_h=12.0,
            trough_times_h=[0, 120, 144],
            ss_times_after_dose_h=[0, 12],
            partial_intervals_h=[(0, 4), (5, 12)],
        )


def test_make_repeated_nca_requires_stability_qc_trough_points(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="120 and 144"):
        make_repeated_nca(
            clinical_samples_csv=tmp_path / "not_read.csv",
            out_dir=tmp_path / "nca",
            analysis_dose_time_h=12.0,
            interval_h=12.0,
            trough_times_h=[0, 24, 48],
            ss_times_after_dose_h=[0, 12],
            partial_intervals_h=[(0, 12)],
        )
