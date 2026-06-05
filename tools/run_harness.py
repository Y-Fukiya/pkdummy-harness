#!/usr/bin/env python3
"""Run the PK fixture harness from a single YAML configuration file.

This is the cloud/local friendly entrypoint. It dispatches to existing tools:
- demo_set: generate demo sim_full.csv files and run each workflow
- post_simulation: run the deterministic workflow for an existing sim_full.csv

It does not modify pk.yml, targets.yml, or spec files.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.run_demo_set import run_demo_set
from tools.run_workflow import run_workflow


@dataclass(frozen=True)
class HarnessResult:
    out_dir: Path
    mode: str
    status: str
    files: dict[str, Path]
    warnings: list[str]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_yaml(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _as_path(value: Any, *, label: str) -> Path:
    if value is None or str(value).strip() == "":
        raise ValueError(f"Missing required config value: {label}")
    return Path(str(value))


def _times(config: dict[str, Any]) -> list[float] | None:
    sampling = config.get("sampling") or {}
    raw = sampling.get("times_h")
    if raw is None:
        return None
    if not isinstance(raw, list) or not raw:
        raise ValueError("sampling.times_h must be a non-empty list of hours.")
    try:
        return [float(value) for value in raw]
    except (TypeError, ValueError) as exc:
        raise ValueError("sampling.times_h must contain numeric hours.") from exc


def _manifest_common(
    *,
    config_path: Path,
    mode: str,
    status: str,
    warnings: list[str],
    outputs: dict[str, Path],
    extra: dict[str, Any],
) -> dict[str, Any]:
    return {
        "purpose": "pk_fixture_harness_entrypoint",
        "mode": mode,
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "config_yml": str(config_path),
        "outputs": {key: str(value) for key, value in outputs.items()},
        "warnings": warnings,
        "safeguards": [
            "run_harness.py dispatches existing tools and does not modify pk.yml, targets.yml, or spec files.",
            "Simulation engines are explicit in config; analytical_demo is for workflow smoke demos, not mrgsolve replacement.",
            "Canonical PK updates remain in the harvest/review path, never in the workflow runner.",
        ],
        **extra,
    }


def _status_payload(
    *,
    mode: str,
    status: str,
    out_dir: Path,
    warnings: list[str],
    outputs: dict[str, Path],
    counts: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema": "pk_fixture_harness_status_v0.1",
        "mode": mode,
        "status": status,
        "out_dir": str(out_dir),
        "warnings_n": len(warnings),
        "warnings": warnings,
        "outputs": {key: str(value) for key, value in outputs.items()},
        "counts": counts,
        "safeguards": [
            "Do not present generated files as clinical validation outputs.",
            "Do not update pk.yml, targets.yml, or spec files from launcher/UI code.",
            "Treat WARN/FAILED as workflow fixture status, not clinical correctness.",
        ],
    }
    if extra:
        payload.update(extra)
    return payload


def _run_demo_set_mode(config: dict[str, Any], *, config_path: Path) -> HarnessResult:
    out_dir = _as_path(config.get("out_dir"), label="out_dir")
    manifest = out_dir / "HARNESS_MANIFEST.yml"
    status_json = out_dir / "HARNESS_STATUS.json"
    simulation = config.get("simulation") or {}
    engine = str(simulation.get("engine") or "analytical_demo")
    if engine != "analytical_demo":
        raise ValueError("demo_set currently supports only simulation.engine: analytical_demo")
    drugs = config.get("drugs")
    if not isinstance(drugs, list) or not drugs:
        raise ValueError("demo_set mode requires a non-empty drugs list.")
    result = run_demo_set(
        drugs=[str(drug) for drug in drugs],
        drugs_dir=_as_path(config.get("drugs_dir", "drugs"), label="drugs_dir"),
        out_dir=out_dir,
        sample_times_h=_times(config),
        allow_validation_failed=bool((config.get("validation") or {}).get("allow_failed", True)),
    )
    files = {
        "manifest": manifest,
        "status_json": status_json,
        "demo_manifest": result.files["manifest"],
        "summary_csv": result.files["summary_csv"],
        "summary_md": result.files["summary_md"],
    }
    _write_yaml(
        manifest,
        _manifest_common(
            config_path=config_path,
            mode="demo_set",
            status=result.status,
            warnings=result.warnings,
            outputs=files,
            extra={
                "simulation_engine": engine,
                "drugs": [str(drug) for drug in drugs],
                "counts": result.counts,
            },
        ),
    )
    _write_json(
        status_json,
        _status_payload(
            mode="demo_set",
            status=result.status,
            out_dir=out_dir,
            warnings=result.warnings,
            outputs=files,
            counts=result.counts,
            extra={
                "simulation_engine": engine,
                "drugs": [str(drug) for drug in drugs],
            },
        ),
    )
    return HarnessResult(
        out_dir=out_dir,
        mode="demo_set",
        status=result.status,
        files=files,
        warnings=result.warnings,
    )


def _run_post_simulation_mode(config: dict[str, Any], *, config_path: Path) -> HarnessResult:
    out_dir = _as_path(config.get("out_dir"), label="out_dir")
    manifest = out_dir / "HARNESS_MANIFEST.yml"
    status_json = out_dir / "HARNESS_STATUS.json"
    inputs = config.get("inputs") or {}
    validation = config.get("validation") or {}
    existing_domains = config.get("existing_domains") or {}
    result = run_workflow(
        sim_full_csv=_as_path(inputs.get("sim_full_csv"), label="inputs.sim_full_csv"),
        out_dir=out_dir,
        pk_yml=inputs.get("pk_yml"),
        targets_yml=inputs.get("targets_yml"),
        spec_yml=inputs.get("spec_yml"),
        drug=inputs.get("drug"),
        drugs_dir=inputs.get("drugs_dir", config.get("drugs_dir", "drugs")),
        subjects_csv=inputs.get("subjects_csv"),
        dm_csv=existing_domains.get("dm_csv"),
        vs_csv=existing_domains.get("vs_csv"),
        lb_csv=existing_domains.get("lb_csv"),
        ex_csv=existing_domains.get("ex_csv"),
        pc_csv=existing_domains.get("pc_csv"),
        times_h=_times(config),
        schedule_csv=(config.get("sampling") or {}).get("schedule_csv"),
        method=str((config.get("sampling") or {}).get("method", "linear")),  # type: ignore[arg-type]
        jitter_min=float((config.get("sampling") or {}).get("jitter_min", 0.0)),
        seed=int(config.get("seed", 20260217)),
        strict_subject_match=bool(config.get("strict_subject_match", False)),
        overwrite_existing_pc_conc=bool(config.get("overwrite_existing_pc_conc", False)),
        max_validation_loops=int(validation.get("max_loops", 3)),
        warn_rel=float(validation.get("warn_rel", 0.25)),
        fail_rel=float(validation.get("fail_rel", 0.50)),
        allow_validation_failed=bool(validation.get("allow_failed", False)),
    )
    files = {
        "manifest": manifest,
        "status_json": status_json,
        "workflow_manifest": result.files["manifest"],
        "simulation_validation_md": result.files["simulation_validation_md"],
    }
    if "adpc_csv" in result.files:
        files["adpc_csv"] = result.files["adpc_csv"]
    if "nca_input_csv" in result.files:
        files["nca_input_csv"] = result.files["nca_input_csv"]
    if "poppk_input_csv" in result.files:
        files["poppk_input_csv"] = result.files["poppk_input_csv"]
    _write_yaml(
        manifest,
        _manifest_common(
            config_path=config_path,
            mode="post_simulation",
            status=result.status,
            warnings=result.warnings,
            outputs=files,
            extra={
                "validation_status": result.validation_status,
                "counts": result.counts,
            },
        ),
    )
    _write_json(
        status_json,
        _status_payload(
            mode="post_simulation",
            status=result.status,
            out_dir=out_dir,
            warnings=result.warnings,
            outputs=files,
            counts=result.counts,
            extra={
                "validation_status": result.validation_status,
            },
        ),
    )
    return HarnessResult(
        out_dir=out_dir,
        mode="post_simulation",
        status=result.status,
        files=files,
        warnings=result.warnings,
    )


def run_harness(config_yml: Path | str) -> HarnessResult:
    config_path = Path(config_yml)
    config = _load_yaml(config_path)
    mode = str(config.get("mode") or "").strip()
    if mode == "demo_set":
        return _run_demo_set_mode(config, config_path=config_path)
    if mode == "post_simulation":
        return _run_post_simulation_mode(config, config_path=config_path)
    raise ValueError("config.mode must be one of: demo_set, post_simulation")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config_yml", type=Path, help="Harness YAML config")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = run_harness(args.config_yml)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Harness: {result.status}")
    print(f"Mode: {result.mode}")
    print(f"Output directory: {result.out_dir}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for key in sorted(result.files):
        print(f"{key}: {result.files[key]}")
    return 1 if result.status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
