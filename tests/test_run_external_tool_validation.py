from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from tools.run_external_tool_validation import run_external_tool_validation


ROOT = Path(__file__).resolve().parents[1]


def write_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")


def test_run_external_tool_validation_executes_available_profile(tmp_path: Path) -> None:
    profile_yml = tmp_path / "profiles.yml"
    out_dir = tmp_path / "external_validation"
    write_yaml(
        profile_yml,
        {
            "profiles": {
                "fake_tool": {
                    "required": True,
                    "command": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('fake_tool.ok').write_text('ok', encoding='utf-8')",
                    ],
                    "success_artifacts": ["fake_tool.ok"],
                    "description": "fake external validation tool",
                }
            }
        },
    )

    result = run_external_tool_validation(profile_yml=profile_yml, out_dir=out_dir, tools=["fake_tool"], execute=True)

    assert result.status == "OK"
    assert result.results[0].status == "OK"
    assert (out_dir / "fake_tool" / "fake_tool.ok").read_text(encoding="utf-8") == "ok"
    manifest = yaml.safe_load((out_dir / "EXTERNAL_TOOL_VALIDATION.yml").read_text(encoding="utf-8"))
    assert manifest["purpose"] == "external_tool_validation"
    assert manifest["tools"][0]["status"] == "OK"


def test_run_external_tool_validation_skips_unavailable_optional_profile(tmp_path: Path) -> None:
    profile_yml = tmp_path / "profiles.yml"
    out_dir = tmp_path / "external_validation"
    write_yaml(
        profile_yml,
        {
            "profiles": {
                "missing_tool": {
                    "required": False,
                    "command": ["definitely-not-installed-pk-fixture-tool", "--version"],
                    "success_artifacts": [],
                    "description": "optional missing external validation tool",
                }
            }
        },
    )

    result = run_external_tool_validation(profile_yml=profile_yml, out_dir=out_dir, tools=["missing_tool"], execute=True)

    assert result.status == "WARN"
    assert result.results[0].status == "SKIPPED"
    assert "not found" in result.results[0].message


def test_run_external_tool_validation_cli_probe_mode(tmp_path: Path) -> None:
    profile_yml = tmp_path / "profiles.yml"
    out_dir = tmp_path / "external_validation"
    write_yaml(
        profile_yml,
        {
            "profiles": {
                "fake_probe": {
                    "required": False,
                    "command": [sys.executable, "-c", "print('probe')"],
                    "success_artifacts": [],
                }
            }
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            "tools/run_external_tool_validation.py",
            "--profile-yml",
            str(profile_yml),
            "--out-dir",
            str(out_dir),
            "--tools",
            "fake_probe",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "External tool validation: OK" in completed.stdout
    assert "execute=false" in completed.stdout
