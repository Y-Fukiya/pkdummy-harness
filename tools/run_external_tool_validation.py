#!/usr/bin/env python3
"""Run optional external Phoenix/NONMEM/nlmixr2 validation hooks.

External tools and licenses are not bundled. This command lives in the same
repository so projects can record and run environment-specific validation in a
consistent manifest, while remaining safe on CI machines that do not have those
tools installed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ExternalToolResult:
    name: str
    status: str
    required: bool
    command: list[str]
    cwd: Path
    returncode: int | None
    stdout_log: Path | None
    stderr_log: Path | None
    success_artifacts: list[Path]
    message: str


@dataclass(frozen=True)
class ExternalValidationResult:
    out_dir: Path
    status: str
    execute: bool
    results: list[ExternalToolResult]
    manifest: Path


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = yaml.safe_load(f) or {}
    if not isinstance(obj, dict):
        raise ValueError(f"Profile YAML must be a mapping: {path}")
    return obj


def _write_yaml(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)


def _format_token(token: Any, variables: dict[str, str]) -> str:
    return str(token).format(**variables)


def _format_command(command: list[Any], variables: dict[str, str]) -> list[str]:
    return [_format_token(token, variables) for token in command]


def _parse_tools(value: str | list[str] | None, available: list[str]) -> list[str]:
    if value is None:
        return available
    if isinstance(value, list):
        out = [str(item).strip() for item in value if str(item).strip()]
    else:
        out = [item.strip() for item in str(value).split(",") if item.strip()]
    unknown = sorted(set(out) - set(available))
    if unknown:
        raise ValueError(f"Unknown external validation profiles: {unknown}")
    return out


def _tool_available(command: list[str]) -> bool:
    if not command:
        return False
    executable = command[0]
    if Path(executable).is_file():
        return True
    return shutil.which(executable) is not None


def _result_payload(result: ExternalToolResult) -> dict[str, Any]:
    payload = asdict(result)
    payload["cwd"] = str(result.cwd)
    payload["stdout_log"] = str(result.stdout_log) if result.stdout_log else None
    payload["stderr_log"] = str(result.stderr_log) if result.stderr_log else None
    payload["success_artifacts"] = [str(path) for path in result.success_artifacts]
    return payload


def _write_stream(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _run_profile(
    *,
    name: str,
    profile: dict[str, Any],
    out_dir: Path,
    variables: dict[str, str],
    execute: bool,
) -> ExternalToolResult:
    command = _format_command(list(profile.get("command") or []), variables)
    required = bool(profile.get("required", False))
    tool_dir = out_dir / name
    cwd = tool_dir
    cwd.mkdir(parents=True, exist_ok=True)
    success_artifacts = [cwd / _format_token(path, variables) for path in (profile.get("success_artifacts") or [])]

    if not command:
        status = "FAILED" if required else "SKIPPED"
        return ExternalToolResult(name, status, required, command, cwd, None, None, None, success_artifacts, "no command configured")

    if not _tool_available(command):
        status = "FAILED" if required else "SKIPPED"
        return ExternalToolResult(name, status, required, command, cwd, None, None, None, success_artifacts, f"executable not found: {command[0]}")

    if not execute:
        return ExternalToolResult(name, "OK", required, command, cwd, None, None, None, success_artifacts, "probe passed; execute=false")

    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=int(profile.get("timeout_s", 300) or 300),
    )
    stdout_log = _write_stream(cwd / "stdout.log", completed.stdout)
    stderr_log = _write_stream(cwd / "stderr.log", completed.stderr)
    missing_artifacts = [path for path in success_artifacts if not path.exists()]
    if completed.returncode != 0:
        status = "FAILED" if required else "WARN"
        message = f"command exited with {completed.returncode}"
    elif missing_artifacts:
        status = "FAILED" if required else "WARN"
        message = f"missing success artifacts: {[path.name for path in missing_artifacts]}"
    else:
        status = "OK"
        message = "command completed"
    return ExternalToolResult(
        name,
        status,
        required,
        command,
        cwd,
        completed.returncode,
        stdout_log,
        stderr_log,
        success_artifacts,
        message,
    )


def _overall_status(results: list[ExternalToolResult]) -> str:
    if any(result.status == "FAILED" for result in results):
        return "FAILED"
    if any(result.status in {"WARN", "SKIPPED"} for result in results):
        return "WARN"
    return "OK"


def run_external_tool_validation(
    *,
    profile_yml: Path | str = "external_validation/tool_profiles.yml",
    out_dir: Path | str,
    tools: list[str] | str | None = None,
    downstream_dir: Path | str | None = None,
    execute: bool = False,
) -> ExternalValidationResult:
    profile_path = Path(profile_yml)
    out_path = Path(out_dir)
    downstream_path = Path(downstream_dir) if downstream_dir else out_path.parent / "downstream_smoke"
    obj = _load_yaml(profile_path)
    profiles = obj.get("profiles") or {}
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError(f"No profiles found in {profile_path}")
    selected = _parse_tools(tools, sorted(profiles))
    variables = {
        "out_dir": str(out_path),
        "downstream_dir": str(downstream_path),
        "repo_root": str(Path.cwd()),
    }
    results = [
        _run_profile(name=name, profile=profiles[name] or {}, out_dir=out_path, variables=variables, execute=execute)
        for name in selected
    ]
    status = _overall_status(results)
    manifest = out_path / "EXTERNAL_TOOL_VALIDATION.yml"
    _write_yaml(
        manifest,
        {
            "purpose": "external_tool_validation",
            "status": status,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "execute": execute,
            "profile_yml": str(profile_path),
            "downstream_dir": str(downstream_path),
            "tools": [_result_payload(result) for result in results],
            "notes": [
                "External tools and licenses are not bundled in this repository.",
                "SKIPPED means the profile is configured but executable was not available in this environment.",
                "Use --execute only in a validated local or controlled external tool environment.",
            ],
        },
    )
    return ExternalValidationResult(out_path, status, execute, results, manifest)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-yml", type=Path, default=Path("external_validation/tool_profiles.yml"))
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--downstream-dir", type=Path, default=None)
    parser.add_argument("--tools", default=None, help="Comma-separated profile names. Defaults to all profiles.")
    parser.add_argument("--execute", action="store_true", help="Actually run external commands. Default only probes availability.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = run_external_tool_validation(
            profile_yml=args.profile_yml,
            out_dir=args.out_dir,
            downstream_dir=args.downstream_dir,
            tools=args.tools,
            execute=args.execute,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"External tool validation: {result.status}")
    print(f"execute={str(result.execute).lower()}")
    print(f"manifest: {result.manifest}")
    for item in result.results:
        print(f"{item.name}: {item.status} - {item.message}")
    return 1 if result.status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
