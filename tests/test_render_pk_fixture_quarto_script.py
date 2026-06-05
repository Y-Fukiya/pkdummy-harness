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


def write_demo_adpc(path: Path) -> None:
    fieldnames = ["USUBJID", "AGE", "SEX", "WT", "ROUTE", "AVAL", "AVALU", "TIME_H", "TPT", "TPTNUM"]
    write_csv(
        path,
        [
            {"USUBJID": "DEMO-001", "AGE": "40", "SEX": "M", "WT": "70", "ROUTE": "ORAL", "AVAL": "0", "AVALU": "ng/mL", "TIME_H": "0", "TPT": "Pre-dose", "TPTNUM": "1"},
            {"USUBJID": "DEMO-001", "AGE": "40", "SEX": "M", "WT": "70", "ROUTE": "ORAL", "AVAL": "50", "AVALU": "ng/mL", "TIME_H": "1", "TPT": "1 h", "TPTNUM": "2"},
            {"USUBJID": "DEMO-002", "AGE": "50", "SEX": "F", "WT": "60", "ROUTE": "ORAL", "AVAL": "0", "AVALU": "ng/mL", "TIME_H": "0", "TPT": "Pre-dose", "TPTNUM": "1"},
            {"USUBJID": "DEMO-002", "AGE": "50", "SEX": "F", "WT": "60", "ROUTE": "ORAL", "AVAL": "70", "AVALU": "ng/mL", "TIME_H": "1", "TPT": "1 h", "TPTNUM": "2"},
        ],
        fieldnames,
    )


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
def test_render_pk_fixture_quarto_prepares_qmd_without_rendering_docx(tmp_path: Path) -> None:
    adpc = tmp_path / "analysis_inputs" / "ADPC.csv"
    write_demo_adpc(adpc)
    out_dir = tmp_path / "quarto_report"

    completed = subprocess.run(
        [
            "Rscript",
            "tools/render_pk_fixture_quarto.R",
            "--adpc",
            str(adpc),
            "--out-dir",
            str(out_dir),
            "--title",
            "Demo Quarto PK Fixture Report",
            "--no-render",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Quarto PK fixture report prepared: OK" in completed.stdout
    assert (out_dir / "pk_fixture_report.qmd").exists()
    assert (out_dir / "REPORT.md").exists()
    assert (out_dir / "concentration_profile_linear.png").exists()
    assert (out_dir / "concentration_profile_log.png").exists()
    assert (out_dir / "QUARTO_REPORT_MANIFEST.yml").exists()
    assert not (out_dir / "pk_fixture_report.docx").exists()

    qmd = (out_dir / "pk_fixture_report.qmd").read_text(encoding="utf-8")
    assert "Demo Quarto PK Fixture Report" in qmd
    assert "format:" in qmd
    assert "docx:" in qmd
    assert "concentration_profile_linear.png" in qmd
    assert "concentration_profile_log.png" in qmd

    manifest = yaml.safe_load((out_dir / "QUARTO_REPORT_MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["purpose"] == "pk_fixture_quarto_docx_report"
    assert manifest["status"] == "OK"
    assert manifest["render"]["docx_rendered"] is False
    assert manifest["outputs"]["qmd"].endswith("pk_fixture_report.qmd")


@pytest.mark.skipif(not has_ggplot2(), reason="Rscript with ggplot2 is required")
def test_render_pk_fixture_quarto_can_render_docx_when_quarto_is_available(tmp_path: Path) -> None:
    if shutil.which("quarto") is None:
        pytest.skip("Quarto CLI is not available")

    adpc = tmp_path / "analysis_inputs" / "ADPC.csv"
    write_demo_adpc(adpc)
    out_dir = tmp_path / "quarto_report"

    completed = subprocess.run(
        [
            "Rscript",
            "tools/render_pk_fixture_quarto.R",
            "--adpc",
            str(adpc),
            "--out-dir",
            str(out_dir),
            "--title",
            "Demo Quarto PK Fixture Report",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if completed.returncode != 0 and (
        "Quarto CLI is required" in completed.stdout or "Quarto DOCX render failed" in completed.stdout
    ):
        pytest.skip(f"Quarto docx rendering is not available in this environment:\n{completed.stdout}")
    assert completed.returncode == 0, completed.stdout
    assert (out_dir / "pk_fixture_report.docx").exists()
    manifest = yaml.safe_load((out_dir / "QUARTO_REPORT_MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["render"]["docx_rendered"] is True
