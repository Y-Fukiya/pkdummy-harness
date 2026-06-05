#!/usr/bin/env python3
"""Validate generated PK simulation data against pk.yml and targets.yml.

This is a simulation-output sanity check. It recalculates subject-level
AUC0-inf, Cmax, Tmax, and terminal half-life from concentration-time rows,
then compares central summaries with targets and source-derived expectations.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


CONC_COLUMNS = ["CP", "IPRED", "DV", "CONC"]


@dataclass(frozen=True)
class SubjectMetrics:
    subject_id: str
    n_points: int
    auc0_last: float
    auc0_inf: float
    cmax: float
    tmax_h: float
    terminal_ke_1_per_h: float | None
    half_life_h: float | None


@dataclass(frozen=True)
class SimulationTolerances:
    warn_rel: float = 0.25
    fail_rel: float = 0.50
    terminal_points: int = 3


@dataclass(frozen=True)
class Comparison:
    label: str
    observed: float
    expected: float
    rel_error: float
    unit: str
    status: str


@dataclass(frozen=True)
class ValidationResult:
    status: str
    summary: dict[str, Any]
    comparisons: list[Comparison]
    warnings: list[str]
    failures: list[str]
    subject_metrics: dict[str, SubjectMetrics]


@dataclass(frozen=True)
class ValidationLoopResult:
    max_loops: int
    attempts: list[ValidationResult]

    @property
    def final_result(self) -> ValidationResult:
        return self.attempts[-1]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"NA", "NAN", "NULL"}:
        return None
    try:
        x = float(text)
    except ValueError:
        return None
    if not math.isfinite(x):
        return None
    return x


def _is_observation(row: dict[str, Any]) -> bool:
    evid = _to_float(row.get("evid") if "evid" in row else row.get("EVID"))
    if evid is not None and evid != 0:
        return False
    mdv = _to_float(row.get("MDV") if "MDV" in row else row.get("mdv"))
    if mdv is not None and mdv == 1 and evid is None:
        return False
    return True


def _concentration(row: dict[str, Any]) -> float | None:
    for col in CONC_COLUMNS:
        if col in row:
            value = _to_float(row.get(col))
            if value is not None:
                return value
    return None


def _time(row: dict[str, Any]) -> float | None:
    return _to_float(row.get("time") if "time" in row else row.get("TIME"))


def _subject_id(row: dict[str, Any]) -> str:
    value = row.get("ID") if "ID" in row else row.get("id")
    return str(value or "").strip()


def _deduplicate_points(points: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    by_time: dict[float, float] = {}
    for time_h, conc in points:
        by_time[time_h] = conc
    return sorted(by_time.items())


def _terminal_ke(points: list[tuple[float, float]], terminal_points: int) -> float | None:
    positive = [(t, c) for t, c in points if c > 0]
    if len(positive) < terminal_points:
        return None
    tail = positive[-terminal_points:]
    times = [p[0] for p in tail]
    logs = [math.log(p[1]) for p in tail]
    mean_t = sum(times) / len(times)
    mean_log = sum(logs) / len(logs)
    denom = sum((t - mean_t) ** 2 for t in times)
    if denom <= 0:
        return None
    slope = sum((t - mean_t) * (y - mean_log) for t, y in zip(times, logs)) / denom
    if slope >= 0:
        return None
    return -slope


def _auc_linear(points: list[tuple[float, float]]) -> float:
    auc = 0.0
    for (t0, c0), (t1, c1) in zip(points, points[1:]):
        dt = t1 - t0
        if dt > 0:
            auc += 0.5 * (c0 + c1) * dt
    return auc


def compute_subject_metrics(
    rows: list[dict[str, Any]],
    *,
    tolerances: SimulationTolerances | None = None,
) -> dict[str, SubjectMetrics]:
    tolerances = tolerances or SimulationTolerances()
    grouped: dict[str, list[tuple[float, float]]] = {}
    for row in rows:
        if not _is_observation(row):
            continue
        sid = _subject_id(row)
        time_h = _time(row)
        conc = _concentration(row)
        if not sid or time_h is None or conc is None:
            continue
        if conc < 0:
            continue
        grouped.setdefault(sid, []).append((time_h, conc))

    metrics: dict[str, SubjectMetrics] = {}
    for sid, raw_points in grouped.items():
        points = _deduplicate_points(raw_points)
        if len(points) < 2:
            continue
        auc0_last = _auc_linear(points)
        ke = _terminal_ke(points, tolerances.terminal_points)
        last_conc = points[-1][1]
        auc0_inf = auc0_last + (last_conc / ke if ke and last_conc > 0 else 0.0)
        cmax_time, cmax = max(points, key=lambda p: p[1])
        half_life = math.log(2.0) / ke if ke and ke > 0 else None
        metrics[sid] = SubjectMetrics(
            subject_id=sid,
            n_points=len(points),
            auc0_last=auc0_last,
            auc0_inf=auc0_inf,
            cmax=cmax,
            tmax_h=cmax_time,
            terminal_ke_1_per_h=ke,
            half_life_h=half_life,
        )
    return metrics


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _geomean(values: list[float]) -> float | None:
    positive = [v for v in values if v > 0]
    if not positive:
        return None
    return math.exp(sum(math.log(v) for v in positive) / len(positive))


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def summarize_metrics(metrics: dict[str, SubjectMetrics]) -> dict[str, Any]:
    aucs = [m.auc0_inf for m in metrics.values()]
    cmax = [m.cmax for m in metrics.values()]
    tmax = [m.tmax_h for m in metrics.values()]
    half_lives = [m.half_life_h for m in metrics.values() if m.half_life_h is not None]
    return {
        "n_subjects": len(metrics),
        "auc0_inf_mean": _mean(aucs),
        "auc0_inf_geomean": _geomean(aucs),
        "auc0_inf_median": _median(aucs),
        "cmax_mean": _mean(cmax),
        "cmax_geomean": _geomean(cmax),
        "cmax_median": _median(cmax),
        "tmax_h_mean": _mean(tmax),
        "tmax_h_median": _median(tmax),
        "half_life_h_mean": _mean(half_lives),
        "half_life_h_median": _median(half_lives),
    }


def _relative_error(observed: float, expected: float) -> float:
    if expected == 0:
        return abs(observed - expected)
    return abs(observed - expected) / abs(expected)


def _status_for_error(rel_error: float, tolerances: SimulationTolerances) -> str:
    if rel_error > tolerances.fail_rel:
        return "FAIL"
    if rel_error > tolerances.warn_rel:
        return "WARN"
    return "OK"


def _add_comparison(
    comparisons: list[Comparison],
    warnings: list[str],
    failures: list[str],
    *,
    label: str,
    observed: float | None,
    expected: Any,
    unit: str,
    tolerances: SimulationTolerances,
) -> None:
    exp = _to_float(expected)
    if observed is None or exp is None:
        return
    rel_error = _relative_error(float(observed), float(exp))
    status = _status_for_error(rel_error, tolerances)
    comparison = Comparison(label, float(observed), float(exp), rel_error, unit, status)
    comparisons.append(comparison)
    msg = (
        f"{label}: observed={comparison.observed:g} {unit}, "
        f"expected={comparison.expected:g} {unit}, rel_error={comparison.rel_error:.3g}"
    )
    if status == "FAIL":
        failures.append(msg)
    elif status == "WARN":
        warnings.append(msg)


def _target_observed(summary: dict[str, Any], metric: str, target: dict[str, Any]) -> float | None:
    summary_name = str(target.get("summary") or "").strip().lower()
    if metric == "auc":
        if summary_name == "arithmetic_mean":
            return summary.get("auc0_inf_mean")
        if summary_name == "median":
            return summary.get("auc0_inf_median")
        return summary.get("auc0_inf_geomean")
    if metric == "cmax":
        if summary_name == "arithmetic_mean":
            return summary.get("cmax_mean")
        if summary_name == "median":
            return summary.get("cmax_median")
        return summary.get("cmax_geomean")
    if metric == "tmax":
        if summary_name == "median":
            return summary.get("tmax_h_median")
        return summary.get("tmax_h_mean")
    if metric == "t_half":
        if summary_name == "median":
            return summary.get("half_life_h_median")
        return summary.get("half_life_h_mean")
    return None


def _dose_mg(targets: dict[str, Any], rows: list[dict[str, str]]) -> float | None:
    dose = (((targets.get("scenario") or {}).get("dose") or {}).get("value"))
    value = _to_float(dose)
    if value is not None:
        return value
    for row in rows:
        value = _to_float(row.get("DOSE_MG") if "DOSE_MG" in row else row.get("dose_mg"))
        if value is not None and value > 0:
            return value
    return None


def validate_simulation(
    sim_csv: Path,
    pk_yml: Path,
    targets_yml: Path,
    *,
    tolerances: SimulationTolerances | None = None,
) -> ValidationResult:
    tolerances = tolerances or SimulationTolerances()
    rows = read_csv_rows(sim_csv)
    pk = load_yaml(pk_yml)
    targets = load_yaml(targets_yml)
    subject_metrics = compute_subject_metrics(rows, tolerances=tolerances)
    summary = summarize_metrics(subject_metrics)
    comparisons: list[Comparison] = []
    warnings: list[str] = []
    failures: list[str] = []

    if not subject_metrics:
        failures.append("no usable observation concentration rows found")

    target_map = targets.get("targets") or {}
    target_specs = [
        ("targets.auc", "auc", "ng*h/mL"),
        ("targets.cmax", "cmax", "ng/mL"),
        ("targets.tmax", "tmax", "h"),
        ("targets.t_half", "t_half", "h"),
    ]
    for label, metric, unit in target_specs:
        target = target_map.get(metric if metric != "t_half" else "t_half") or {}
        if target:
            _add_comparison(
                comparisons,
                warnings,
                failures,
                label=label,
                observed=_target_observed(summary, metric, target),
                expected=target.get("value"),
                unit=str(target.get("unit") or unit),
                tolerances=tolerances,
            )

    parsed = pk.get("pk_parsed") or {}
    derived = pk.get("derived") or {}
    _add_comparison(
        comparisons,
        warnings,
        failures,
        label="pk_parsed.half_life_h",
        observed=summary.get("half_life_h_mean"),
        expected=parsed.get("half_life_h"),
        unit="h",
        tolerances=tolerances,
    )
    ke = _to_float(derived.get("ke_1_per_h"))
    if ke and ke > 0:
        _add_comparison(
            comparisons,
            warnings,
            failures,
            label="derived.ke_1_per_h implied half-life",
            observed=summary.get("half_life_h_mean"),
            expected=math.log(2.0) / ke,
            unit="h",
            tolerances=tolerances,
        )
    dose = _dose_mg(targets, rows)
    cl_abs = _to_float(derived.get("CL_abs_L_per_h_at_70kg"))
    if dose and cl_abs and cl_abs > 0:
        _add_comparison(
            comparisons,
            warnings,
            failures,
            label="derived.CL_abs implied AUC",
            observed=summary.get("auc0_inf_geomean"),
            expected=dose * 1000.0 / cl_abs,
            unit="ng*h/mL",
            tolerances=tolerances,
        )

    status = "FAILED" if failures else "WARN" if warnings else "OK"
    return ValidationResult(status, summary, comparisons, warnings, failures, subject_metrics)


def validate_simulation_loop(
    sim_csv: Path,
    pk_yml: Path,
    targets_yml: Path,
    *,
    tolerances: SimulationTolerances | None = None,
    max_loops: int = 3,
) -> ValidationLoopResult:
    if max_loops < 1:
        raise ValueError("max_loops must be >= 1")

    attempts: list[ValidationResult] = []
    for _ in range(max_loops):
        result = validate_simulation(sim_csv, pk_yml, targets_yml, tolerances=tolerances)
        attempts.append(result)
        if result.status == "OK":
            break
    return ValidationLoopResult(max_loops=max_loops, attempts=attempts)


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def render_markdown(
    result: ValidationResult,
    sim_csv: Path,
    pk_yml: Path,
    targets_yml: Path,
    *,
    loop: ValidationLoopResult | None = None,
) -> str:
    lines = [
        "# Simulation validation",
        "",
        f"- Status: `{result.status}`",
        f"- Simulation CSV: `{sim_csv}`",
        f"- pk.yml: `{pk_yml}`",
        f"- targets.yml: `{targets_yml}`",
        f"- Validation attempts: `{len(loop.attempts) if loop else 1}` / `{loop.max_loops if loop else 1}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Subjects | {_fmt(result.summary.get('n_subjects'))} |",
        f"| AUC0-inf geometric mean | {_fmt(result.summary.get('auc0_inf_geomean'))} ng*h/mL |",
        f"| AUC0-inf arithmetic mean | {_fmt(result.summary.get('auc0_inf_mean'))} ng*h/mL |",
        f"| Cmax geometric mean | {_fmt(result.summary.get('cmax_geomean'))} ng/mL |",
        f"| Tmax mean | {_fmt(result.summary.get('tmax_h_mean'))} h |",
        f"| Terminal half-life mean | {_fmt(result.summary.get('half_life_h_mean'))} h |",
        "",
        "## Comparisons",
        "",
        "| Check | Observed | Expected | Relative error | Status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    if result.comparisons:
        for comp in result.comparisons:
            lines.append(
                f"| {comp.label} | {_fmt(comp.observed)} {comp.unit} | "
                f"{_fmt(comp.expected)} {comp.unit} | {_fmt(comp.rel_error)} | {comp.status} |"
            )
    else:
        lines.append("| No comparable targets found | NA | NA | NA | NA |")

    if result.failures:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in result.failures)
    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result.warnings)
    if loop and len(loop.attempts) > 1:
        lines.extend(["", "## Loop History", ""])
        lines.extend(
            f"- Attempt {idx}: `{attempt.status}`"
            for idx, attempt in enumerate(loop.attempts, start=1)
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sim_csv", type=Path, help="raw/sim_full.csv from a simulation run")
    parser.add_argument("--pk", required=True, type=Path, help="drug pk.yml")
    parser.add_argument("--targets", required=True, type=Path, help="drug targets.yml")
    parser.add_argument("--out-md", type=Path, default=None, help="optional markdown report path")
    parser.add_argument("--warn-rel", type=float, default=0.25, help="relative error threshold for warnings")
    parser.add_argument("--fail-rel", type=float, default=0.50, help="relative error threshold for failures")
    parser.add_argument("--max-loops", type=int, default=3, help="max validation attempts when WARN/FAILED is returned")
    args = parser.parse_args(argv)

    loop = validate_simulation_loop(
        args.sim_csv,
        args.pk,
        args.targets,
        tolerances=SimulationTolerances(warn_rel=args.warn_rel, fail_rel=args.fail_rel),
        max_loops=args.max_loops,
    )
    result = loop.final_result
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(render_markdown(result, args.sim_csv, args.pk, args.targets, loop=loop), encoding="utf-8")

    print(f"Simulation validation: {result.status}")
    print(f"Validation attempts: {len(loop.attempts)}/{loop.max_loops}")
    if len(loop.attempts) > 1:
        for idx, attempt in enumerate(loop.attempts, start=1):
            print(f"- Attempt {idx}: {attempt.status}")
    for failure in result.failures:
        print(f"- FAIL: {failure}")
    for warning in result.warnings:
        print(f"- WARN: {warning}")
    return 1 if result.status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
