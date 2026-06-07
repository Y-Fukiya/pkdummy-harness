#!/usr/bin/env python3
"""Create limited SDTM-like dummy domains for PK workflow testing.

The generated CSVs are workflow fixtures, not submission-ready SDTM datasets.
Scope is intentionally limited:
- DM: one row per subject
- VS: HEIGHT, WEIGHT, BMI, BSA
- LB: creatinine only
- EX: one dosing record per subject from the simulation spec/subjects
- PC: concentration records from clinical_samples.csv
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SdtmLikeResult:
    out_dir: Path
    files: dict[str, Path]
    counts: dict[str, int]
    warnings: list[str]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV is empty: {path}")
        return list(reader.fieldnames), list(reader)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row.get(field, "")) for field in fieldnames})


def _ensure_fields(fieldnames: list[str], extra_fields: list[str]) -> list[str]:
    return list(fieldnames) + [field for field in extra_fields if field not in fieldnames]


def _require_columns(*, domain: str, fieldnames: list[str], required: list[str]) -> None:
    present = set(fieldnames)
    missing = [field for field in required if field not in present]
    if missing:
        raise ValueError(f"Existing {domain} CSV is missing required columns: {', '.join(missing)}")


def _validate_existing_domain_csv(*, domain: str, fieldnames: list[str]) -> None:
    required_by_domain = {
        "DM": ["USUBJID"],
        "VS": ["USUBJID", "VSTESTCD", "VSSTRESN"],
        "LB": ["USUBJID", "LBTESTCD", "LBSTRESN"],
        "EX": ["USUBJID", "EXTRT", "EXDOSE", "EXROUTE"],
        "PC": ["USUBJID"],
    }
    _require_columns(domain=domain, fieldnames=fieldnames, required=required_by_domain[domain])
    if domain == "PC":
        match_columns = {"PCTPTNUM", "TPTNUM", "PCTPT", "TPT", "PCELTM", "TIME_H", "TIME", "time"}
        if not match_columns.intersection(fieldnames):
            raise ValueError(
                "Existing PC CSV needs at least one matching column: "
                "PCTPTNUM, PCTPT, PCELTM, TIME_H, TIME, or time"
            )


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


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


def _to_int_string(value: object) -> str:
    parsed = _to_float(value)
    if parsed is None:
        return ""
    return str(int(round(parsed)))


def _subject_key(study_id: str, subject_id: object, fallback: int = 1) -> str:
    raw = str(subject_id or "").strip()
    parsed = _to_float(raw)
    if parsed is not None:
        return f"{study_id}-{int(round(parsed)):03d}"
    cleaned = "".join(ch for ch in raw.upper() if ch.isalnum())
    suffix = cleaned or f"{fallback:03d}"
    return f"{study_id}-{suffix}"


def _subject_match_key(row: dict[str, Any]) -> str:
    return str(row.get("ID") or row.get("SUBJID") or row.get("USUBJID") or "").strip()


def _format_number(value: float, digits: int = 6) -> str:
    if abs(value) < 1e-12:
        value = 0.0
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def _format_value(value: object) -> str:
    if isinstance(value, float):
        return _format_number(value)
    if value is None:
        return ""
    return str(value)


def _is_blank(value: object) -> bool:
    return value is None or str(value).strip() == ""


def _norm_text(value: object) -> str:
    return str(value or "").strip().upper()


def _norm_num(value: object) -> str:
    parsed = _to_float(value)
    if parsed is None:
        return ""
    return _format_number(parsed)


def _pceltm_hours(value: object) -> float | None:
    text = str(value or "").strip().upper()
    if not text.startswith("PT") or not text.endswith("H"):
        return None
    return _to_float(text[2:-1])


def _clean_title(title: str) -> str:
    cleaned = title.split("(")[0].strip()
    return cleaned.upper() if cleaned else "STUDY DRUG"


def _study_id(spec: dict[str, Any], rows: list[dict[str, str]]) -> str:
    from_rows = next((row.get("STUDYID") for row in rows if row.get("STUDYID")), None)
    if from_rows:
        return str(from_rows)
    return str(((spec.get("study") or {}).get("id")) or "SYNTH_PK_STUDY")


def _spec_drug_name(spec: dict[str, Any]) -> str:
    title = str(((spec.get("study") or {}).get("title")) or ((spec.get("study") or {}).get("id")) or "Study Drug")
    return _clean_title(title)


def _spec_route(spec: dict[str, Any]) -> str:
    route = str(((spec.get("regimen") or {}).get("route")) or "").strip().lower()
    if route in {"oral", "po"}:
        return "ORAL"
    if route in {"iv", "intravenous"}:
        return "INTRAVENOUS"
    return route.upper() or "UNKNOWN"


def _arm_dose(spec: dict[str, Any], arm: str) -> float | None:
    arms = ((spec.get("regimen") or {}).get("arms")) or {}
    arm_block = arms.get(arm) or (next(iter(arms.values())) if arms else {})
    return _to_float((arm_block or {}).get("dose_mg"))


def _iso_from_hours(start: datetime, hours: float | None) -> str:
    if hours is None:
        return start.isoformat(timespec="seconds")
    return (start + timedelta(hours=hours)).isoformat(timespec="seconds")


def _sex_from_row(row: dict[str, str]) -> str:
    sex = str(row.get("SEX") or row.get("SEX_CHAR") or "").strip().upper()
    if sex.startswith("F"):
        return "F"
    if sex.startswith("M"):
        return "M"
    return "U"


def _height_from_subject(subject: dict[str, Any], rng: random.Random) -> float:
    for key in ("HEIGHT_CM", "HTCM", "HEIGHT", "VSHEIGHT"):
        parsed = _to_float(subject.get(key))
        if parsed is not None and parsed > 0:
            return parsed
    sex = _sex_from_row(subject)
    wt = _to_float(subject.get("WT")) or 70.0
    base = 176.0 if sex == "M" else 163.0 if sex == "F" else 169.0
    wt_adjust = 0.18 * (wt - (78.0 if sex == "M" else 64.0 if sex == "F" else 70.0))
    height = base + wt_adjust + rng.normalvariate(0.0, 5.5)
    return min(max(height, 140.0), 205.0)


def _bmi(weight_kg: float, height_cm: float) -> float:
    return weight_kg / ((height_cm / 100.0) ** 2)


def _bsa(weight_kg: float, height_cm: float) -> float:
    return math.sqrt((height_cm * weight_kg) / 3600.0)


def _creatinine_mg_dl(subject: dict[str, Any], rng: random.Random) -> float:
    sex = _sex_from_row(subject)
    age = _to_float(subject.get("AGE")) or 50.0
    wt = _to_float(subject.get("WT")) or 70.0
    base = 0.9 if sex == "M" else 0.72 if sex == "F" else 0.8
    age_shift = max(age - 50.0, 0.0) * 0.004
    wt_shift = (wt - (78.0 if sex == "M" else 64.0 if sex == "F" else 70.0)) * 0.002
    value = base + age_shift + wt_shift + rng.normalvariate(0.0, 0.08)
    return min(max(value, 0.45), 1.8)


def _first_by_subject(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    subjects: dict[str, dict[str, str]] = {}
    for row in rows:
        key = _subject_match_key(row)
        if key and key not in subjects:
            subjects[key] = row
    if not subjects:
        raise ValueError("No subjects found in clinical_samples.csv.")
    return subjects


def _load_subjects(
    *,
    clinical_rows: list[dict[str, str]],
    subjects_csv: Path | None,
    study_id: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    clinical_subjects = _first_by_subject(clinical_rows)
    if subjects_csv is None:
        return [_normalize_subject(row, study_id=study_id) for row in clinical_subjects.values()], []

    _, subject_rows = _read_csv(subjects_csv)
    normalized: list[dict[str, Any]] = []
    warnings: list[str] = []
    clinical_by_id = {_subject_match_key(row): row for row in clinical_subjects.values()}
    clinical_ids = {key for key in clinical_by_id if key}
    subject_ids = {_subject_match_key(row) for row in subject_rows if _subject_match_key(row)}
    subjects_without_pc = sorted(subject_ids - clinical_ids)
    pc_without_subjects = sorted(clinical_ids - subject_ids)
    if subjects_without_pc or pc_without_subjects:
        warnings.append(
            "subject ID mismatch between subjects_csv and clinical_samples: "
            f"subjects_without_pc={subjects_without_pc}, pc_without_subjects={pc_without_subjects}"
        )
    for row in subject_rows:
        merged = dict(row)
        clinical = clinical_by_id.get(_subject_match_key(row))
        if clinical:
            for key in ("USUBJID", "STUDYID", "SEX_CHAR"):
                if key in clinical and key not in merged:
                    merged[key] = clinical[key]
        normalized.append(_normalize_subject(merged, study_id=study_id))
    if not normalized:
        raise ValueError(f"No subject rows found in {subjects_csv}")
    return normalized, warnings


def _normalize_subject(row: dict[str, Any], *, study_id: str) -> dict[str, Any]:
    subject_id = str(row.get("ID") or row.get("SUBJID") or row.get("USUBJID") or "").strip()
    if not subject_id:
        raise ValueError("Subject row is missing ID/USUBJID.")
    usubjid = str(row.get("USUBJID") or _subject_key(study_id, subject_id)).strip()
    sex = _sex_from_row(row)
    return {
        "STUDYID": str(row.get("STUDYID") or study_id),
        "ID": subject_id,
        "USUBJID": usubjid,
        "SUBJID": subject_id,
        "ARM": str(row.get("ARM") or "A"),
        "ACTARM": str(row.get("ACTARM") or row.get("ARM") or "A"),
        "AGE": _to_int_string(row.get("AGE")),
        "SEX": sex,
        "WT": _to_float(row.get("WT")) or 70.0,
        "DOSE_MG": _to_float(row.get("DOSE_MG")),
        "HEIGHT_CM": _to_float(row.get("HEIGHT_CM") or row.get("HEIGHT")),
    }


def _make_dm(subjects: list[dict[str, Any]], *, study_start: datetime) -> list[dict[str, Any]]:
    return [
        {
            "STUDYID": subject["STUDYID"],
            "DOMAIN": "DM",
            "USUBJID": subject["USUBJID"],
            "SUBJID": subject["SUBJID"],
            "RFSTDTC": study_start.date().isoformat(),
            "RFENDTC": study_start.date().isoformat(),
            "ARM": subject["ARM"],
            "ACTARM": subject["ACTARM"],
            "AGE": subject["AGE"],
            "AGEU": "YEARS",
            "SEX": subject["SEX"],
        }
        for subject in subjects
    ]


def _make_vs(subjects: list[dict[str, Any]], *, study_start: datetime, seed: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rng = random.Random(seed)
    tests = [
        ("HEIGHT", "Height", "cm"),
        ("WEIGHT", "Weight", "kg"),
        ("BMI", "Body Mass Index", "kg/m2"),
        ("BSA", "Body Surface Area", "m2"),
    ]
    for subject in subjects:
        wt = float(subject["WT"])
        height = float(subject["HEIGHT_CM"] or _height_from_subject(subject, rng))
        values = {
            "HEIGHT": height,
            "WEIGHT": wt,
            "BMI": _bmi(wt, height),
            "BSA": _bsa(wt, height),
        }
        for seq, (testcd, test, unit) in enumerate(tests, start=1):
            rows.append(
                {
                    "STUDYID": subject["STUDYID"],
                    "DOMAIN": "VS",
                    "USUBJID": subject["USUBJID"],
                    "VSSEQ": seq,
                    "VSTESTCD": testcd,
                    "VSTEST": test,
                    "VSORRES": values[testcd],
                    "VSORRESU": unit,
                    "VSSTRESN": values[testcd],
                    "VSSTRESU": unit,
                    "VSDTC": study_start.date().isoformat(),
                    "VISITNUM": 1,
                    "VISIT": "Baseline",
                    "VSTPT": "Baseline",
                    "VSTPTNUM": 0,
                }
            )
    return rows


def _make_lb(subjects: list[dict[str, Any]], *, study_start: datetime, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed + 1000)
    rows: list[dict[str, Any]] = []
    for subject in subjects:
        scr = _creatinine_mg_dl(subject, rng)
        rows.append(
            {
                "STUDYID": subject["STUDYID"],
                "DOMAIN": "LB",
                "USUBJID": subject["USUBJID"],
                "LBSEQ": 1,
                "LBTESTCD": "CREAT",
                "LBTEST": "Creatinine",
                "LBCAT": "CHEMISTRY",
                "LBORRES": scr,
                "LBORRESU": "mg/dL",
                "LBSTRESN": scr,
                "LBSTRESU": "mg/dL",
                "LBDTC": study_start.date().isoformat(),
                "VISITNUM": 1,
                "VISIT": "Baseline",
                "LBTPT": "Baseline",
                "LBTPTNUM": 0,
            }
        )
    return rows


def _make_ex(
    subjects: list[dict[str, Any]],
    *,
    spec: dict[str, Any],
    study_start: datetime,
) -> list[dict[str, Any]]:
    route = _spec_route(spec)
    drug_name = _spec_drug_name(spec)
    rows: list[dict[str, Any]] = []
    for seq, subject in enumerate(subjects, start=1):
        dose = subject.get("DOSE_MG") or _arm_dose(spec, str(subject.get("ARM") or "A")) or ""
        rows.append(
            {
                "STUDYID": subject["STUDYID"],
                "DOMAIN": "EX",
                "USUBJID": subject["USUBJID"],
                "EXSEQ": seq,
                "EXTRT": drug_name,
                "EXDOSE": dose,
                "EXDOSU": "mg",
                "EXROUTE": route,
                "EXSTDTC": study_start.isoformat(timespec="seconds"),
                "EXENDTC": study_start.isoformat(timespec="seconds"),
                "EXARM": subject["ARM"],
                "EXACTARM": subject["ACTARM"],
            }
        )
    return rows


def _row_value_case_insensitive(row: dict[str, str], keys: list[str]) -> str:
    lower_map = {key.lower(): value for key, value in row.items()}
    for key in keys:
        value = row.get(key)
        if not _is_blank(value):
            return str(value).strip()
        value = lower_map.get(key.lower())
        if not _is_blank(value):
            return str(value).strip()
    return ""


def _pc_conc_unit_from_row(row: dict[str, str], *, conc_col: str, conc_unit: str | None) -> str:
    if not _is_blank(conc_unit):
        return str(conc_unit).strip()
    unit = _row_value_case_insensitive(
        row,
        [
            f"{conc_col}_UNIT",
            f"{conc_col}U",
            "CONC_UNIT",
            "CONCU",
            "DV_UNIT",
            "DVU",
            "CP_UNIT",
            "CPU",
            "IPRED_UNIT",
            "IPREDU",
            "PCSTRESU",
            "PCORRESU",
            "UNIT",
        ],
    )
    return unit or "ng/mL"


def _make_pc(
    clinical_rows: list[dict[str, str]],
    *,
    study_id: str,
    study_start: datetime,
    conc_col: str,
    conc_unit: str | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for seq, row in enumerate(clinical_rows, start=1):
        usubjid = str(row.get("USUBJID") or _subject_key(study_id, row.get("ID"), fallback=seq))
        time_h = _to_float(row.get("TIME_H") or row.get("time") or row.get("TIME"))
        conc = _to_float(row.get(conc_col))
        if conc is None:
            conc = _to_float(row.get("DV") or row.get("CP") or row.get("IPRED"))
        unit = _pc_conc_unit_from_row(row, conc_col=conc_col, conc_unit=conc_unit)
        rows.append(
            {
                "STUDYID": str(row.get("STUDYID") or study_id),
                "DOMAIN": "PC",
                "USUBJID": usubjid,
                "PCSEQ": seq,
                "PCTESTCD": "DRUGCONC",
                "PCTEST": "Drug Concentration",
                "PCORRES": conc if conc is not None else "",
                "PCORRESU": unit,
                "PCSTRESN": conc if conc is not None else "",
                "PCSTRESU": unit,
                "PCDTC": _iso_from_hours(study_start, time_h),
                "PCTPT": row.get("TPT") or "",
                "PCTPTNUM": row.get("TPTNUM") or "",
                "PCELTM": f"PT{_format_number(time_h or 0.0)}H",
            }
        )
    return rows


def _pc_conc_from_row(row: dict[str, str], *, conc_col: str) -> float | None:
    conc = _to_float(row.get(conc_col))
    if conc is None:
        conc = _to_float(row.get("DV") or row.get("CP") or row.get("IPRED"))
    return conc


def _clinical_pc_match_map(
    clinical_rows: list[dict[str, str]],
    *,
    study_id: str,
    conc_col: str,
    conc_unit: str | None,
) -> dict[tuple[str, str, str], tuple[float, str]]:
    match_map: dict[tuple[str, str, str], tuple[float, str]] = {}
    for seq, row in enumerate(clinical_rows, start=1):
        conc = _pc_conc_from_row(row, conc_col=conc_col)
        if conc is None:
            continue
        unit = _pc_conc_unit_from_row(row, conc_col=conc_col, conc_unit=conc_unit)
        usubjid = str(row.get("USUBJID") or _subject_key(study_id, row.get("ID"), fallback=seq))
        tptnum = _norm_num(row.get("TPTNUM"))
        if tptnum:
            match_map[("tptnum", usubjid, tptnum)] = (conc, unit)
        tpt = _norm_text(row.get("TPT"))
        if tpt:
            match_map[("tpt", usubjid, tpt)] = (conc, unit)
        time_h = _norm_num(row.get("TIME_H") or row.get("time") or row.get("TIME") or row.get("NOMTIME_H"))
        if time_h:
            match_map[("time", usubjid, time_h)] = (conc, unit)
    return match_map


def _existing_pc_keys(row: dict[str, str]) -> list[tuple[str, str, str]]:
    usubjid = str(row.get("USUBJID") or _subject_match_key(row)).strip()
    keys: list[tuple[str, str, str]] = []
    if not usubjid:
        return keys
    tptnum = _norm_num(row.get("PCTPTNUM") or row.get("TPTNUM"))
    if tptnum:
        keys.append(("tptnum", usubjid, tptnum))
    tpt = _norm_text(row.get("PCTPT") or row.get("TPT"))
    if tpt:
        keys.append(("tpt", usubjid, tpt))
    elapsed = _pceltm_hours(row.get("PCELTM"))
    time_h = _norm_num(elapsed if elapsed is not None else row.get("TIME_H") or row.get("time") or row.get("TIME"))
    if time_h:
        keys.append(("time", usubjid, time_h))
    return keys


def _fill_existing_pc_skeleton(
    *,
    pc_csv: Path,
    clinical_rows: list[dict[str, str]],
    study_id: str,
    conc_col: str,
    conc_unit: str | None,
    overwrite_existing_pc_conc: bool,
) -> tuple[list[str], list[dict[str, str]], list[str]]:
    fieldnames, pc_rows = _read_csv(pc_csv)
    _validate_existing_domain_csv(domain="PC", fieldnames=fieldnames)
    out_fields = _ensure_fields(fieldnames, ["PCORRES", "PCORRESU", "PCSTRESN", "PCSTRESU"])
    match_map = _clinical_pc_match_map(clinical_rows, study_id=study_id, conc_col=conc_col, conc_unit=conc_unit)
    matched = 0
    unmatched_blank = 0
    for row in pc_rows:
        conc = None
        unit = ""
        for key in _existing_pc_keys(row):
            if key in match_map:
                conc, unit = match_map[key]
                break
        has_existing = not _is_blank(row.get("PCSTRESN")) or not _is_blank(row.get("PCORRES"))
        if conc is None:
            if not has_existing:
                unmatched_blank += 1
            continue
        matched += 1
        if overwrite_existing_pc_conc or not has_existing:
            value = _format_number(conc)
            row["PCORRES"] = value
            row["PCSTRESN"] = value
        if _is_blank(row.get("PCORRESU")):
            row["PCORRESU"] = unit or "ng/mL"
        if _is_blank(row.get("PCSTRESU")):
            row["PCSTRESU"] = unit or "ng/mL"

    if matched == 0 and unmatched_blank:
        raise ValueError(
            "Existing PC skeleton could not be matched to clinical sample concentrations. "
            "Expected matching USUBJID plus PCTPTNUM, PCTPT, or PCELTM/TIME."
        )
    warnings: list[str] = []
    if unmatched_blank:
        warnings.append(
            f"Existing PC skeleton had {unmatched_blank}/{len(pc_rows)} blank concentration rows without a matching clinical sample."
        )
    return out_fields, pc_rows, warnings


def _pc_concentration_warnings(clinical_rows: list[dict[str, str]], *, conc_col: str) -> list[str]:
    missing = 0
    for row in clinical_rows:
        conc = _pc_conc_from_row(row, conc_col=conc_col)
        if conc is None:
            missing += 1
    if missing == 0:
        return []
    checked = [conc_col]
    for fallback in ("DV", "CP", "IPRED"):
        if fallback not in checked:
            checked.append(fallback)
    if missing == len(clinical_rows):
        raise ValueError(
            "No usable PC concentration values found in clinical_samples.csv. "
            f"Checked columns: {', '.join(checked)}"
        )
    return [
        f"PC concentration missing for {missing}/{len(clinical_rows)} rows; "
        "PCORRES/PCSTRESN are blank for those rows."
    ]


def make_sdtm_like_domains(
    *,
    clinical_samples_csv: Path | str,
    spec_yml: Path | str,
    out_dir: Path | str,
    subjects_csv: Path | str | None = None,
    dm_csv: Path | str | None = None,
    vs_csv: Path | str | None = None,
    lb_csv: Path | str | None = None,
    ex_csv: Path | str | None = None,
    pc_csv: Path | str | None = None,
    study_start: str = "2026-01-01T08:00:00",
    seed: int = 20260217,
    pc_conc_col: str = "DV",
    pc_conc_unit: str | None = None,
    strict_subject_match: bool = False,
    overwrite_existing_pc_conc: bool = False,
) -> SdtmLikeResult:
    clinical_path = Path(clinical_samples_csv)
    spec_path = Path(spec_yml)
    out_path = Path(out_dir)
    _, clinical_rows = _read_csv(clinical_path)
    spec = _load_yaml(spec_path)
    study_id = _study_id(spec, clinical_rows)
    start = datetime.fromisoformat(study_start)
    subjects, warnings = _load_subjects(
        clinical_rows=clinical_rows,
        subjects_csv=Path(subjects_csv) if subjects_csv else None,
        study_id=study_id,
    )
    if strict_subject_match and warnings:
        raise ValueError("; ".join(warnings))
    warnings.extend(_pc_concentration_warnings(clinical_rows, conc_col=pc_conc_col))

    files = {
        "DM": out_path / "DM.csv",
        "VS": out_path / "VS.csv",
        "LB": out_path / "LB.csv",
        "EX": out_path / "EX.csv",
        "PC": out_path / "PC.csv",
        "MANIFEST": out_path / "MANIFEST.yml",
    }

    domain_sources = {
        "DM": "existing_csv" if dm_csv else "generated",
        "VS": "existing_csv" if vs_csv else "generated",
        "LB": "existing_csv" if lb_csv else "generated",
        "EX": "existing_csv" if ex_csv else "generated",
        "PC": "existing_pc_skeleton_filled" if pc_csv else "generated",
    }
    if dm_csv:
        dm_fields, dm_rows = _read_csv(Path(dm_csv))
        _validate_existing_domain_csv(domain="DM", fieldnames=dm_fields)
    else:
        dm_rows = _make_dm(subjects, study_start=start)
        dm_fields = ["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "RFSTDTC", "RFENDTC", "ARM", "ACTARM", "AGE", "AGEU", "SEX"]
    if vs_csv:
        vs_fields, vs_rows = _read_csv(Path(vs_csv))
        _validate_existing_domain_csv(domain="VS", fieldnames=vs_fields)
    else:
        vs_rows = _make_vs(subjects, study_start=start, seed=seed)
        vs_fields = [
            "STUDYID",
            "DOMAIN",
            "USUBJID",
            "VSSEQ",
            "VSTESTCD",
            "VSTEST",
            "VSORRES",
            "VSORRESU",
            "VSSTRESN",
            "VSSTRESU",
            "VSDTC",
            "VISITNUM",
            "VISIT",
            "VSTPT",
            "VSTPTNUM",
        ]
    if lb_csv:
        lb_fields, lb_rows = _read_csv(Path(lb_csv))
        _validate_existing_domain_csv(domain="LB", fieldnames=lb_fields)
    else:
        lb_rows = _make_lb(subjects, study_start=start, seed=seed)
        lb_fields = [
            "STUDYID",
            "DOMAIN",
            "USUBJID",
            "LBSEQ",
            "LBTESTCD",
            "LBTEST",
            "LBCAT",
            "LBORRES",
            "LBORRESU",
            "LBSTRESN",
            "LBSTRESU",
            "LBDTC",
            "VISITNUM",
            "VISIT",
            "LBTPT",
            "LBTPTNUM",
        ]
    if ex_csv:
        ex_fields, ex_rows = _read_csv(Path(ex_csv))
        _validate_existing_domain_csv(domain="EX", fieldnames=ex_fields)
    else:
        ex_rows = _make_ex(subjects, spec=spec, study_start=start)
        ex_fields = ["STUDYID", "DOMAIN", "USUBJID", "EXSEQ", "EXTRT", "EXDOSE", "EXDOSU", "EXROUTE", "EXSTDTC", "EXENDTC", "EXARM", "EXACTARM"]
    if pc_csv:
        pc_fields, pc_rows, pc_warnings = _fill_existing_pc_skeleton(
            pc_csv=Path(pc_csv),
            clinical_rows=clinical_rows,
            study_id=study_id,
            conc_col=pc_conc_col,
            conc_unit=pc_conc_unit,
            overwrite_existing_pc_conc=overwrite_existing_pc_conc,
        )
        warnings.extend(pc_warnings)
    else:
        pc_rows = _make_pc(
            clinical_rows,
            study_id=study_id,
            study_start=start,
            conc_col=pc_conc_col,
            conc_unit=pc_conc_unit,
        )
        pc_fields = [
            "STUDYID",
            "DOMAIN",
            "USUBJID",
            "PCSEQ",
            "PCTESTCD",
            "PCTEST",
            "PCORRES",
            "PCORRESU",
            "PCSTRESN",
            "PCSTRESU",
            "PCDTC",
            "PCTPT",
            "PCTPTNUM",
            "PCELTM",
        ]

    counts = {
        "DM": len(dm_rows),
        "VS": len(vs_rows),
        "LB": len(lb_rows),
        "EX": len(ex_rows),
        "PC": len(pc_rows),
    }
    _write_csv(
        files["DM"],
        dm_rows,
        dm_fields,
    )
    _write_csv(
        files["VS"],
        vs_rows,
        vs_fields,
    )
    _write_csv(
        files["LB"],
        lb_rows,
        lb_fields,
    )
    _write_csv(
        files["EX"],
        ex_rows,
        ex_fields,
    )
    _write_csv(
        files["PC"],
        pc_rows,
        pc_fields,
    )
    _write_yaml(
        files["MANIFEST"],
        {
            "purpose": "workflow_fixture_not_submission_ready_sdtm",
            "limited_sdtm_like": True,
            "domains": ["DM", "VS", "LB", "EX", "PC"],
            "inputs": {
                "clinical_samples_csv": str(clinical_path),
                "spec_yml": str(spec_path),
                "subjects_csv": str(subjects_csv) if subjects_csv else None,
                "dm_csv": str(dm_csv) if dm_csv else None,
                "vs_csv": str(vs_csv) if vs_csv else None,
                "lb_csv": str(lb_csv) if lb_csv else None,
                "ex_csv": str(ex_csv) if ex_csv else None,
                "pc_csv": str(pc_csv) if pc_csv else None,
            },
            "settings": {
                "study_start": study_start,
                "seed": seed,
                "pc_conc_col": pc_conc_col,
                "pc_conc_unit": pc_conc_unit,
                "strict_subject_match": strict_subject_match,
                "overwrite_existing_pc_conc": overwrite_existing_pc_conc,
            },
            "domain_sources": domain_sources,
            "counts": counts,
            "warnings": warnings,
            "notes": [
                "Generated CSVs are limited SDTM-like workflow fixtures, not submission-ready SDTM/XPT datasets.",
                "LB is limited to creatinine; VS is limited to height, weight, BMI, and BSA.",
                "EX is derived from the simulation spec/subjects; PC is derived from clinical_samples.csv.",
            ],
        },
    )
    return SdtmLikeResult(
        out_dir=out_path,
        files=files,
        counts=counts,
        warnings=warnings,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clinical-samples", required=True, type=Path, help="clinical_samples.csv from sample_clinical_timepoints.py")
    parser.add_argument("--spec", required=True, type=Path, help="spec_pk1_oral.yml or spec_pk1_iv.yml used to create the run")
    parser.add_argument("--out-dir", required=True, type=Path, help="Output directory for DM/VS/LB/EX/PC CSV files")
    parser.add_argument("--subjects-csv", type=Path, default=None, help="Optional subjects.csv with ID, ARM, DOSE_MG, WT, AGE, SEX, optional HEIGHT_CM")
    parser.add_argument("--dm-csv", type=Path, default=None, help="Optional existing DM CSV to copy into output")
    parser.add_argument("--vs-csv", type=Path, default=None, help="Optional existing VS CSV to copy into output")
    parser.add_argument("--lb-csv", type=Path, default=None, help="Optional existing LB CSV to copy into output")
    parser.add_argument("--ex-csv", type=Path, default=None, help="Optional existing EX CSV to copy into output")
    parser.add_argument("--pc-csv", type=Path, default=None, help="Optional existing PC skeleton CSV to fill with concentrations")
    parser.add_argument("--study-start", default="2026-01-01T08:00:00", help="ISO datetime for dosing and baseline records")
    parser.add_argument("--seed", type=int, default=20260217, help="Seed for synthetic HEIGHT/SCR generation")
    parser.add_argument("--pc-conc-col", default="DV", help="Clinical sample concentration column to map to PC")
    parser.add_argument("--pc-conc-unit", default=None, help="Optional concentration unit override for PCORRESU/PCSTRESU")
    parser.add_argument("--strict-subject-match", action="store_true", help="Fail if subjects.csv IDs and clinical_samples.csv IDs differ")
    parser.add_argument("--overwrite-existing-pc-conc", action="store_true", help="Overwrite nonblank PCORRES/PCSTRESN in --pc-csv")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = make_sdtm_like_domains(
            clinical_samples_csv=args.clinical_samples,
            spec_yml=args.spec,
            out_dir=args.out_dir,
            subjects_csv=args.subjects_csv,
            dm_csv=args.dm_csv,
            vs_csv=args.vs_csv,
            lb_csv=args.lb_csv,
            ex_csv=args.ex_csv,
            pc_csv=args.pc_csv,
            study_start=args.study_start,
            seed=args.seed,
            pc_conc_col=args.pc_conc_col,
            pc_conc_unit=args.pc_conc_unit,
            strict_subject_match=args.strict_subject_match,
            overwrite_existing_pc_conc=args.overwrite_existing_pc_conc,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"SDTM-like domains written: {result.out_dir}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for domain in ["DM", "VS", "LB", "EX", "PC"]:
        print(f"{domain}: {result.counts[domain]} rows -> {result.files[domain]}")
    print(f"MANIFEST: {result.files['MANIFEST']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
