from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tools.make_sdtm_like_domains import make_sdtm_like_domains


ROOT = Path(__file__).resolve().parents[1]


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_spec(path: Path) -> None:
    path.write_text(
        yaml.safe_dump(
            {
                "study": {"id": "OSP_test_drug", "title": "Test Drug"},
                "regimen": {
                    "route": "oral",
                    "arms": {"A": {"n": 2, "dose_mg": 100.0}},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def write_clinical_samples(path: Path) -> None:
    write_csv(
        path,
        [
            {
                "ID": "1",
                "USUBJID": "OSP_test-001",
                "STUDYID": "OSP_test_drug",
                "ARM": "A",
                "WT": "70",
                "AGE": "40",
                "SEX_CHAR": "M",
                "DOSE_MG": "100",
                "DV": "0",
                "TIME_H": "0",
                "NOMTIME_H": "0",
                "TPT": "Pre-dose",
                "TPTNUM": "1",
            },
            {
                "ID": "1",
                "USUBJID": "OSP_test-001",
                "STUDYID": "OSP_test_drug",
                "ARM": "A",
                "WT": "70",
                "AGE": "40",
                "SEX_CHAR": "M",
                "DOSE_MG": "100",
                "DV": "123.4",
                "TIME_H": "1",
                "NOMTIME_H": "1",
                "TPT": "1 h",
                "TPTNUM": "2",
            },
            {
                "ID": "2",
                "USUBJID": "OSP_test-002",
                "STUDYID": "OSP_test_drug",
                "ARM": "A",
                "WT": "60",
                "AGE": "55",
                "SEX_CHAR": "F",
                "DOSE_MG": "100",
                "DV": "0",
                "TIME_H": "0",
                "NOMTIME_H": "0",
                "TPT": "Pre-dose",
                "TPTNUM": "1",
            },
            {
                "ID": "2",
                "USUBJID": "OSP_test-002",
                "STUDYID": "OSP_test_drug",
                "ARM": "A",
                "WT": "60",
                "AGE": "55",
                "SEX_CHAR": "F",
                "DOSE_MG": "100",
                "DV": "45.6",
                "TIME_H": "1",
                "NOMTIME_H": "1",
                "TPT": "1 h",
                "TPTNUM": "2",
            },
        ],
        [
            "ID",
            "USUBJID",
            "STUDYID",
            "ARM",
            "WT",
            "AGE",
            "SEX_CHAR",
            "DOSE_MG",
            "DV",
            "TIME_H",
            "NOMTIME_H",
            "TPT",
            "TPTNUM",
        ],
    )


def test_make_sdtm_like_domains_writes_limited_domains(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    spec = tmp_path / "spec.yml"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)

    result = make_sdtm_like_domains(
        clinical_samples_csv=samples,
        spec_yml=spec,
        out_dir=out_dir,
        study_start="2026-01-01T08:00:00",
        seed=11,
    )

    assert result.files["DM"].name == "DM.csv"
    assert result.counts == {"DM": 2, "VS": 8, "LB": 2, "EX": 2, "PC": 4}
    assert result.warnings == []

    dm = read_csv(out_dir / "DM.csv")
    assert dm[0]["DOMAIN"] == "DM"
    assert dm[0]["USUBJID"] == "OSP_test-001"
    assert dm[0]["AGE"] == "40"
    assert dm[0]["SEX"] == "M"

    vs = read_csv(out_dir / "VS.csv")
    first_subject_vs = [row for row in vs if row["USUBJID"] == "OSP_test-001"]
    assert [row["VSTESTCD"] for row in first_subject_vs] == ["HEIGHT", "WEIGHT", "BMI", "BSA"]
    assert float(first_subject_vs[0]["VSSTRESN"]) > 0
    assert first_subject_vs[3]["VSSTRESU"] == "m2"

    lb = read_csv(out_dir / "LB.csv")
    assert lb[0]["LBTESTCD"] == "CREAT"
    assert lb[0]["LBSTRESU"] == "mg/dL"
    assert 0.45 <= float(lb[0]["LBSTRESN"]) <= 1.8

    ex = read_csv(out_dir / "EX.csv")
    assert ex[0]["EXTRT"] == "TEST DRUG"
    assert ex[0]["EXDOSE"] == "100"
    assert ex[0]["EXROUTE"] == "ORAL"

    pc = read_csv(out_dir / "PC.csv")
    assert pc[1]["PCTESTCD"] == "DRUGCONC"
    assert pc[1]["PCSTRESN"] == "123.4"
    assert pc[1]["PCTPT"] == "1 h"

    manifest = yaml.safe_load((out_dir / "MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["purpose"] == "workflow_fixture_not_submission_ready_sdtm"
    assert manifest["counts"] == result.counts
    assert manifest["warnings"] == []


def test_make_sdtm_like_domains_preserves_input_concentration_unit(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    spec = tmp_path / "spec.yml"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)
    rows = read_csv(samples)
    for row in rows:
        row["DV_UNIT"] = "ug/mL"
    write_csv(samples, rows, list(rows[0]))

    make_sdtm_like_domains(
        clinical_samples_csv=samples,
        spec_yml=spec,
        out_dir=out_dir,
    )

    pc = read_csv(out_dir / "PC.csv")
    assert {row["PCSTRESU"] for row in pc} == {"ug/mL"}
    assert {row["PCORRESU"] for row in pc} == {"ug/mL"}


def test_make_sdtm_like_domains_allows_explicit_concentration_unit_override(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    spec = tmp_path / "spec.yml"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)

    make_sdtm_like_domains(
        clinical_samples_csv=samples,
        spec_yml=spec,
        out_dir=out_dir,
        pc_conc_unit="pmol/mL",
    )

    pc = read_csv(out_dir / "PC.csv")
    assert {row["PCSTRESU"] for row in pc} == {"pmol/mL"}


def test_make_sdtm_like_domains_marks_blq_when_spec_has_lloq(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    spec = tmp_path / "spec.yml"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)
    spec_data = yaml.safe_load(spec.read_text(encoding="utf-8"))
    spec_data["assay"] = {"lloq": {"value": 50, "unit": "ng/mL"}}
    spec.write_text(yaml.safe_dump(spec_data, sort_keys=False), encoding="utf-8")

    make_sdtm_like_domains(
        clinical_samples_csv=samples,
        spec_yml=spec,
        out_dir=out_dir,
    )

    pc = read_csv(out_dir / "PC.csv")
    predose = [row for row in pc if row["PCTPT"] == "Pre-dose"]
    assert {row["PCSTAT"] for row in predose} == {"BLQ"}
    assert {row["PCLLOQ"] for row in predose} == {"50"}
    assert {row["PCBLFL"] for row in predose} == {"Y"}


def test_make_sdtm_like_domains_uses_subject_height_when_available(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    subjects = tmp_path / "subjects.csv"
    spec = tmp_path / "spec.yml"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)
    write_csv(
        subjects,
        [
            {"ID": "1", "ARM": "A", "DOSE_MG": "100", "WT": "70", "AGE": "40", "SEX": "M", "HEIGHT_CM": "180"},
            {"ID": "2", "ARM": "A", "DOSE_MG": "100", "WT": "60", "AGE": "55", "SEX": "F", "HEIGHT_CM": "160"},
        ],
        ["ID", "ARM", "DOSE_MG", "WT", "AGE", "SEX", "HEIGHT_CM"],
    )

    make_sdtm_like_domains(
        clinical_samples_csv=samples,
        spec_yml=spec,
        out_dir=out_dir,
        subjects_csv=subjects,
    )

    vs = read_csv(out_dir / "VS.csv")
    heights = [row for row in vs if row["VSTESTCD"] == "HEIGHT"]
    assert [row["VSSTRESN"] for row in heights] == ["180", "160"]


def test_make_sdtm_like_domains_reuses_existing_domains_and_fills_pc_concentrations(
    tmp_path: Path,
) -> None:
    samples = tmp_path / "clinical_samples.csv"
    spec = tmp_path / "spec.yml"
    out_dir = tmp_path / "sdtm"
    dm_csv = tmp_path / "DM_existing.csv"
    vs_csv = tmp_path / "VS_existing.csv"
    lb_csv = tmp_path / "LB_existing.csv"
    pc_csv = tmp_path / "PC_skeleton.csv"
    write_clinical_samples(samples)
    write_spec(spec)
    write_csv(
        dm_csv,
        [
            {"STUDYID": "OSP_test_drug", "DOMAIN": "DM", "USUBJID": "OSP_test-001", "CUSTOMDM": "keep"},
            {"STUDYID": "OSP_test_drug", "DOMAIN": "DM", "USUBJID": "OSP_test-002", "CUSTOMDM": "keep"},
        ],
        ["STUDYID", "DOMAIN", "USUBJID", "CUSTOMDM"],
    )
    write_csv(
        vs_csv,
        [
            {"STUDYID": "OSP_test_drug", "DOMAIN": "VS", "USUBJID": "OSP_test-001", "VSTESTCD": "WEIGHT", "VSSTRESN": "70"},
        ],
        ["STUDYID", "DOMAIN", "USUBJID", "VSTESTCD", "VSSTRESN"],
    )
    write_csv(
        lb_csv,
        [
            {"STUDYID": "OSP_test_drug", "DOMAIN": "LB", "USUBJID": "OSP_test-001", "LBTESTCD": "CREAT", "LBSTRESN": "0.9"},
        ],
        ["STUDYID", "DOMAIN", "USUBJID", "LBTESTCD", "LBSTRESN"],
    )
    write_csv(
        pc_csv,
        [
            {
                "STUDYID": "OSP_test_drug",
                "DOMAIN": "PC",
                "USUBJID": "OSP_test-001",
                "PCSEQ": "1",
                "PCTPTNUM": "1",
                "PCTPT": "Pre-dose",
                "PCSTRESN": "",
                "PCORRES": "",
            },
            {
                "STUDYID": "OSP_test_drug",
                "DOMAIN": "PC",
                "USUBJID": "OSP_test-001",
                "PCSEQ": "2",
                "PCTPTNUM": "2",
                "PCTPT": "1 h",
                "PCSTRESN": "",
                "PCORRES": "",
            },
            {
                "STUDYID": "OSP_test_drug",
                "DOMAIN": "PC",
                "USUBJID": "OSP_test-002",
                "PCSEQ": "3",
                "PCTPTNUM": "2",
                "PCTPT": "1 h",
                "PCSTRESN": "",
                "PCORRES": "",
            },
        ],
        ["STUDYID", "DOMAIN", "USUBJID", "PCSEQ", "PCTPTNUM", "PCTPT", "PCSTRESN", "PCORRES"],
    )

    result = make_sdtm_like_domains(
        clinical_samples_csv=samples,
        spec_yml=spec,
        out_dir=out_dir,
        dm_csv=dm_csv,
        vs_csv=vs_csv,
        lb_csv=lb_csv,
        pc_csv=pc_csv,
    )

    assert result.counts["DM"] == 2
    assert result.counts["VS"] == 1
    assert result.counts["LB"] == 1
    assert result.counts["PC"] == 3
    assert result.warnings == []
    dm = read_csv(out_dir / "DM.csv")
    assert dm[0]["CUSTOMDM"] == "keep"
    pc = read_csv(out_dir / "PC.csv")
    assert pc[0]["PCSTRESN"] == "0"
    assert pc[1]["PCSTRESN"] == "123.4"
    assert pc[2]["PCORRES"] == "45.6"
    assert pc[2]["PCSTRESU"] == "ng/mL"
    manifest = yaml.safe_load((out_dir / "MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["domain_sources"]["DM"] == "existing_csv"
    assert manifest["domain_sources"]["PC"] == "existing_pc_skeleton_filled"


def test_make_sdtm_like_domains_errors_when_existing_pc_has_no_matching_samples(
    tmp_path: Path,
) -> None:
    samples = tmp_path / "clinical_samples.csv"
    spec = tmp_path / "spec.yml"
    pc_csv = tmp_path / "PC_skeleton.csv"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)
    write_csv(
        pc_csv,
        [
            {
                "STUDYID": "OSP_test_drug",
                "DOMAIN": "PC",
                "USUBJID": "OSP_test-999",
                "PCTPTNUM": "1",
                "PCSTRESN": "",
            }
        ],
        ["STUDYID", "DOMAIN", "USUBJID", "PCTPTNUM", "PCSTRESN"],
    )

    with pytest.raises(ValueError, match="Existing PC skeleton could not be matched"):
        make_sdtm_like_domains(
            clinical_samples_csv=samples,
            spec_yml=spec,
            out_dir=out_dir,
            pc_csv=pc_csv,
        )


def test_make_sdtm_like_domains_rejects_existing_dm_without_usubjid(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    spec = tmp_path / "spec.yml"
    dm_csv = tmp_path / "DM_existing.csv"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)
    write_csv(
        dm_csv,
        [{"STUDYID": "OSP_test_drug", "DOMAIN": "DM", "SUBJID": "1"}],
        ["STUDYID", "DOMAIN", "SUBJID"],
    )

    with pytest.raises(ValueError, match="Existing DM CSV is missing required columns: USUBJID"):
        make_sdtm_like_domains(
            clinical_samples_csv=samples,
            spec_yml=spec,
            out_dir=out_dir,
            dm_csv=dm_csv,
        )


def test_make_sdtm_like_domains_rejects_pc_skeleton_without_time_match_columns(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    spec = tmp_path / "spec.yml"
    pc_csv = tmp_path / "PC_skeleton.csv"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)
    write_csv(
        pc_csv,
        [{"STUDYID": "OSP_test_drug", "DOMAIN": "PC", "USUBJID": "OSP_test-001", "PCSTRESN": ""}],
        ["STUDYID", "DOMAIN", "USUBJID", "PCSTRESN"],
    )

    with pytest.raises(ValueError, match="Existing PC CSV needs at least one matching column"):
        make_sdtm_like_domains(
            clinical_samples_csv=samples,
            spec_yml=spec,
            out_dir=out_dir,
            pc_csv=pc_csv,
        )


def test_make_sdtm_like_domains_warns_on_subject_mismatch(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    subjects = tmp_path / "subjects.csv"
    spec = tmp_path / "spec.yml"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)
    write_csv(
        subjects,
        [
            {"ID": "1", "ARM": "A", "DOSE_MG": "100", "WT": "70", "AGE": "40", "SEX": "M"},
            {"ID": "3", "ARM": "A", "DOSE_MG": "100", "WT": "60", "AGE": "55", "SEX": "F"},
        ],
        ["ID", "ARM", "DOSE_MG", "WT", "AGE", "SEX"],
    )

    result = make_sdtm_like_domains(
        clinical_samples_csv=samples,
        spec_yml=spec,
        out_dir=out_dir,
        subjects_csv=subjects,
    )

    assert len(result.warnings) == 1
    assert "subject ID mismatch" in result.warnings[0]
    assert "subjects_without_pc=['3']" in result.warnings[0]
    assert "pc_without_subjects=['2']" in result.warnings[0]


def test_make_sdtm_like_domains_can_fail_on_subject_mismatch(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    subjects = tmp_path / "subjects.csv"
    spec = tmp_path / "spec.yml"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)
    write_csv(
        subjects,
        [{"ID": "1", "ARM": "A", "DOSE_MG": "100", "WT": "70", "AGE": "40", "SEX": "M"}],
        ["ID", "ARM", "DOSE_MG", "WT", "AGE", "SEX"],
    )

    with pytest.raises(ValueError, match="subject ID mismatch"):
        make_sdtm_like_domains(
            clinical_samples_csv=samples,
            spec_yml=spec,
            out_dir=out_dir,
            subjects_csv=subjects,
            strict_subject_match=True,
        )


def test_make_sdtm_like_domains_warns_on_partial_pc_concentration_missing(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    spec = tmp_path / "spec.yml"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)
    rows = read_csv(samples)
    rows[1]["DV"] = ""
    write_csv(samples, rows, list(rows[0].keys()))

    result = make_sdtm_like_domains(
        clinical_samples_csv=samples,
        spec_yml=spec,
        out_dir=out_dir,
    )

    assert result.warnings == [
        "PC concentration missing for 1/4 rows; PCORRES/PCSTRESN are blank for those rows."
    ]
    pc = read_csv(out_dir / "PC.csv")
    assert pc[1]["PCSTRESN"] == ""


def test_make_sdtm_like_domains_fails_when_all_pc_concentrations_missing(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    spec = tmp_path / "spec.yml"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)
    rows = read_csv(samples)
    for row in rows:
        row["DV"] = ""
    write_csv(samples, rows, list(rows[0].keys()))

    with pytest.raises(ValueError, match="No usable PC concentration values"):
        make_sdtm_like_domains(
            clinical_samples_csv=samples,
            spec_yml=spec,
            out_dir=out_dir,
        )


def test_make_sdtm_like_domains_cli(tmp_path: Path) -> None:
    samples = tmp_path / "clinical_samples.csv"
    spec = tmp_path / "spec.yml"
    out_dir = tmp_path / "sdtm"
    write_clinical_samples(samples)
    write_spec(spec)

    completed = subprocess.run(
        [
            sys.executable,
            "tools/make_sdtm_like_domains.py",
            "--clinical-samples",
            str(samples),
            "--spec",
            str(spec),
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
    assert "SDTM-like domains written" in completed.stdout
    assert (out_dir / "DM.csv").exists()
    assert (out_dir / "VS.csv").exists()
    assert (out_dir / "LB.csv").exists()
    assert (out_dir / "EX.csv").exists()
    assert (out_dir / "PC.csv").exists()
    assert (out_dir / "MANIFEST.yml").exists()
