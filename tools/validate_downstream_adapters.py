#!/usr/bin/env python3
"""Validate lightweight downstream adapter CSV contracts.

This checks repository-owned smoke-test contracts only. It does not certify
Phoenix, NONMEM, nlmixr2, or any other external tool dataset specification.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONTRACTS = {
    "nca_r.csv": {
        "required": ["ID", "TIME", "CONC", "CONC_UNIT", "DOSE", "DOSE_UNIT", "ROUTE"],
        "numeric": ["TIME", "CONC", "DOSE"],
        "type": "nca",
    },
    "nca_phoenix.csv": {
        "required": ["Subject", "Time", "Concentration", "ConcentrationUnit", "Dose", "DoseUnit", "Route"],
        "numeric": ["Time", "Concentration", "Dose"],
        "type": "nca",
    },
    "poppk_nonmem.csv": {
        "required": ["ID", "TIME", "EVID", "MDV", "AMT", "DV", "CMT", "RATE", "DOSE", "ROUTE", "USUBJID"],
        "numeric": ["TIME", "EVID", "MDV", "AMT", "CMT", "RATE"],
        "type": "poppk",
    },
    "poppk_nlmixr2.csv": {
        "required": ["id", "time", "evid", "mdv", "amt", "dv", "cmt", "rate", "dose", "route", "usubjid"],
        "numeric": ["time", "evid", "mdv", "amt", "cmt", "rate"],
        "type": "poppk",
    },
}


@dataclass(frozen=True)
class AdapterValidationResult:
    status: str
    files_checked: list[str]
    issues: list[str]
    warnings: list[str]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV is empty: {path}")
        return list(reader.fieldnames), list(reader)


def _to_float(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _check_numeric(*, filename: str, rows: list[dict[str, str]], numeric_fields: list[str], issues: list[str]) -> None:
    for idx, row in enumerate(rows, start=2):
        for field in numeric_fields:
            if _is_blank(row.get(field)):
                continue
            if _to_float(row.get(field)) is None:
                issues.append(f"{filename}:{idx}: {field} must be numeric")


def _check_nca(*, filename: str, rows: list[dict[str, str]], subject_col: str, time_col: str, conc_col: str, issues: list[str]) -> None:
    by_subject: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        subject = str(row.get(subject_col) or "").strip()
        if subject:
            by_subject.setdefault(subject, []).append(row)
    if not by_subject:
        issues.append(f"{filename}: no subject IDs found")
        return
    for subject, subject_rows in by_subject.items():
        times = [_to_float(row.get(time_col)) for row in subject_rows if _to_float(row.get(time_col)) is not None]
        concs = [_to_float(row.get(conc_col)) for row in subject_rows if _to_float(row.get(conc_col)) is not None]
        if len(times) < 2:
            issues.append(f"{filename}: subject {subject} has fewer than 2 time points")
        if not concs:
            issues.append(f"{filename}: subject {subject} has no usable concentrations")
        if times != sorted(times):
            issues.append(f"{filename}: subject {subject} times are not sorted")


def _check_poppk(
    *,
    filename: str,
    rows: list[dict[str, str]],
    id_col: str,
    time_col: str,
    evid_col: str,
    mdv_col: str,
    amt_col: str,
    dv_col: str,
    issues: list[str],
) -> None:
    by_id: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        subject = str(row.get(id_col) or "").strip()
        if subject:
            by_id.setdefault(subject, []).append(row)
    if not by_id:
        issues.append(f"{filename}: no ID values found")
        return
    for subject, subject_rows in by_id.items():
        times = [_to_float(row.get(time_col)) for row in subject_rows if _to_float(row.get(time_col)) is not None]
        if times != sorted(times):
            issues.append(f"{filename}: ID {subject} times are not sorted")
        dose_rows = [row for row in subject_rows if str(row.get(evid_col)).strip() == "1"]
        obs_rows = [row for row in subject_rows if str(row.get(evid_col)).strip() == "0"]
        if not dose_rows:
            issues.append(f"{filename}: ID {subject} has no EVID=1 dose row")
        if not obs_rows:
            issues.append(f"{filename}: ID {subject} has no EVID=0 observation rows")
        for row in dose_rows:
            amt = _to_float(row.get(amt_col))
            if amt is None or amt <= 0:
                issues.append(f"{filename}: ID {subject} dose row has non-positive AMT")
        for row in obs_rows:
            if str(row.get(mdv_col)).strip() == "0" and _is_blank(row.get(dv_col)):
                issues.append(f"{filename}: ID {subject} MDV=0 observation has missing DV")


def validate_adapter_dir(adapter_dir: Path | str) -> AdapterValidationResult:
    adapter_path = Path(adapter_dir)
    issues: list[str] = []
    warnings: list[str] = []
    files_checked: list[str] = []
    if not adapter_path.is_dir():
        return AdapterValidationResult("FAILED", [], [f"adapter directory not found: {adapter_path}"], [])

    for filename, contract in CONTRACTS.items():
        path = adapter_path / filename
        if not path.exists():
            continue
        files_checked.append(filename)
        try:
            fieldnames, rows = _read_csv(path)
        except Exception as exc:
            issues.append(f"{filename}: {exc}")
            continue
        missing = [field for field in contract["required"] if field not in fieldnames]
        if missing:
            issues.append(f"{filename} missing required columns: {missing}")
            continue
        if not rows:
            issues.append(f"{filename}: no data rows")
            continue
        _check_numeric(filename=filename, rows=rows, numeric_fields=list(contract["numeric"]), issues=issues)
        if contract["type"] == "nca":
            if filename == "nca_r.csv":
                _check_nca(filename=filename, rows=rows, subject_col="ID", time_col="TIME", conc_col="CONC", issues=issues)
            else:
                _check_nca(filename=filename, rows=rows, subject_col="Subject", time_col="Time", conc_col="Concentration", issues=issues)
        else:
            if filename == "poppk_nonmem.csv":
                _check_poppk(
                    filename=filename,
                    rows=rows,
                    id_col="ID",
                    time_col="TIME",
                    evid_col="EVID",
                    mdv_col="MDV",
                    amt_col="AMT",
                    dv_col="DV",
                    issues=issues,
                )
            else:
                _check_poppk(
                    filename=filename,
                    rows=rows,
                    id_col="id",
                    time_col="time",
                    evid_col="evid",
                    mdv_col="mdv",
                    amt_col="amt",
                    dv_col="dv",
                    issues=issues,
                )

    if not files_checked:
        issues.append(f"no known adapter CSVs found in {adapter_path}")
    status = "FAILED" if issues else "OK"
    return AdapterValidationResult(status, sorted(files_checked), issues, warnings)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adapter_dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    result = validate_adapter_dir(args.adapter_dir)
    print(f"Downstream adapter validation: {result.status}")
    for filename in result.files_checked:
        print(f"checked: {filename}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for issue in result.issues:
        print(f"ERROR: {issue}")
    return 0 if result.status == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
