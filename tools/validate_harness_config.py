#!/usr/bin/env python3
"""Validate YAML configuration for tools/run_harness.py.

This intentionally uses lightweight hand-written checks instead of a JSON Schema
dependency so the harness remains easy to run in constrained environments.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import yaml


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_non_negative_number(value: Any) -> bool:
    try:
        parsed = float(value)
        return math.isfinite(parsed) and parsed >= 0
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
            parsed_times: list[float] = []
            for value in times:
                try:
                    parsed = float(value)
                    if not math.isfinite(parsed) or parsed < 0:
                        raise ValueError
                    parsed_times.append(parsed)
                except (TypeError, ValueError):
                    issues.append("sampling.times_h must contain finite non-negative numeric values")
                    break
            if len(parsed_times) == len(times) and len(set(parsed_times)) != len(parsed_times):
                issues.append("sampling.times_h must not contain duplicate times")
    method = sampling.get("method")
    if method is not None and str(method) not in {"linear", "log-linear", "exact", "nearest"}:
        issues.append("sampling.method must be one of: linear, log-linear, exact, nearest")


def _validate_validation(config: dict[str, Any], issues: list[str]) -> None:
    validation = config.get("validation") or {}
    if not isinstance(validation, dict):
        issues.append("validation must be a mapping")
        return
    if "max_loops" in validation:
        issues.append("validation.max_loops is no longer supported; validation is a single deterministic check")
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
        except (TypeError, ValueError, OverflowError):
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
    if "n_subjects" in simulation:
        value = simulation["n_subjects"]
        try:
            parsed = int(value)
            if isinstance(value, bool) or float(value) != parsed or parsed < 1:
                raise ValueError
        except (TypeError, ValueError, OverflowError):
            issues.append("simulation.n_subjects must be a positive integer")
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


def _validate_numeric_list(value: Any, label: str, issues: list[str]) -> list[float]:
    if not isinstance(value, list) or not value:
        issues.append(f"{label} must be a non-empty list")
        return []
    parsed: list[float] = []
    for item in value:
        try:
            parsed_value = float(item)
            if not math.isfinite(parsed_value):
                raise ValueError
            parsed.append(parsed_value)
        except (TypeError, ValueError):
            issues.append(f"{label} must contain only numeric values")
            return []
    return parsed


def _validate_repeated_oral_demo(config: dict[str, Any], issues: list[str]) -> None:
    drugs = config.get("drugs")
    if not isinstance(drugs, list) or len(drugs) != 1 or not _is_non_empty_string(str(drugs[0])):
        issues.append("repeated_oral_demo requires exactly one non-empty drug slug")
    simulation = config.get("simulation") or {}
    if not isinstance(simulation, dict):
        issues.append("simulation must be a mapping")
        return
    engine = str(simulation.get("engine", "analytical_demo")).strip().lower()
    if engine not in {"analytical_demo", "mrgsolve"}:
        issues.append("simulation.engine must be analytical_demo or mrgsolve for repeated_oral_demo mode")
    n_subjects = simulation.get("n_subjects")
    try:
        parsed_n = int(n_subjects)
        if isinstance(n_subjects, bool) or float(n_subjects) != parsed_n or parsed_n < 1:
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        issues.append("simulation.n_subjects must be a positive integer")
    t_end_h = float(simulation.get("t_end_h")) if _is_non_negative_number(simulation.get("t_end_h")) else None
    for key in ("t_end_h", "dt_h"):
        if key not in simulation or not _is_non_negative_number(simulation[key]) or float(simulation[key]) <= 0:
            issues.append(f"simulation.{key} must be a positive number")
    dosing = simulation.get("repeated_dosing") or {}
    interval_h: float | None = None
    dose_count: int | None = None
    analysis_dose_number: int | None = None
    if not isinstance(dosing, dict):
        issues.append("simulation.repeated_dosing must be a mapping")
    else:
        if not _is_non_negative_number(dosing.get("interval_h")) or float(dosing.get("interval_h", 0)) <= 0:
            issues.append("simulation.repeated_dosing.interval_h must be positive")
        else:
            interval_h = float(dosing["interval_h"])
        for key in ("dose_count", "analysis_dose_number"):
            value = dosing.get(key)
            try:
                parsed = int(value)
                if isinstance(value, bool) or float(value) != parsed or parsed < 1:
                    raise ValueError
                if key == "dose_count":
                    dose_count = parsed
                else:
                    analysis_dose_number = parsed
            except (TypeError, ValueError, OverflowError):
                issues.append(f"simulation.repeated_dosing.{key} must be a positive integer")
        if dose_count is not None and dose_count < 2:
            issues.append("simulation.repeated_dosing.dose_count must be at least 2")
        if dose_count is not None and analysis_dose_number is not None and not 1 <= analysis_dose_number <= dose_count:
            issues.append("simulation.repeated_dosing.analysis_dose_number must be between 1 and dose_count")
        if interval_h is not None and dose_count is not None and t_end_h is not None:
            last_dose_time = (dose_count - 1) * interval_h
            if t_end_h + 1e-9 < last_dose_time:
                issues.append("simulation.t_end_h must cover the final dose time")
            if analysis_dose_number is not None:
                analysis_time_h = (analysis_dose_number - 1) * interval_h
                nca_interval = config.get("nca") or {}
                interval_values = nca_interval.get("interval_h", [0, interval_h]) if isinstance(nca_interval, dict) else [0, interval_h]
                try:
                    nca_end = float(interval_values[1])
                    if t_end_h + 1e-9 < analysis_time_h + nca_end:
                        issues.append("simulation.t_end_h must cover the full final analysis interval")
                except (TypeError, ValueError, IndexError):
                    pass
    variability = simulation.get("variability")
    if variability is not None:
        _validate_variability(simulation, issues)

    sampling = config.get("sampling") or {}
    if not isinstance(sampling, dict):
        issues.append("sampling must be a mapping")
    else:
        trough = _validate_numeric_list(sampling.get("trough_times_h"), "sampling.trough_times_h", issues)
        ss = _validate_numeric_list(sampling.get("ss_times_after_dose_h"), "sampling.ss_times_after_dose_h", issues)
        if trough and any(value < 0 for value in trough):
            issues.append("sampling.trough_times_h must be non-negative")
        if trough and len(set(trough)) != len(trough):
            issues.append("sampling.trough_times_h must not contain duplicate times")
        if trough and not {120.0, 144.0}.issubset(set(trough)):
            issues.append("sampling.trough_times_h must include 120 and 144 h for predicted stability QC")
        if ss and any(value < 0 for value in ss):
            issues.append("sampling.ss_times_after_dose_h must be non-negative")
        if ss and len(set(ss)) != len(ss):
            issues.append("sampling.ss_times_after_dose_h must not contain duplicate times")
        if ss and interval_h is not None and (min(ss) != 0 or max(ss) != interval_h or any(value > interval_h for value in ss)):
            issues.append("sampling.ss_times_after_dose_h must start at 0, end at interval_h, and stay within the interval")
        if sampling.get("method", "exact") != "exact":
            issues.append("sampling.method must be exact for repeated_oral_demo mode")

    nca = config.get("nca") or {}
    if not isinstance(nca, dict):
        issues.append("nca must be a mapping")
    else:
        if nca.get("concentration", "DV") != "DV":
            issues.append("nca.concentration must be DV for repeated_oral_demo mode")
        if nca.get("integration", "linear-up-log-down") != "linear-up-log-down":
            issues.append("nca.integration must be linear-up-log-down")
        interval = _validate_numeric_list(nca.get("interval_h", [0, 12]), "nca.interval_h", issues)
        if interval and (len(interval) != 2 or interval[0] != 0 or interval[1] <= interval[0]):
            issues.append("nca.interval_h must be [0, positive_end]")
        if interval and interval_h is not None and len(interval) == 2 and abs(interval[1] - interval_h) > 1e-9:
            issues.append("nca.interval_h end must equal simulation.repeated_dosing.interval_h")
        partials = nca.get("partial_intervals_h", [[0, 4], [4, 12]])
        if not isinstance(partials, list) or not partials:
            issues.append("nca.partial_intervals_h must be a non-empty list")
        else:
            for index, pair in enumerate(partials):
                if not isinstance(pair, list) or len(pair) != 2:
                    issues.append(f"nca.partial_intervals_h[{index}] must be [start, end]")
                    continue
                try:
                    start = float(pair[0])
                    end = float(pair[1])
                    if (
                        not math.isfinite(start)
                        or not math.isfinite(end)
                        or start < 0
                        or end > (interval[1] if interval and len(interval) == 2 else float("inf"))
                        or end <= start
                    ):
                        raise ValueError
                except (TypeError, ValueError):
                    issues.append(f"nca.partial_intervals_h[{index}] must have end > start")
            if interval and len(interval) == 2:
                try:
                    ordered = sorted((float(pair[0]), float(pair[1])) for pair in partials if isinstance(pair, list) and len(pair) == 2)
                    if not ordered or abs(ordered[0][0] - interval[0]) > 1e-9 or abs(ordered[-1][1] - interval[1]) > 1e-9:
                        issues.append("nca.partial_intervals_h must cover nca.interval_h")
                    if any(abs(ordered[index][1] - ordered[index + 1][0]) > 1e-9 for index in range(len(ordered) - 1)):
                        issues.append("nca.partial_intervals_h must be contiguous and cover nca.interval_h")
                    if ss:
                        ss_sorted = sorted(set(ss))
                        for boundary in {value for pair in ordered for value in pair}:
                            if not any(abs(sample - boundary) <= 1e-9 for sample in ss_sorted):
                                issues.append("nca.partial_intervals_h boundaries must be present in sampling.ss_times_after_dose_h")
                                break
                except (TypeError, ValueError, IndexError):
                    pass


def validate_harness_config(config: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if not isinstance(config, dict):
        return ["config must be a YAML mapping"]
    if "version" in config and str(config["version"]) != "0.1":
        issues.append("version must be 0.1 when provided")
    if not _is_non_empty_string(str(config.get("out_dir") or "")):
        issues.append("out_dir is required")

    mode = str(config.get("mode") or "").strip()
    if mode not in {"demo_set", "post_simulation", "repeated_oral_demo"}:
        issues.append("mode must be one of: demo_set, post_simulation, repeated_oral_demo")
    elif mode == "demo_set":
        _validate_demo_set(config, issues)
    elif mode == "post_simulation":
        _validate_post_simulation(config, issues)
    else:
        _validate_repeated_oral_demo(config, issues)

    if mode != "repeated_oral_demo":
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
        print("Harness config validation: FAILED")
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
