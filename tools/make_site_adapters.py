#!/usr/bin/env python3
"""Create site-specific CSV adapters from analysis input fixtures."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


SOURCE_FILES = {
    "ADPC": "ADPC.csv",
    "NCA_INPUT": "NCA_INPUT.csv",
    "POPPK_INPUT": "POPPK_INPUT.csv",
}


@dataclass(frozen=True)
class SiteAdapterResult:
    out_dir: Path
    status: str
    files: dict[str, Path]
    counts: dict[str, int]
    warnings: list[str]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = yaml.safe_load(f) or {}
    if not isinstance(obj, dict):
        raise ValueError(f"Site adapter spec must be a mapping: {path}")
    return obj


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
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_yaml(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)


def _source_path(analysis_dir: Path, source_name: str) -> Path:
    try:
        filename = SOURCE_FILES[source_name]
    except KeyError as exc:
        raise ValueError(f"Unsupported site adapter source: {source_name}") from exc
    path = analysis_dir / filename
    if not path.exists():
        raise ValueError(f"Required source CSV not found for {source_name}: {path}")
    return path


def _safe_output_path(adapter_name: str, out_dir: Path, output: str) -> Path:
    raw_candidate = out_dir / output
    base = out_dir.resolve(strict=False)
    candidate = raw_candidate.resolve(strict=False)
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"{adapter_name}: output path must stay inside out_dir: {output}") from exc
    return raw_candidate


def _column_value(adapter_name: str, column: dict[str, Any], row: dict[str, str], source_fields: set[str]) -> str:
    name = str(column.get("name") or "").strip()
    if not name:
        raise ValueError(f"{adapter_name}: column entry is missing name")
    if "value" in column:
        return str(column.get("value") or "")
    source = str(column.get("source") or "").strip()
    if not source:
        raise ValueError(f"{adapter_name}: column {name} needs either source or value")
    if source not in source_fields:
        raise ValueError(f"{adapter_name}: source column not found: {source}")
    return row.get(source, "")


def _build_rows(
    *,
    adapter_name: str,
    source_rows: list[dict[str, str]],
    source_fields: list[str],
    columns: list[dict[str, Any]],
    required_nonblank: list[str],
) -> tuple[list[str], list[dict[str, str]], list[str]]:
    source_set = set(source_fields)
    fieldnames = [str(column.get("name") or "").strip() for column in columns]
    if not fieldnames or any(not field for field in fieldnames):
        raise ValueError(f"{adapter_name}: columns must have non-empty names")
    out_rows: list[dict[str, str]] = []
    warnings: list[str] = []
    for row_idx, row in enumerate(source_rows, start=2):
        out_row = {
            field: _column_value(adapter_name, column, row, source_set)
            for field, column in zip(fieldnames, columns)
        }
        missing_required = [field for field in required_nonblank if str(out_row.get(field) or "").strip() == ""]
        if missing_required:
            warnings.append(f"{adapter_name}: row {row_idx} has blank required fields: {missing_required}")
        out_rows.append(out_row)
    return fieldnames, out_rows, warnings


def make_site_adapters(
    *,
    analysis_dir: Path | str,
    spec_yml: Path | str,
    out_dir: Path | str,
) -> SiteAdapterResult:
    analysis_path = Path(analysis_dir)
    spec_path = Path(spec_yml)
    out_path = Path(out_dir)
    spec = _load_yaml(spec_path)
    adapters = spec.get("adapters") or {}
    if not isinstance(adapters, dict) or not adapters:
        raise ValueError(f"No adapters found in {spec_path}")

    files: dict[str, Path] = {}
    counts: dict[str, int] = {}
    warnings: list[str] = []
    for adapter_name, adapter in adapters.items():
        if not isinstance(adapter, dict):
            raise ValueError(f"{adapter_name}: adapter spec must be a mapping")
        source_name = str(adapter.get("source") or "").strip()
        source_fields, source_rows = _read_csv(_source_path(analysis_path, source_name))
        columns = adapter.get("columns") or []
        if not isinstance(columns, list) or not columns:
            raise ValueError(f"{adapter_name}: columns must be a non-empty list")
        required_nonblank = [str(value) for value in (adapter.get("required_nonblank") or [])]
        fieldnames, out_rows, adapter_warnings = _build_rows(
            adapter_name=str(adapter_name),
            source_rows=source_rows,
            source_fields=source_fields,
            columns=columns,
            required_nonblank=required_nonblank,
        )
        output = str(adapter.get("output") or f"{adapter_name}.csv")
        out_file = _safe_output_path(str(adapter_name), out_path, output)
        _write_csv(out_file, out_rows, fieldnames)
        files[str(adapter_name)] = out_file
        counts[f"{adapter_name}_rows"] = len(out_rows)
        warnings.extend(adapter_warnings)

    manifest = out_path / "SITE_ADAPTER_MANIFEST.yml"
    files["manifest"] = manifest
    status = "WARN" if warnings else "OK"
    _write_yaml(
        manifest,
        {
            "purpose": "site_specific_adapter_fixture",
            "status": status,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "inputs": {
                "analysis_dir": str(analysis_path),
                "spec_yml": str(spec_path),
            },
            "adapters": [name for name in adapters],
            "outputs": {key: str(value) for key, value in files.items()},
            "counts": counts,
            "warnings": warnings,
            "notes": [
                "These CSVs are site-specific workflow fixtures generated from analysis_inputs.",
                "They are not certified NCA, Phoenix, NONMEM, nlmixr2, ADaM, or SDTM datasets.",
                "Keep site-specific mapping specs under version control when sharing validation expectations.",
            ],
        },
    )
    return SiteAdapterResult(out_path, status, files, counts, warnings)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", required=True, type=Path)
    parser.add_argument("--spec-yml", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = make_site_adapters(analysis_dir=args.analysis_dir, spec_yml=args.spec_yml, out_dir=args.out_dir)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Site adapters written: {result.status}")
    print(f"Output directory: {result.out_dir}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for key in sorted(result.files):
        print(f"{key}: {result.files[key]}")
    return 1 if result.status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
