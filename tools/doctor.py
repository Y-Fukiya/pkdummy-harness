#!/usr/bin/env python3
"""Preflight dependency check for the PK fixture harness."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


CommandExists = Callable[[str], bool]
PackageExists = Callable[[str], bool]


@dataclass(frozen=True)
class DependencyCheck:
    name: str
    status: str
    level: str
    message: str


@dataclass(frozen=True)
class DoctorResult:
    status: str
    checks: list[DependencyCheck]


def _default_command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def _default_python_package_exists(package: str) -> bool:
    return importlib.util.find_spec(package) is not None


def _default_r_package_exists(package: str) -> bool:
    if shutil.which("Rscript") is None:
        return False
    completed = subprocess.run(
        [
            "Rscript",
            "-e",
            f"quit(status = ifelse(requireNamespace('{package}', quietly = TRUE), 0, 1))",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=20,
    )
    return completed.returncode == 0


def _check(name: str, *, ok: bool, level: str, ok_message: str, missing_message: str) -> DependencyCheck:
    if ok:
        return DependencyCheck(name=name, status="OK", level=level, message=ok_message)
    status = "FAILED" if level == "required" else "WARN"
    return DependencyCheck(name=name, status=status, level=level, message=missing_message)


def run_doctor(
    *,
    command_exists: CommandExists = _default_command_exists,
    python_package_exists: PackageExists = _default_python_package_exists,
    r_package_exists: PackageExists = _default_r_package_exists,
) -> DoctorResult:
    checks = [
        _check(
            "python3",
            ok=command_exists("python3"),
            level="required",
            ok_message="Python CLI is available.",
            missing_message="python3 is required for the CLI harness.",
        ),
        _check(
            "python_package:yaml",
            ok=python_package_exists("yaml"),
            level="required",
            ok_message="PyYAML is importable.",
            missing_message="PyYAML is required; install requirements.txt.",
        ),
        _check(
            "Rscript",
            ok=command_exists("Rscript"),
            level="recommended",
            ok_message="Rscript is available for reporting tools.",
            missing_message="Rscript is missing; Python-only workflows still run, but R reports will not.",
        ),
        _check(
            "R_package:ggplot2",
            ok=r_package_exists("ggplot2"),
            level="recommended",
            ok_message="ggplot2 is available for concentration plots.",
            missing_message="ggplot2 is missing; report_pk_fixture.R cannot make ggplot figures.",
        ),
        _check(
            "quarto",
            ok=command_exists("quarto"),
            level="recommended",
            ok_message="Quarto is available for DOCX report rendering.",
            missing_message="Quarto is missing; DOCX report rendering is optional.",
        ),
        _check(
            "R_package:simpop",
            ok=r_package_exists("simpop"),
            level="optional",
            ok_message="simpop is available for optional subject generation.",
            missing_message="simpop is missing; built-in fallback subject fixtures can still be used.",
        ),
    ]
    if any(check.status == "FAILED" for check in checks):
        status = "FAILED"
    elif any(check.status == "WARN" for check in checks):
        status = "WARN"
    else:
        status = "OK"
    return DoctorResult(status=status, checks=checks)


def _payload(result: DoctorResult) -> dict[str, object]:
    return {
        "purpose": "pk_fixture_harness_preflight",
        "status": result.status,
        "checks": [asdict(check) for check in result.checks],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    result = run_doctor()
    if args.json:
        print(json.dumps(_payload(result), indent=2, ensure_ascii=False))
    else:
        print(f"Doctor: {result.status}")
        for check in result.checks:
            print(f"{check.status}\t{check.level}\t{check.name}\t{check.message}")
    return 1 if result.status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
