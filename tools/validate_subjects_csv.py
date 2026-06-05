#!/usr/bin/env python3
"""Validate optional subject-level covariate CSV files for PK simulations."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.template_gen import SUBJECT_CSV_REQUIRED_COLUMNS


def _missing_columns(fieldnames: Iterable[str] | None) -> list[str]:
    present = set(fieldnames or [])
    return [col for col in SUBJECT_CSV_REQUIRED_COLUMNS if col not in present]


def _is_float(value: str) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def validate_subject_rows(
    rows: list[dict[str, str]],
    *,
    fieldnames: Iterable[str] | None = None,
    expected_n: int | None = None,
    allowed_arms: set[str] | None = None,
) -> list[str]:
    """Return validation issues for runner-ready subject rows."""
    issues: list[str] = []
    header = list(fieldnames or (rows[0].keys() if rows else SUBJECT_CSV_REQUIRED_COLUMNS))
    missing = _missing_columns(header)
    if missing:
        return [f"missing required subject columns: {', '.join(missing)}"]

    if expected_n is not None and len(rows) != expected_n:
        issues.append(f"expected {expected_n} subjects, found {len(rows)}")

    seen_ids: set[str] = set()
    for idx, row in enumerate(rows, start=2):
        subject_id = str(row.get("ID", "")).strip()
        if not subject_id:
            issues.append(f"row {idx}: ID is blank")
        elif subject_id in seen_ids:
            issues.append(f"row {idx}: duplicate ID {subject_id}")
        seen_ids.add(subject_id)

        arm = str(row.get("ARM", "")).strip()
        if not arm:
            issues.append(f"row {idx}: ARM is blank")
        elif allowed_arms is not None and arm not in allowed_arms:
            issues.append(f"row {idx}: ARM {arm!r} is not in allowed arms {sorted(allowed_arms)}")

        for col in ["DOSE_MG", "WT", "AGE"]:
            raw = str(row.get(col, "")).strip()
            if not _is_float(raw):
                issues.append(f"row {idx}: {col} must be numeric")
                continue
            if col in {"DOSE_MG", "WT"} and float(raw) <= 0:
                issues.append(f"row {idx}: {col} must be > 0")

        height_raw = str(row.get("HEIGHT_CM", "")).strip()
        if height_raw:
            if not _is_float(height_raw):
                issues.append(f"row {idx}: HEIGHT_CM must be numeric")
            elif float(height_raw) <= 0:
                issues.append(f"row {idx}: HEIGHT_CM must be > 0")

        sex = str(row.get("SEX", "")).strip().upper()
        if sex not in {"M", "F"}:
            issues.append(f"row {idx}: SEX must be M or F")

    return issues


def validate_subjects_csv(
    path: Path,
    *,
    expected_n: int | None = None,
    allowed_arms: set[str] | None = None,
) -> list[str]:
    if not path.exists():
        return [f"subjects CSV not found: {path}"]
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return validate_subject_rows(
            rows,
            fieldnames=reader.fieldnames,
            expected_n=expected_n,
            allowed_arms=allowed_arms,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path, help="subjects.csv to validate")
    parser.add_argument("--expected-n", type=int, default=None)
    parser.add_argument("--allowed-arm", action="append", dest="allowed_arms", default=None)
    args = parser.parse_args(argv)

    issues = validate_subjects_csv(
        args.csv,
        expected_n=args.expected_n,
        allowed_arms=set(args.allowed_arms) if args.allowed_arms else None,
    )
    if issues:
        print("Subject CSV validation: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Subject CSV validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
