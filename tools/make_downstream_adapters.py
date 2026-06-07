#!/usr/bin/env python3
"""Create lightweight NCA/PopPK tool-specific adapter CSVs.

These adapter outputs are workflow fixtures. They normalize column names for
common downstream parser smoke tests; they are not tool-certified datasets.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


DEFAULT_TARGETS = ["r_nca", "phoenix_nca", "nonmem", "nlmixr2"]


@dataclass(frozen=True)
class AdapterResult:
    out_dir: Path
    status: str
    files: dict[str, Path]
    counts: dict[str, int]
    warnings: list[str]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV is empty: {path}")
        return list(reader)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_yaml(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _require(path: Path) -> None:
    if not path.exists():
        raise ValueError(f"Required analysis input not found: {path}")


def _r_nca_rows(adpc_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "ID": row.get("USUBJID", ""),
            "TIME": row.get("TIME_H", ""),
            "CONC": row.get("AVAL", ""),
            "CONC_UNIT": row.get("AVALU", ""),
            "DOSE": row.get("DOSE_MG", ""),
            "DOSE_UNIT": row.get("DOSE_UNIT", ""),
            "ROUTE": row.get("ROUTE", ""),
            "ARM": row.get("ARM", ""),
            "AGE": row.get("AGE", ""),
            "SEX": row.get("SEX", ""),
            "WT": row.get("WT", ""),
            "BSA": row.get("BSA", ""),
            "CREAT_MG_DL": row.get("CREAT_MG_DL", ""),
        }
        for row in adpc_rows
    ]


def _phoenix_rows(adpc_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "Subject": row.get("USUBJID", ""),
            "Time": row.get("TIME_H", ""),
            "Concentration": row.get("AVAL", ""),
            "ConcentrationUnit": row.get("AVALU", ""),
            "Dose": row.get("DOSE_MG", ""),
            "DoseUnit": row.get("DOSE_UNIT", ""),
            "Route": row.get("ROUTE", ""),
            "Treatment": row.get("ARM", ""),
            "NominalTime": row.get("NOMTIME_H", row.get("TIME_H", "")),
            "TimePoint": row.get("TPT", ""),
            "TimePointNumber": row.get("TPTNUM", ""),
        }
        for row in adpc_rows
    ]


def _nonmem_rows(poppk_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "ID": row.get("ID", ""),
            "TIME": row.get("TIME", ""),
            "EVID": row.get("EVID", ""),
            "MDV": row.get("MDV", ""),
            "AMT": row.get("AMT", ""),
            "DV": row.get("DV", ""),
            "CMT": row.get("CMT", ""),
            "RATE": row.get("RATE", ""),
            "DOSE": row.get("DOSE_MG", ""),
            "ROUTE": row.get("ROUTE", ""),
            "WT": row.get("WT", ""),
            "AGE": row.get("AGE", ""),
            "SEX": row.get("SEX", ""),
            "BSA": row.get("BSA", ""),
            "CREAT": row.get("CREAT_MG_DL", ""),
            "USUBJID": row.get("USUBJID", ""),
        }
        for row in poppk_rows
    ]


def _nlmixr2_rows(poppk_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [
        {
            "id": row.get("ID", ""),
            "time": row.get("TIME", ""),
            "evid": row.get("EVID", ""),
            "mdv": row.get("MDV", ""),
            "amt": row.get("AMT", ""),
            "dv": row.get("DV", ""),
            "cmt": row.get("CMT", ""),
            "rate": row.get("RATE", ""),
            "dose": row.get("DOSE_MG", ""),
            "route": row.get("ROUTE", ""),
            "wt": row.get("WT", ""),
            "age": row.get("AGE", ""),
            "sex": row.get("SEX", ""),
            "bsa": row.get("BSA", ""),
            "creat": row.get("CREAT_MG_DL", ""),
            "usubjid": row.get("USUBJID", ""),
        }
        for row in poppk_rows
    ]


def _parse_targets(value: str | list[str] | None) -> list[str]:
    if value is None:
        return list(DEFAULT_TARGETS)
    if isinstance(value, list):
        parts = [str(part).strip() for part in value]
    else:
        parts = [part.strip() for part in str(value).split(",")]
    out = [part for part in parts if part]
    unknown = sorted(set(out) - set(DEFAULT_TARGETS))
    if unknown:
        raise ValueError(f"Unknown adapter targets: {unknown}")
    return out


def make_downstream_adapters(
    *,
    analysis_dir: Path | str,
    out_dir: Path | str,
    targets: str | list[str] | None = None,
) -> AdapterResult:
    analysis_path = Path(analysis_dir)
    out_path = Path(out_dir)
    target_list = _parse_targets(targets)
    adpc_path = analysis_path / "ADPC.csv"
    poppk_path = analysis_path / "POPPK_INPUT.csv"
    _require(adpc_path)
    _require(poppk_path)

    adpc_rows = _read_csv(adpc_path)
    poppk_rows = _read_csv(poppk_path)
    if not adpc_rows:
        raise ValueError("ADPC.csv has no rows.")
    if not poppk_rows:
        raise ValueError("POPPK_INPUT.csv has no rows.")

    files: dict[str, Path] = {}
    warnings: list[str] = []
    if "r_nca" in target_list:
        path = out_path / "nca_r.csv"
        _write_csv(path, _r_nca_rows(adpc_rows), ["ID", "TIME", "CONC", "CONC_UNIT", "DOSE", "DOSE_UNIT", "ROUTE", "ARM", "AGE", "SEX", "WT", "BSA", "CREAT_MG_DL"])
        files["r_nca"] = path
    if "phoenix_nca" in target_list:
        path = out_path / "nca_phoenix.csv"
        _write_csv(path, _phoenix_rows(adpc_rows), ["Subject", "Time", "Concentration", "ConcentrationUnit", "Dose", "DoseUnit", "Route", "Treatment", "NominalTime", "TimePoint", "TimePointNumber"])
        files["phoenix_nca"] = path
    if "nonmem" in target_list:
        path = out_path / "poppk_nonmem.csv"
        _write_csv(path, _nonmem_rows(poppk_rows), ["ID", "TIME", "EVID", "MDV", "AMT", "DV", "CMT", "RATE", "DOSE", "ROUTE", "WT", "AGE", "SEX", "BSA", "CREAT", "USUBJID"])
        files["nonmem"] = path
    if "nlmixr2" in target_list:
        path = out_path / "poppk_nlmixr2.csv"
        _write_csv(path, _nlmixr2_rows(poppk_rows), ["id", "time", "evid", "mdv", "amt", "dv", "cmt", "rate", "dose", "route", "wt", "age", "sex", "bsa", "creat", "usubjid"])
        files["nlmixr2"] = path

    if any(_norm(row.get("AVAL")) == "" for row in adpc_rows):
        warnings.append("ADPC.csv contains missing AVAL values; adapter outputs preserve missing concentrations.")
    manifest = out_path / "MANIFEST.yml"
    files["manifest"] = manifest
    counts = {
        "adpc_rows": len(adpc_rows),
        "poppk_rows": len(poppk_rows),
        "targets": len(target_list),
    }
    _write_yaml(
        manifest,
        {
            "purpose": "downstream_tool_adapter_fixture",
            "status": "WARN" if warnings else "OK",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "inputs": {
                "analysis_dir": str(analysis_path),
                "adpc_csv": str(adpc_path),
                "poppk_input_csv": str(poppk_path),
            },
            "targets": target_list,
            "outputs": {key: str(path) for key, path in files.items()},
            "counts": counts,
            "warnings": warnings,
            "notes": [
                "Adapter CSVs are lightweight parser/workflow fixtures.",
                "They are not certified Phoenix, NONMEM, or nlmixr2 datasets.",
                "Tool-specific model/control configuration remains outside this harness.",
            ],
        },
    )
    return AdapterResult(out_dir=out_path, status="WARN" if warnings else "OK", files=files, counts=counts, warnings=warnings)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--targets", default=",".join(DEFAULT_TARGETS), help="Comma-separated targets: r_nca, phoenix_nca, nonmem, nlmixr2")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = make_downstream_adapters(analysis_dir=args.analysis_dir, out_dir=args.out_dir, targets=args.targets)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Downstream adapters written: {result.status}")
    print(f"Output directory: {result.out_dir}")
    for key in sorted(result.files):
        print(f"{key}: {result.files[key]}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
