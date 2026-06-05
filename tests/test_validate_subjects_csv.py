from __future__ import annotations

from pathlib import Path

from tools.validate_subjects_csv import validate_subject_rows, validate_subjects_csv


def test_validate_subject_rows_accepts_required_runner_columns() -> None:
    rows = [
        {"ID": "1", "ARM": "A", "DOSE_MG": "100", "WT": "70.1", "AGE": "44", "SEX": "M"},
        {"ID": "2", "ARM": "A", "DOSE_MG": "100", "WT": "62.3", "AGE": "51", "SEX": "F"},
    ]

    issues = validate_subject_rows(rows, expected_n=2, allowed_arms={"A"})

    assert issues == []


def test_validate_subject_rows_accepts_optional_height_cm() -> None:
    rows = [
        {"ID": "1", "ARM": "A", "DOSE_MG": "100", "WT": "70.1", "AGE": "44", "SEX": "M", "HEIGHT_CM": "175.2"}
    ]

    issues = validate_subject_rows(rows, expected_n=1, allowed_arms={"A"})

    assert issues == []


def test_validate_subject_rows_reports_invalid_optional_height_cm() -> None:
    rows = [
        {"ID": "1", "ARM": "A", "DOSE_MG": "100", "WT": "70.1", "AGE": "44", "SEX": "M", "HEIGHT_CM": "unknown"}
    ]

    issues = validate_subject_rows(rows)

    assert "row 2: HEIGHT_CM must be numeric" in issues


def test_validate_subject_rows_reports_missing_required_columns() -> None:
    rows = [{"ID": "1", "ARM": "A", "WT": "70.1", "AGE": "44", "SEX": "M"}]

    issues = validate_subject_rows(rows)

    assert issues == ["missing required subject columns: DOSE_MG"]


def test_validate_subjects_csv_reads_file_and_checks_expected_n(tmp_path: Path) -> None:
    csv_path = tmp_path / "subjects.csv"
    csv_path.write_text(
        "ID,ARM,DOSE_MG,WT,AGE,SEX\n"
        "1,A,100,70.1,44,M\n"
        "2,A,100,62.3,51,F\n",
        encoding="utf-8",
    )

    issues = validate_subjects_csv(csv_path, expected_n=3)

    assert issues == ["expected 3 subjects, found 2"]
