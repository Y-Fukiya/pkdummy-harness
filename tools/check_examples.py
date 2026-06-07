#!/usr/bin/env python3
"""Regenerate versioned minimal examples and check for output drift."""

from __future__ import annotations

import argparse
import csv
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.make_analysis_inputs import make_analysis_inputs


CSV_OUTPUTS = ["ADPC.csv", "NCA_INPUT.csv", "POPPK_INPUT.csv"]
MANIFEST_KEYS = ["purpose", "status", "counts", "warnings"]


@dataclass(frozen=True)
class ExamplesCheckResult:
    status: str
    checked_examples: list[str]
    warnings: list[str]
    failures: list[str]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _compare_csv(expected: Path, actual: Path) -> list[str]:
    if not expected.exists():
        return [f"missing expected output: {expected}"]
    if not actual.exists():
        return [f"regenerated output missing: {actual.name}"]
    expected_rows = _read_csv(expected)
    actual_rows = _read_csv(actual)
    if expected_rows != actual_rows:
        return [f"{expected.name} drifted: expected {len(expected_rows)} rows, regenerated {len(actual_rows)} rows"]
    return []


def _compare_manifest(expected: Path, actual: Path) -> list[str]:
    if not expected.exists():
        return [f"missing expected manifest: {expected}"]
    expected_obj = _load_yaml(expected)
    actual_obj = _load_yaml(actual)
    issues: list[str] = []
    for key in MANIFEST_KEYS:
        if expected_obj.get(key) != actual_obj.get(key):
            issues.append(f"MANIFEST.yml drifted at {key!r}: expected {expected_obj.get(key)!r}, regenerated {actual_obj.get(key)!r}")
    return issues


def _example_dirs(examples_dir: Path) -> list[Path]:
    return sorted(path for path in examples_dir.glob("minimal_*") if path.is_dir())


def check_examples(examples_dir: Path | str = "examples") -> ExamplesCheckResult:
    examples_path = Path(examples_dir)
    failures: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []

    if not examples_path.exists():
        return ExamplesCheckResult("FAILED", [], [], [f"examples directory not found: {examples_path}"])

    dirs = _example_dirs(examples_path)
    if not dirs:
        return ExamplesCheckResult("FAILED", [], [], [f"no minimal_* examples found under {examples_path}"])

    with tempfile.TemporaryDirectory(prefix="pk-fixture-examples-") as tmp:
        tmp_root = Path(tmp)
        for example_dir in dirs:
            name = example_dir.name
            checked.append(name)
            source_dir = example_dir / "sdtm_like"
            expected_dir = example_dir / "workflow" / "analysis_inputs"
            if not source_dir.is_dir():
                failures.append(f"{name}: missing sdtm_like source directory")
                continue
            if not expected_dir.is_dir():
                failures.append(f"{name}: missing workflow/analysis_inputs expected directory")
                continue

            actual_dir = tmp_root / name / "analysis_inputs"
            result = make_analysis_inputs(sdtm_like_dir=source_dir, out_dir=actual_dir)
            if result.status != "OK":
                warnings.extend(f"{name}: {warning}" for warning in result.warnings)
            for filename in CSV_OUTPUTS:
                failures.extend(f"{name}: {issue}" for issue in _compare_csv(expected_dir / filename, actual_dir / filename))
            failures.extend(
                f"{name}: {issue}"
                for issue in _compare_manifest(expected_dir / "MANIFEST.yml", actual_dir / "MANIFEST.yml")
            )

    return ExamplesCheckResult("FAILED" if failures else "OK", checked, warnings, failures)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("examples_dir", nargs="?", default="examples", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    result = check_examples(args.examples_dir)
    print(f"Examples check: {result.status}")
    for name in result.checked_examples:
        print(f"checked: {name}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for failure in result.failures:
        print(f"ERROR: {failure}")
    return 0 if result.status == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
