#!/usr/bin/env python3
"""Create lightweight ADPC/NCA/PopPK input fixtures from SDTM-like domains.

These outputs are smoke-test fixtures for downstream workflow development.
They are not submission-ready ADaM datasets and not model-specific NONMEM
datasets.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AnalysisInputResult:
    out_dir: Path
    status: str
    files: dict[str, Path]
    counts: dict[str, int]
    warnings: list[str]


ADPC_FIELDS = [
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
    "MDV",
    "BLQ",
    "LLOQ",
    "PCSTAT",
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

NCA_FIELDS = [
    "STUDYID",
    "USUBJID",
    "TIME_H",
    "CONC",
    "CONC_UNIT",
    "DOSE_MG",
    "DOSE_UNIT",
    "ROUTE",
    "TPT",
    "TPTNUM",
    "MDV",
    "BLQ",
    "LLOQ",
    "PCSTAT",
    "SUBJID",
    "ARM",
    "AGE",
    "SEX",
    "WT",
    "BSA",
    "CREAT_MG_DL",
]

POPPK_FIELDS = [
    "ID",
    "USUBJID",
    "TIME",
    "EVID",
    "MDV",
    "AMT",
    "DV",
    "CMT",
    "RATE",
    "BLQ",
    "CENS",
    "LLOQ",
    "LIMIT",
    "DOSE_MG",
    "ROUTE",
    "TPT",
    "TPTNUM",
    "AGE",
    "SEX",
    "WT",
    "BSA",
    "CREAT_MG_DL",
    "STUDYID",
    "ARM",
]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV is empty: {path}")
        return list(reader.fieldnames), list(reader)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row.get(field, "")) for field in fieldnames})


def _write_yaml(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)


def _to_float(value: object) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: float, digits: int = 12) -> str:
    if abs(value) < 1e-12:
        value = 0.0
    return f"{value:.{digits}g}"


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return _format_number(value)
    return str(value)


def _norm(value: object) -> str:
    return str(value or "").strip()


def _upper(value: object) -> str:
    return _norm(value).upper()


def _first_by_subject(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        usubjid = _norm(row.get("USUBJID"))
        if usubjid and usubjid not in out:
            out[usubjid] = row
    return out


def _pivot_vs(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    name_map = {
        "HEIGHT": "HEIGHT_CM",
        "WEIGHT": "WT",
        "BMI": "BMI",
        "BSA": "BSA",
    }
    for row in rows:
        usubjid = _norm(row.get("USUBJID"))
        testcd = _upper(row.get("VSTESTCD"))
        target = name_map.get(testcd)
        if not usubjid or not target:
            continue
        out.setdefault(usubjid, {})[target] = _norm(row.get("VSSTRESN"))
    return out


def _pivot_lb(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        if _upper(row.get("LBTESTCD")) != "CREAT":
            continue
        usubjid = _norm(row.get("USUBJID"))
        if usubjid:
            out.setdefault(usubjid, {})["CREAT_MG_DL"] = _norm(row.get("LBSTRESN"))
    return out


def _elapsed_hours(row: dict[str, str]) -> str:
    for key in ("TIME_H", "NOMTIME_H", "TIME", "time"):
        parsed = _to_float(row.get(key))
        if parsed is not None:
            return _format_number(parsed)
    text = _upper(row.get("PCELTM"))
    match = re.fullmatch(r"PT([0-9.+-]+)H", text)
    if match:
        parsed = _to_float(match.group(1))
        if parsed is not None:
            return _format_number(parsed)
    return ""


def _conc(row: dict[str, str]) -> str:
    for key in ("PCSTRESN", "PCORRES", "DV", "CP", "IPRED"):
        parsed = _to_float(row.get(key))
        if parsed is not None:
            return _format_number(parsed)
    return ""


def _poppk_rate(ex_row: dict[str, str], dose_mg: str, fallback_route: str) -> str:
    route = _upper(ex_row.get("EXROUTE") or fallback_route).replace("-", "").replace("_", "")
    if route not in {"IV", "INTRAVENOUS", "IVINFUSION"}:
        return "0"
    infusion_h = _to_float(ex_row.get("EXINFH"))
    if infusion_h is None or infusion_h <= 0:
        return "0"
    dose = _to_float(dose_mg)
    if dose is None or dose <= 0:
        return "0"
    return _format_number(dose / infusion_h)


def _pc_unit(row: dict[str, str]) -> str:
    return _norm(row.get("PCSTRESU") or row.get("PCORRESU") or "ng/mL")


def _pc_blq(row: dict[str, str]) -> str:
    if _upper(row.get("PCSTAT")) == "BLQ" or _upper(row.get("PCBLFL")) == "Y":
        return "1"
    conc = _to_float(row.get("PCSTRESN") or row.get("PCORRES"))
    lloq = _to_float(row.get("PCLLOQ"))
    if conc is not None and lloq is not None and conc < lloq:
        return "1"
    return "0"


def _pc_mdv(row: dict[str, str]) -> str:
    parsed = _to_float(row.get("PCMDV") or row.get("MDV"))
    if parsed is not None and int(parsed) == 1:
        return "1"
    return "0"


def _base_subject(
    usubjid: str,
    *,
    dm_by_subject: dict[str, dict[str, str]],
    vs_by_subject: dict[str, dict[str, str]],
    lb_by_subject: dict[str, dict[str, str]],
    ex_by_subject: dict[str, dict[str, str]],
) -> dict[str, str]:
    dm = dm_by_subject.get(usubjid, {})
    vs = vs_by_subject.get(usubjid, {})
    lb = lb_by_subject.get(usubjid, {})
    ex = ex_by_subject.get(usubjid, {})
    return {
        "STUDYID": _norm(dm.get("STUDYID") or ex.get("STUDYID")),
        "USUBJID": usubjid,
        "SUBJID": _norm(dm.get("SUBJID")),
        "ARM": _norm(dm.get("ARM") or ex.get("EXARM")),
        "ACTARM": _norm(dm.get("ACTARM") or ex.get("EXACTARM")),
        "AGE": _norm(dm.get("AGE")),
        "SEX": _norm(dm.get("SEX")),
        "WT": _norm(vs.get("WT")),
        "HEIGHT_CM": _norm(vs.get("HEIGHT_CM")),
        "BMI": _norm(vs.get("BMI")),
        "BSA": _norm(vs.get("BSA")),
        "CREAT_MG_DL": _norm(lb.get("CREAT_MG_DL")),
        "EXTRT": _norm(ex.get("EXTRT")),
        "DOSE_MG": _norm(ex.get("EXDOSE")),
        "DOSE_UNIT": _norm(ex.get("EXDOSU")),
        "ROUTE": _norm(ex.get("EXROUTE")),
    }


def _make_adpc(
    pc_rows: list[dict[str, str]],
    *,
    dm_by_subject: dict[str, dict[str, str]],
    vs_by_subject: dict[str, dict[str, str]],
    lb_by_subject: dict[str, dict[str, str]],
    ex_by_subject: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pc in pc_rows:
        usubjid = _norm(pc.get("USUBJID"))
        base = _base_subject(
            usubjid,
            dm_by_subject=dm_by_subject,
            vs_by_subject=vs_by_subject,
            lb_by_subject=lb_by_subject,
            ex_by_subject=ex_by_subject,
        )
        time_h = _elapsed_hours(pc)
        rows.append(
            {
                **base,
                "STUDYID": _norm(pc.get("STUDYID") or base["STUDYID"]),
                "PARAMCD": "CONC",
                "PARAM": "Drug Concentration",
                "AVAL": _conc(pc),
                "AVALU": _pc_unit(pc),
                "TIME_H": time_h,
                "NOMTIME_H": time_h,
                "TPT": _norm(pc.get("PCTPT")),
                "TPTNUM": _norm(pc.get("PCTPTNUM")),
                "ADTM": _norm(pc.get("PCDTC")),
                "MDV": _pc_mdv(pc),
                "BLQ": _pc_blq(pc),
                "LLOQ": _norm(pc.get("PCLLOQ")),
                "PCSTAT": _norm(pc.get("PCSTAT")),
                "PCSEQ": _norm(pc.get("PCSEQ")),
            }
        )
    return rows


def _make_nca(adpc_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "STUDYID": row["STUDYID"],
            "USUBJID": row["USUBJID"],
            "TIME_H": row["TIME_H"],
            "CONC": row["AVAL"],
            "CONC_UNIT": row["AVALU"],
            "DOSE_MG": row["DOSE_MG"],
            "DOSE_UNIT": row["DOSE_UNIT"],
            "ROUTE": row["ROUTE"],
            "TPT": row["TPT"],
            "TPTNUM": row["TPTNUM"],
            "MDV": row["MDV"],
            "BLQ": row["BLQ"],
            "LLOQ": row["LLOQ"],
            "PCSTAT": row["PCSTAT"],
            "SUBJID": row["SUBJID"],
            "ARM": row["ARM"],
            "AGE": row["AGE"],
            "SEX": row["SEX"],
            "WT": row["WT"],
            "BSA": row["BSA"],
            "CREAT_MG_DL": row["CREAT_MG_DL"],
        }
        for row in adpc_rows
    ]


def _make_poppk(
    adpc_rows: list[dict[str, Any]],
    *,
    ex_by_subject: dict[str, dict[str, str]],
    dose_cmt: str = "1",
    observation_cmt: str = "2",
) -> list[dict[str, Any]]:
    subject_order = {
        usubjid: idx
        for idx, usubjid in enumerate(sorted({str(row["USUBJID"]) for row in adpc_rows if row["USUBJID"]}), start=1)
    }
    rows: list[dict[str, Any]] = []
    for usubjid in sorted(subject_order, key=lambda key: subject_order[key]):
        subject_rows = [row for row in adpc_rows if row["USUBJID"] == usubjid]
        first = subject_rows[0]
        ex = ex_by_subject.get(usubjid, {})
        dose = _norm(ex.get("EXDOSE") or first["DOSE_MG"])
        route = _norm(ex.get("EXROUTE") or first["ROUTE"])
        rows.append(
            {
                "ID": subject_order[usubjid],
                "USUBJID": usubjid,
                "TIME": "0",
                "EVID": "1",
                "MDV": "1",
                "AMT": dose,
                "DV": "",
                "CMT": dose_cmt,
                "RATE": _poppk_rate(ex, dose, route),
                "BLQ": "0",
                "CENS": "0",
                "LLOQ": "",
                "LIMIT": "",
                "DOSE_MG": dose,
                "ROUTE": route,
                "TPT": "Dose",
                "TPTNUM": "0",
                "AGE": first["AGE"],
                "SEX": first["SEX"],
                "WT": first["WT"],
                "BSA": first["BSA"],
                "CREAT_MG_DL": first["CREAT_MG_DL"],
                "STUDYID": first["STUDYID"],
                "ARM": first["ARM"],
            }
        )
        for obs in sorted(subject_rows, key=lambda row: _to_float(row["TIME_H"]) or 0.0):
            has_dv = _norm(obs["AVAL"]) != ""
            is_blq = _norm(obs["BLQ"]) == "1"
            is_mdv = _norm(obs["MDV"]) == "1"
            rows.append(
                {
                    "ID": subject_order[usubjid],
                    "USUBJID": usubjid,
                    "TIME": obs["TIME_H"],
                    "EVID": "0",
                    "MDV": "0" if has_dv and not is_blq and not is_mdv else "1",
                    "AMT": "0",
                    "DV": obs["AVAL"],
                    "CMT": observation_cmt,
                    "RATE": "0",
                    "BLQ": obs["BLQ"],
                    "CENS": "1" if is_blq else "0",
                    "LLOQ": obs["LLOQ"],
                    "LIMIT": obs["LLOQ"],
                    "DOSE_MG": obs["DOSE_MG"],
                    "ROUTE": obs["ROUTE"],
                    "TPT": obs["TPT"],
                    "TPTNUM": obs["TPTNUM"],
                    "AGE": obs["AGE"],
                    "SEX": obs["SEX"],
                    "WT": obs["WT"],
                    "BSA": obs["BSA"],
                    "CREAT_MG_DL": obs["CREAT_MG_DL"],
                    "STUDYID": obs["STUDYID"],
                    "ARM": obs["ARM"],
                }
            )
    return rows


def _warnings(
    *,
    pc_rows: list[dict[str, str]],
    dm_by_subject: dict[str, dict[str, str]],
    ex_by_subject: dict[str, dict[str, str]],
    vs_by_subject: dict[str, dict[str, str]],
    lb_by_subject: dict[str, dict[str, str]],
) -> list[str]:
    warnings: list[str] = []
    pc_subjects = {_norm(row.get("USUBJID")) for row in pc_rows if _norm(row.get("USUBJID"))}
    missing_dm = sorted(pc_subjects - set(dm_by_subject))
    missing_ex = sorted(pc_subjects - set(ex_by_subject))
    missing_vs = sorted(subject for subject in pc_subjects if subject not in vs_by_subject)
    missing_lb = sorted(subject for subject in pc_subjects if subject not in lb_by_subject)
    missing_conc = sum(1 for row in pc_rows if _conc(row) == "")

    if missing_dm:
        warnings.append(f"PC subjects missing from DM: {missing_dm}")
    if missing_ex:
        warnings.append(f"PC subjects missing from EX: {missing_ex}")
    if missing_vs:
        warnings.append(f"VS covariates missing for PC subjects: {missing_vs}")
    if missing_lb:
        warnings.append(f"LB creatinine missing for PC subjects: {missing_lb}")
    if missing_conc:
        warnings.append(f"PC concentration missing for {missing_conc}/{len(pc_rows)} rows; PopPK MDV=1 for those rows.")
    return warnings


def make_analysis_inputs(
    *,
    sdtm_like_dir: Path | str,
    out_dir: Path | str,
    dose_cmt: str = "1",
    observation_cmt: str = "2",
) -> AnalysisInputResult:
    sdtm_path = Path(sdtm_like_dir)
    out_path = Path(out_dir)
    required = {
        "DM": sdtm_path / "DM.csv",
        "VS": sdtm_path / "VS.csv",
        "LB": sdtm_path / "LB.csv",
        "EX": sdtm_path / "EX.csv",
        "PC": sdtm_path / "PC.csv",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        raise ValueError(f"Missing SDTM-like domain CSVs: {missing}")

    _, dm_rows = _read_csv(required["DM"])
    _, vs_rows = _read_csv(required["VS"])
    _, lb_rows = _read_csv(required["LB"])
    _, ex_rows = _read_csv(required["EX"])
    _, pc_rows = _read_csv(required["PC"])
    if not pc_rows:
        raise ValueError("PC.csv has no concentration rows.")
    if all(_conc(row) == "" for row in pc_rows):
        raise ValueError("PC.csv has no usable concentration values.")

    dm_by_subject = _first_by_subject(dm_rows)
    ex_by_subject = _first_by_subject(ex_rows)
    vs_by_subject = _pivot_vs(vs_rows)
    lb_by_subject = _pivot_lb(lb_rows)

    warnings = _warnings(
        pc_rows=pc_rows,
        dm_by_subject=dm_by_subject,
        ex_by_subject=ex_by_subject,
        vs_by_subject=vs_by_subject,
        lb_by_subject=lb_by_subject,
    )
    adpc_rows = _make_adpc(
        pc_rows,
        dm_by_subject=dm_by_subject,
        vs_by_subject=vs_by_subject,
        lb_by_subject=lb_by_subject,
        ex_by_subject=ex_by_subject,
    )
    nca_rows = _make_nca(adpc_rows)
    poppk_rows = _make_poppk(
        adpc_rows,
        ex_by_subject=ex_by_subject,
        dose_cmt=str(dose_cmt),
        observation_cmt=str(observation_cmt),
    )

    files = {
        "ADPC": out_path / "ADPC.csv",
        "NCA_INPUT": out_path / "NCA_INPUT.csv",
        "POPPK_INPUT": out_path / "POPPK_INPUT.csv",
        "MANIFEST": out_path / "MANIFEST.yml",
    }
    counts = {
        "dm_subjects": len(dm_by_subject),
        "ex_subjects": len(ex_by_subject),
        "pc_rows": len(pc_rows),
        "adpc_rows": len(adpc_rows),
        "nca_rows": len(nca_rows),
        "poppk_rows": len(poppk_rows),
    }
    status = "WARN" if warnings else "OK"

    _write_csv(files["ADPC"], adpc_rows, ADPC_FIELDS)
    _write_csv(files["NCA_INPUT"], nca_rows, NCA_FIELDS)
    _write_csv(files["POPPK_INPUT"], poppk_rows, POPPK_FIELDS)
    _write_yaml(
        files["MANIFEST"],
        {
            "purpose": "analysis_input_smoke_test_fixture",
            "status": status,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "inputs": {name: str(path) for name, path in required.items()},
            "outputs": {name: str(path) for name, path in files.items()},
            "counts": counts,
            "settings": {
                "dose_cmt": str(dose_cmt),
                "observation_cmt": str(observation_cmt),
            },
            "warnings": warnings,
            "notes": [
                "ADPC.csv is ADPC-like and intended for workflow smoke tests, not submission-ready ADaM.",
                "NCA_INPUT.csv is a simple concentration-time table for NCA pipeline testing.",
                "POPPK_INPUT.csv is NONMEM-like input for parser/control-stream smoke tests, not a model-specific dataset.",
            ],
        },
    )
    return AnalysisInputResult(
        out_dir=out_path,
        status=status,
        files=files,
        counts=counts,
        warnings=warnings,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdtm-like-dir", required=True, type=Path, help="Directory containing DM/VS/LB/EX/PC CSVs")
    parser.add_argument("--out-dir", required=True, type=Path, help="Output directory for ADPC/NCA/PopPK fixture CSVs")
    parser.add_argument("--dose-cmt", default="1", help="CMT value for PopPK dosing rows")
    parser.add_argument("--observation-cmt", default="2", help="CMT value for PopPK observation rows")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = make_analysis_inputs(
            sdtm_like_dir=args.sdtm_like_dir,
            out_dir=args.out_dir,
            dose_cmt=args.dose_cmt,
            observation_cmt=args.observation_cmt,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Analysis input smoke fixtures written: {result.status}")
    print(f"Output directory: {result.out_dir}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for key in sorted(result.files):
        print(f"{key}: {result.files[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
