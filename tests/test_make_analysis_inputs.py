from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import yaml

from tools.make_analysis_inputs import make_analysis_inputs


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


def write_sdtm_like(tmp_path: Path) -> Path:
    sdtm = tmp_path / "sdtm_like"
    write_csv(
        sdtm / "DM.csv",
        [
            {
                "STUDYID": "OSP_test",
                "DOMAIN": "DM",
                "USUBJID": "OSP_test-001",
                "SUBJID": "1",
                "ARM": "A",
                "ACTARM": "A",
                "AGE": "40",
                "SEX": "M",
            }
        ],
        ["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "ARM", "ACTARM", "AGE", "SEX"],
    )
    write_csv(
        sdtm / "VS.csv",
        [
            {"STUDYID": "OSP_test", "DOMAIN": "VS", "USUBJID": "OSP_test-001", "VSTESTCD": "HEIGHT", "VSSTRESN": "180", "VSSTRESU": "cm"},
            {"STUDYID": "OSP_test", "DOMAIN": "VS", "USUBJID": "OSP_test-001", "VSTESTCD": "WEIGHT", "VSSTRESN": "70", "VSSTRESU": "kg"},
            {"STUDYID": "OSP_test", "DOMAIN": "VS", "USUBJID": "OSP_test-001", "VSTESTCD": "BMI", "VSSTRESN": "21.6", "VSSTRESU": "kg/m2"},
            {"STUDYID": "OSP_test", "DOMAIN": "VS", "USUBJID": "OSP_test-001", "VSTESTCD": "BSA", "VSSTRESN": "1.87", "VSSTRESU": "m2"},
        ],
        ["STUDYID", "DOMAIN", "USUBJID", "VSTESTCD", "VSSTRESN", "VSSTRESU"],
    )
    write_csv(
        sdtm / "LB.csv",
        [
            {"STUDYID": "OSP_test", "DOMAIN": "LB", "USUBJID": "OSP_test-001", "LBTESTCD": "CREAT", "LBSTRESN": "0.9", "LBSTRESU": "mg/dL"}
        ],
        ["STUDYID", "DOMAIN", "USUBJID", "LBTESTCD", "LBSTRESN", "LBSTRESU"],
    )
    write_csv(
        sdtm / "EX.csv",
        [
            {
                "STUDYID": "OSP_test",
                "DOMAIN": "EX",
                "USUBJID": "OSP_test-001",
                "EXSEQ": "1",
                "EXTRT": "TEST DRUG",
                "EXDOSE": "100",
                "EXDOSU": "mg",
                "EXROUTE": "ORAL",
                "EXSTDTC": "2026-01-01T08:00:00",
            }
        ],
        ["STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXDOSE", "EXDOSU", "EXROUTE", "EXSTDTC"],
    )
    write_csv(
        sdtm / "PC.csv",
        [
            {
                "STUDYID": "OSP_test",
                "DOMAIN": "PC",
                "USUBJID": "OSP_test-001",
                "PCSEQ": "1",
                "PCSTRESN": "0",
                "PCSTRESU": "ng/mL",
                "PCTPT": "Pre-dose",
                "PCTPTNUM": "1",
                "PCELTM": "PT0H",
            },
            {
                "STUDYID": "OSP_test",
                "DOMAIN": "PC",
                "USUBJID": "OSP_test-001",
                "PCSEQ": "2",
                "PCSTRESN": "50",
                "PCSTRESU": "ng/mL",
                "PCTPT": "1 h",
                "PCTPTNUM": "2",
                "PCELTM": "PT1H",
            },
        ],
        ["STUDYID", "DOMAIN", "USUBJID", "PCSEQ", "PCSTRESN", "PCSTRESU", "PCTPT", "PCTPTNUM", "PCELTM"],
    )
    return sdtm


def test_make_analysis_inputs_creates_adpc_nca_and_poppk_smoke_inputs(tmp_path: Path) -> None:
    sdtm = write_sdtm_like(tmp_path)
    out_dir = tmp_path / "analysis_inputs"

    result = make_analysis_inputs(sdtm_like_dir=sdtm, out_dir=out_dir)

    assert result.status == "OK"
    assert result.counts["adpc_rows"] == 2
    assert result.counts["nca_rows"] == 2
    assert result.counts["poppk_rows"] == 3
    assert result.warnings == []

    adpc = read_csv(out_dir / "ADPC.csv")
    assert adpc[1]["PARAMCD"] == "CONC"
    assert adpc[1]["AVAL"] == "50"
    assert adpc[1]["WT"] == "70"
    assert adpc[1]["CREAT_MG_DL"] == "0.9"

    nca = read_csv(out_dir / "NCA_INPUT.csv")
    assert nca[1]["TIME_H"] == "1"
    assert nca[1]["CONC"] == "50"
    assert nca[1]["DOSE_MG"] == "100"

    poppk = read_csv(out_dir / "POPPK_INPUT.csv")
    assert poppk[0]["EVID"] == "1"
    assert poppk[0]["AMT"] == "100"
    assert poppk[1]["EVID"] == "0"
    assert poppk[2]["DV"] == "50"

    manifest = yaml.safe_load((out_dir / "MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["purpose"] == "analysis_input_smoke_test_fixture"
    assert manifest["status"] == "OK"
    assert manifest["counts"] == result.counts


def test_make_analysis_inputs_allows_poppk_cmt_convention_override(tmp_path: Path) -> None:
    sdtm = write_sdtm_like(tmp_path)
    out_dir = tmp_path / "analysis_inputs"

    make_analysis_inputs(
        sdtm_like_dir=sdtm,
        out_dir=out_dir,
        dose_cmt="10",
        observation_cmt="20",
    )

    poppk = read_csv(out_dir / "POPPK_INPUT.csv")
    assert poppk[0]["CMT"] == "10"
    assert {row["CMT"] for row in poppk[1:]} == {"20"}


def test_make_analysis_inputs_sets_poppk_rate_for_iv_infusion(tmp_path: Path) -> None:
    sdtm = write_sdtm_like(tmp_path)
    ex_path = sdtm / "EX.csv"
    ex_rows = read_csv(ex_path)
    for row in ex_rows:
        row["EXROUTE"] = "INTRAVENOUS"
        row["EXINFH"] = "2"
    write_csv(
        ex_path,
        ex_rows,
        ["STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXDOSE", "EXDOSU", "EXROUTE", "EXINFH", "EXSTDTC"],
    )
    out_dir = tmp_path / "analysis_inputs"

    make_analysis_inputs(sdtm_like_dir=sdtm, out_dir=out_dir)

    poppk = read_csv(out_dir / "POPPK_INPUT.csv")
    assert poppk[0]["EVID"] == "1"
    assert poppk[0]["RATE"] == "50"
    assert {row["RATE"] for row in poppk[1:]} == {"0"}


def test_make_analysis_inputs_carries_blq_flags_to_poppk(tmp_path: Path) -> None:
    sdtm = write_sdtm_like(tmp_path)
    pc_path = sdtm / "PC.csv"
    pc_rows = read_csv(pc_path)
    pc_rows[0]["PCLLOQ"] = "10"
    pc_rows[0]["PCSTAT"] = "BLQ"
    pc_rows[0]["PCBLFL"] = "Y"
    write_csv(
        pc_path,
        pc_rows,
        ["STUDYID", "DOMAIN", "USUBJID", "PCSEQ", "PCSTRESN", "PCSTRESU", "PCTPT", "PCTPTNUM", "PCELTM", "PCLLOQ", "PCSTAT", "PCBLFL"],
    )
    out_dir = tmp_path / "analysis_inputs"

    make_analysis_inputs(sdtm_like_dir=sdtm, out_dir=out_dir)

    adpc = read_csv(out_dir / "ADPC.csv")
    assert adpc[0]["BLQ"] == "1"
    assert adpc[0]["LLOQ"] == "10"

    poppk = read_csv(out_dir / "POPPK_INPUT.csv")
    predose = poppk[1]
    assert predose["EVID"] == "0"
    assert predose["BLQ"] == "1"
    assert predose["LLOQ"] == "10"
    assert predose["MDV"] == "1"


def test_make_analysis_inputs_cli(tmp_path: Path) -> None:
    sdtm = write_sdtm_like(tmp_path)
    out_dir = tmp_path / "analysis_inputs"

    completed = subprocess.run(
        [
            sys.executable,
            "tools/make_analysis_inputs.py",
            "--sdtm-like-dir",
            str(sdtm),
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
    assert "Analysis input smoke fixtures written: OK" in completed.stdout
    assert (out_dir / "ADPC.csv").exists()
    assert (out_dir / "NCA_INPUT.csv").exists()
    assert (out_dir / "POPPK_INPUT.csv").exists()
