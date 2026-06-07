#!/usr/bin/env python3
"""Validate YAML configuration for tools/run_harness.py.

This intentionally uses lightweight hand-written checks instead of a JSON Schema
dependency so the harness remains easy to run in constrained environments.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_non_negative_number(value: Any) -> bool:
    try:
        return float(value) >= 0
    except (TypeError, ValueError):
        return False


def _is_positive_int(value: Any) -> bool:
    try:
        return int(value) > 0
    except (TypeError, ValueError):
        return False


def _validate_sampling(config: dict[str, Any], issues: list[str]) -> None:
    sampling = config.get("sampling") or {}
    if not isinstance(sampling, dict):
        issues.append("sampling must be a mapping")
        return
    has_times = sampling.get("times_h") is not None
    has_schedule = sampling.get("schedule_csv") is not None
    if not has_times and not has_schedule:
        issues.append("sampling.times_h or sampling.schedule_csv is required")
    if has_times:
        times = sampling.get("times_h")
        if not isinstance(times, list) or not times:
            issues.append("sampling.times_h must be a non-empty list")
        else:
            for value in times:
                try:
                    float(value)
                except (TypeError, ValueError):
                    issues.append("sampling.times_h must contain only numeric values")
                    break
    method = sampling.get("method")
    if method is not None and str(method) not in {"linear", "exact", "nearest"}:
        issues.append("sampling.method must be one of: linear, exact, nearest")


def _validate_validation(config: dict[str, Any], issues: list[str]) -> None:
    validation = config.get("validation") or {}
    if not isinstance(validation, dict):
        issues.append("validation must be a mapping")
        return
    if "max_loops" in validation and not _is_positive_int(validation["max_loops"]):
        issues.append("validation.max_loops must be a positive integer")
    for key in ("warn_rel", "fail_rel"):
        if key in validation and not _is_non_negative_number(validation[key]):
            issues.append(f"validation.{key} must be a non-negative number")


def _validate_variability(simulation: dict[str, Any], issues: list[str]) -> None:
    variability = simulation.get("variability")
    if variability is None:
        return
    if not isinstance(variability, dict):
        issues.append("simulation.variability must be a mapping")
        return
    for key in ("iiv_cv", "residual_cv"):
        if key in variability and not _is_non_negative_number(variability[key]):
            issues.append(f"simulation.variability.{key} must be a non-negative number")
    if "seed" in variability:
        try:
            int(variability["seed"])
        except (TypeError, ValueError):
            issues.append("simulation.variability.seed must be an integer")


def _validate_demo_set(config: dict[str, Any], issues: list[str]) -> None:
    drugs = config.get("drugs")
    if not isinstance(drugs, list) or not drugs:
        issues.append("drugs must be a non-empty list")
    elif any(not _is_non_empty_string(str(drug)) for drug in drugs):
        issues.append("drugs must contain non-empty drug slugs")
    simulation = config.get("simulation") or {}
    if not isinstance(simulation, dict):
        issues.append("simulation must be a mapping")
        return
    engine = simulation.get("engine", "analytical_demo")
    if engine != "analytical_demo":
        issues.append("simulation.engine must be analytical_demo for demo_set mode")
    _validate_variability(simulation, issues)


def _validate_post_simulation(config: dict[str, Any], issues: list[str]) -> None:
    inputs = config.get("inputs") or {}
    if not isinstance(inputs, dict):
        issues.append("inputs must be a mapping")
        return
    if not _is_non_empty_string(str(inputs.get("sim_full_csv") or "")):
        issues.append("inputs.sim_full_csv is required for post_simulation mode")
    has_drug = _is_non_empty_string(str(inputs.get("drug") or ""))
    has_explicit_pk = all(_is_non_empty_string(str(inputs.get(key) or "")) for key in ("pk_yml", "targets_yml", "spec_yml"))
    if not has_drug and not has_explicit_pk:
        issues.append("Provide either inputs.drug or all of inputs.pk_yml, inputs.targets_yml, inputs.spec_yml")
    existing_domains = config.get("existing_domains")
    if existing_domains is not None and not isinstance(existing_domains, dict):
        issues.append("existing_domains must be a mapping")


def validate_harness_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not isinstance(config, dict):
        return ["config must be a YAML mapping"]
    if "version" in config and str(config["version"]) != "0.1":
        issues.append("version must be 0.1 when provided")
    if not _is_non_empty_string(str(config.get("out_dir") or "")):
        issues.append("out_dir is required")

    mode = str(config.get("mode") or "").strip()
    if mode not in {"demo_set", "post_simulation"}:
        issues.append("mode must be one of: demo_set, post_simulation")
    elif mode == "demo_set":
        _validate_demo_set(config, issues)
    else:
        _validate_post_simulation(config, issues)

    _validate_sampling(config, issues)
    _validate_validation(config, issues)
    return issues


def validate_harness_config_file(path: Path | str) -> list[str]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return validate_harness_config(config)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config_yml", type=Path, help="Harness YAML config")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        issues = validate_harness_config_file(args.config_yml)
    except Exception as exc:
        print(f"Harness config validation: FAILED")
        print(f"- {exc}")
        return 1
    if issues:
        print("Harness config validation: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Harness config validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
