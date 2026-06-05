from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from tools.sample_clinical_timepoints import sample_clinical_timepoints


ROOT = Path(__file__).resolve().parents[1]


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_sample_clinical_timepoints_linearly_interpolates_each_subject(tmp_path: Path) -> None:
    sim_csv = tmp_path / "sim_full.csv"
    out_csv = tmp_path / "clinical.csv"
    write_csv(
        sim_csv,
        [
            {"ID": "1", "time": "0", "evid": "0", "CP": "0", "DV": "0", "ARM": "A"},
            {"ID": "1", "time": "1", "evid": "0", "CP": "10", "DV": "20", "ARM": "A"},
            {"ID": "1", "time": "2", "evid": "0", "CP": "20", "DV": "40", "ARM": "A"},
            {"ID": "2", "time": "0", "evid": "0", "CP": "100", "DV": "200", "ARM": "B"},
            {"ID": "2", "time": "1", "evid": "0", "CP": "110", "DV": "220", "ARM": "B"},
            {"ID": "2", "time": "2", "evid": "0", "CP": "120", "DV": "240", "ARM": "B"},
        ],
        ["ID", "time", "evid", "CP", "DV", "ARM"],
    )

    result = sample_clinical_timepoints(
        sim_csv,
        out_csv,
        times_h=[0.5, 1.5],
        method="linear",
    )

    rows = read_csv(out_csv)
    assert result.n_rows == 4
    assert result.n_subjects == 2
    assert rows[0]["ID"] == "1"
    assert rows[0]["time"] == "0.5"
    assert rows[0]["NOMTIME_H"] == "0.5"
    assert rows[0]["TIME_H"] == "0.5"
    assert rows[0]["TPT"] == "0.5 h"
    assert rows[0]["TPTNUM"] == "1"
    assert rows[0]["CP"] == "5"
    assert rows[0]["DV"] == "10"
    assert rows[1]["CP"] == "15"
    assert rows[2]["ID"] == "2"
    assert rows[2]["CP"] == "105"


def test_sample_clinical_timepoints_uses_observation_row_when_dose_and_obs_share_time(
    tmp_path: Path,
) -> None:
    sim_csv = tmp_path / "sim_full.csv"
    out_csv = tmp_path / "clinical.csv"
    write_csv(
        sim_csv,
        [
            {"ID": "1", "time": "0", "evid": "1", "CP": "999", "MDV": "1"},
            {"ID": "1", "time": "0", "evid": "0", "CP": "0", "MDV": "0"},
            {"ID": "1", "time": "1", "evid": "0", "CP": "10", "MDV": "0"},
        ],
        ["ID", "time", "evid", "CP", "MDV"],
    )

    sample_clinical_timepoints(sim_csv, out_csv, times_h=[0.0], method="exact")

    rows = read_csv(out_csv)
    assert len(rows) == 1
    assert rows[0]["CP"] == "0"
    assert rows[0]["evid"] == "0"
    assert rows[0]["MDV"] == "0"
    assert rows[0]["TPT"] == "Pre-dose"


def test_sample_clinical_timepoints_cli_reads_schedule_csv(tmp_path: Path) -> None:
    sim_csv = tmp_path / "sim_full.csv"
    schedule_csv = tmp_path / "schedule.csv"
    out_csv = tmp_path / "clinical.csv"
    write_csv(
        sim_csv,
        [
            {"ID": "1", "time": "0", "evid": "0", "CP": "0"},
            {"ID": "1", "time": "1", "evid": "0", "CP": "10"},
        ],
        ["ID", "time", "evid", "CP"],
    )
    write_csv(
        schedule_csv,
        [
            {"NOMTIME_H": "0.25", "TPT": "15 min", "TPTNUM": "1"},
            {"NOMTIME_H": "0.75", "TPT": "45 min", "TPTNUM": "2"},
        ],
        ["NOMTIME_H", "TPT", "TPTNUM"],
    )

    completed = subprocess.run(
        [
            sys.executable,
            "tools/sample_clinical_timepoints.py",
            str(sim_csv),
            "--schedule-csv",
            str(schedule_csv),
            "--out",
            str(out_csv),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Clinical sample CSV written" in completed.stdout
    rows = read_csv(out_csv)
    assert [row["TPT"] for row in rows] == ["15 min", "45 min"]
    assert [row["CP"] for row in rows] == ["2.5", "7.5"]
