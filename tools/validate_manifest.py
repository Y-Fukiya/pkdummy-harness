#!/usr/bin/env python3
"""Validate PK fixture harness MANIFEST.yml files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


REQUIRED_FIELDS = ["purpose", "status", "outputs"]
ALLOWED_STATUS = {"OK", "WARN", "FAILED"}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = yaml.safe_load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"{path.name}: manifest must be a mapping")
    return obj


def validate_manifest_obj(obj: dict[str, Any], *, label: str = "MANIFEST.yml") -> list[str]:
    issues: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in obj:
            issues.append(f"{label}: missing required field: {field}")
    status = obj.get("status")
    if status is not None and status not in ALLOWED_STATUS:
        issues.append(f"{label}: status must be one of {sorted(ALLOWED_STATUS)}, got {status!r}")
    if "purpose" in obj and not str(obj.get("purpose") or "").strip():
        issues.append(f"{label}: purpose must be non-empty")
    for field in ("inputs", "outputs", "counts", "render"):
        if field in obj and not isinstance(obj.get(field), dict):
            issues.append(f"{label}: {field} must be a mapping")
    if "warnings" in obj and not isinstance(obj.get("warnings"), list):
        issues.append(f"{label}: warnings must be a list")
    if "safeguards" in obj and not isinstance(obj.get("safeguards"), list):
        issues.append(f"{label}: safeguards must be a list")
    return issues


def validate_manifest_file(path: Path | str) -> list[str]:
    manifest_path = Path(path)
    try:
        obj = _load_yaml(manifest_path)
    except Exception as exc:
        return [f"{manifest_path.name}: {exc}"]
    return validate_manifest_obj(obj, label=manifest_path.name)


def _collect_paths(paths: list[Path], *, recursive: bool) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        if path.is_dir():
            pattern = "**/*MANIFEST.yml" if recursive else "*MANIFEST.yml"
            out.extend(sorted(path.glob(pattern)))
        else:
            out.append(path)
    return out


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--recursive", action="store_true", help="Search directories recursively for *MANIFEST.yml")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    paths = _collect_paths(args.paths, recursive=args.recursive)
    issues: list[str] = []
    for path in paths:
        issues.extend(validate_manifest_file(path))
    if issues:
        print("Manifest validation: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Manifest validation: OK")
    for path in paths:
        print(f"checked: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
