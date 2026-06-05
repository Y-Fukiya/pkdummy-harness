from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_simpop_subject_generator_is_optional_and_writes_runner_columns() -> None:
    script = ROOT / "tools" / "make_simpop_subjects.R"
    text = script.read_text(encoding="utf-8")

    assert 'requireNamespace("simPop", quietly = TRUE)' in text
    assert "simPop package is required only for this optional generator" in text
    assert 'c("ID", "ARM", "DOSE_MG", "WT", "AGE", "SEX", "HEIGHT_CM")' in text
    assert "Height is included for downstream VS/BMI/BSA fixture generation" in text
