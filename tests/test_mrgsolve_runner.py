from __future__ import annotations

import csv
import hashlib
import math
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


def has_mrgsolve() -> bool:
    if shutil.which("Rscript") is None:
        return False
    check = subprocess.run(
        ["Rscript", "-e", "quit(status = ifelse(requireNamespace('mrgsolve', quietly=TRUE) && requireNamespace('yaml', quietly=TRUE), 0, 1))"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return check.returncode == 0


def run_runner(spec: str, output: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["Rscript", "tools/mrgsolve_runner.R", "--spec", f"drugs/{spec}", "--out", str(output), *extra],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def run_runner_path(spec_path: Path, output: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["Rscript", "tools/mrgsolve_runner.R", "--spec", str(spec_path), "--out", str(output), *extra],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@pytest.mark.skipif(not has_mrgsolve(), reason="Rscript with mrgsolve and yaml is required")
def test_mrgsolve_runner_oral_is_reproducible_and_pop_pk_shaped(tmp_path: Path) -> None:
    first = tmp_path / "apixaban_1.csv"
    second = tmp_path / "apixaban_2.csv"
    first_run = run_runner("apixaban/spec_pk1_oral.yml", first, "--n-subjects", "2", "--t-end-h", "24", "--dt-h", "1", "--seed", "42")
    second_run = run_runner("apixaban/spec_pk1_oral.yml", second, "--n-subjects", "2", "--t-end-h", "24", "--dt-h", "1", "--seed", "42")

    assert first_run.returncode == 0, first_run.stdout
    assert second_run.returncode == 0, second_run.stdout
    assert hashlib.sha256(first.read_bytes()).hexdigest() == hashlib.sha256(second.read_bytes()).hexdigest()
    rows = read_csv(first)
    assert len(rows) == 2 * (25 + 1)
    assert rows[0]["EVID"] == "0"
    assert rows[1]["EVID"] == "1"
    assert rows[1]["AMT"] == "10"
    assert rows[0]["CMT"] == "2"
    assert rows[1]["CMT"] == "1"
    assert rows[0]["DV_UNIT"] == "ng/mL"
    assert float(rows[0]["CL_I"]) > 0
    assert float(rows[0]["V_I"]) > 0
    assert float(rows[0]["KA_I"]) > 0
    assert rows[1]["DOSE_UNIT"] == "mg"
    observations = [row for row in rows if row["EVID"] == "0"]
    assert len(observations) == 50
    assert all(float(row["CP"]) >= 0 for row in observations)
    assert all(float(row["DV"]) >= 0 for row in observations)
    manifest = yaml.safe_load(Path(f"{first}.manifest.yml").read_text(encoding="utf-8"))
    assert manifest["engine"] == "mrgsolve"
    assert manifest["route"] == "oral"
    assert manifest["counts"]["subjects"] == 2
    assert manifest["counts"]["output_rows"] == 52
    assert manifest["units"]["concentration"] == "ng/mL"


@pytest.mark.skipif(not has_mrgsolve(), reason="Rscript with mrgsolve and yaml is required")
def test_mrgsolve_runner_detects_iv_infusion_and_supports_repeated_doses(tmp_path: Path) -> None:
    output = tmp_path / "albuterol.csv"
    completed = run_runner("albuterol/spec_pk1_iv.yml", output, "--n-subjects", "2", "--t-end-h", "24", "--dt-h", "1", "--dose-count", "3", "--interval-h", "8", "--seed", "42")

    assert completed.returncode == 0, completed.stdout
    rows = read_csv(output)
    events = [row for row in rows if row["EVID"] == "1"]
    observations = [row for row in rows if row["EVID"] == "0"]
    assert len(events) == 6
    assert {row["RATE"] for row in events} == {"1"}
    assert {row["CMT"] for row in observations} == {"1"}
    manifest = yaml.safe_load(Path(f"{output}.manifest.yml").read_text(encoding="utf-8"))
    assert manifest["route"] == "iv_infusion"
    assert manifest["settings"]["dose_count"] == 3


@pytest.mark.skipif(not has_mrgsolve(), reason="Rscript with mrgsolve and yaml is required")
def test_mrgsolve_runner_oral_matches_closed_form_without_iiv_or_residual(tmp_path: Path) -> None:
    spec = yaml.safe_load((ROOT / "drugs/apixaban/spec_pk1_oral.yml").read_text(encoding="utf-8"))
    spec["iiv"]["eta"] = {"CL": 0, "V": 0, "KA": 0}
    spec["residual"] = {"type": "prop+add", "prop": 0, "add": 0}
    spec_path = tmp_path / "deterministic_oral.yml"
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    output = tmp_path / "deterministic_oral.csv"
    completed = run_runner_path(spec_path, output, "--n-subjects", "1", "--t-end-h", "1", "--dt-h", "0.5", "--no-residual")
    assert completed.returncode == 0, completed.stdout
    rows = read_csv(output)
    row = next(row for row in rows if row["EVID"] == "0" and row["time"] == "1")
    cl = float(spec["model"]["theta"]["CL"])
    v = float(spec["model"]["theta"]["V"])
    ka = float(spec["model"]["theta"]["KA"])
    dose = float(spec["regimen"]["arms"]["A"]["dose_mg"])
    ke = cl / v
    tau = 1.0 - float(spec["model"]["theta"]["ALAG1"])
    expected = dose * ka / (v * (ka - ke)) * (math.exp(-ke * tau) - math.exp(-ka * tau)) * 1000.0
    assert float(row["CP"]) == pytest.approx(expected, rel=1e-6)
    assert float(row["DV"]) == pytest.approx(expected, rel=1e-6)


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript is required")
def test_mrgsolve_runner_help_does_not_require_r_packages() -> None:
    completed = subprocess.run(
        ["Rscript", "tools/mrgsolve_runner.R", "--help"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    assert completed.returncode == 0
    assert "--spec" in completed.stdout
    assert "mrgsolve" in completed.stdout


@pytest.mark.skipif(not has_mrgsolve(), reason="Rscript with mrgsolve and yaml is required")
@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda spec: spec["regimen"].update(route="iv"), "intravenous"),
        (lambda spec: spec["model"]["theta"].update(F1=1.1), "between 0 and 1"),
        (lambda spec: spec["residual"].update(type="add"), "residual.type"),
        (lambda spec: spec["iiv"].update(corr=True), "diagonal IIV"),
        (lambda spec: spec["model"]["units"].update(mult=1), "inconsistent"),
        (lambda spec: spec["model"]["units"].update(conc="pmol/L"), "Unsupported model.units.conc"),
        (lambda spec: spec["regimen"]["units"].update(dose="mg/kg"), "absolute mg"),
    ],
)
def test_mrgsolve_runner_rejects_unsupported_or_inconsistent_spec_options(tmp_path: Path, mutation, message: str) -> None:
    spec = yaml.safe_load((ROOT / "drugs/apixaban/spec_pk1_oral.yml").read_text(encoding="utf-8"))
    mutation(spec)
    spec_path = tmp_path / "invalid.yml"
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    completed = run_runner_path(spec_path, tmp_path / "invalid.csv", "--n-subjects", "1")
    assert completed.returncode != 0
    assert message in completed.stdout
