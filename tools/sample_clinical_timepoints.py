#!/usr/bin/env python3
"""Sample dense simulation output at clinical nominal time points.

This is a post-processing tool for workflow dummy data. It does not change the
model or PK parameters. It takes a dense `raw/sim_full.csv` and writes a sparse
CSV with one observation per subject per requested nominal sampling time.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal


Method = Literal["exact", "nearest", "linear"]


@dataclass(frozen=True)
class SchedulePoint:
    nominal_time_h: float
    tpt: str
    tptnum: int


@dataclass(frozen=True)
class SamplingResult:
    out_csv: Path
    n_subjects: int
    n_timepoints: int
    n_rows: int
    method: str


def _to_float(value: object) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_float(value: float) -> str:
    if abs(value) < 1e-12:
        value = 0.0
    return f"{value:.12g}"


def _time_col(fieldnames: Iterable[str]) -> str:
    fields = list(fieldnames)
    if "time" in fields:
        return "time"
    if "TIME" in fields:
        return "TIME"
    raise ValueError("Input CSV must contain a `time` or `TIME` column.")


def _id_col(fieldnames: Iterable[str]) -> str:
    fields = list(fieldnames)
    if "ID" in fields:
        return "ID"
    if "USUBJID" in fields:
        return "USUBJID"
    raise ValueError("Input CSV must contain an `ID` or `USUBJID` column.")


def _evid_value(row: dict[str, str]) -> float:
    value = row.get("evid", row.get("EVID", "0"))
    parsed = _to_float(value)
    return 0.0 if parsed is None else parsed


def _is_observation(row: dict[str, str]) -> bool:
    return _evid_value(row) == 0.0


def _default_tpt(time_h: float) -> str:
    if abs(time_h) < 1e-12:
        return "Pre-dose"
    return f"{_format_float(time_h)} h"


def schedule_from_times(times_h: list[float]) -> list[SchedulePoint]:
    if not times_h:
        raise ValueError("At least one sampling time is required.")
    sorted_times = sorted(times_h)
    return [
        SchedulePoint(nominal_time_h=t, tpt=_default_tpt(t), tptnum=i)
        for i, t in enumerate(sorted_times, start=1)
    ]


def parse_times(value: str) -> list[float]:
    try:
        return [float(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise ValueError(f"Could not parse --times value {value!r}; expected comma-separated hours.") from exc


def load_schedule_csv(path: Path) -> list[SchedulePoint]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Schedule CSV is empty: {path}")
        if "NOMTIME_H" not in reader.fieldnames:
            raise ValueError("Schedule CSV must contain NOMTIME_H.")
        points: list[SchedulePoint] = []
        for i, row in enumerate(reader, start=1):
            nominal = _to_float(row.get("NOMTIME_H"))
            if nominal is None:
                raise ValueError(f"Schedule row {i} has invalid NOMTIME_H: {row.get('NOMTIME_H')!r}")
            tpt = (row.get("TPT") or _default_tpt(nominal)).strip()
            tptnum_raw = row.get("TPTNUM")
            tptnum = int(float(tptnum_raw)) if tptnum_raw not in (None, "") else i
            points.append(SchedulePoint(nominal_time_h=nominal, tpt=tpt, tptnum=tptnum))
    if not points:
        raise ValueError(f"Schedule CSV has no rows: {path}")
    return sorted(points, key=lambda p: (p.nominal_time_h, p.tptnum))


def _read_sim_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Input CSV is empty: {path}")
        return list(reader.fieldnames), list(reader)


def _group_observations(
    rows: list[dict[str, str]],
    *,
    id_col: str,
    time_col: str,
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if not _is_observation(row):
            continue
        time = _to_float(row.get(time_col))
        subject_id = row.get(id_col)
        if time is None or subject_id in (None, ""):
            continue
        grouped.setdefault(str(subject_id), []).append(row)
    for subject_rows in grouped.values():
        subject_rows.sort(key=lambda r: float(r[time_col]))
    if not grouped:
        raise ValueError("Input CSV contains no observation rows with usable ID and time.")
    return grouped


def _find_exact(rows: list[dict[str, str]], time_col: str, target_time: float) -> dict[str, str] | None:
    for row in rows:
        row_time = _to_float(row.get(time_col))
        if row_time is not None and abs(row_time - target_time) <= 1e-9:
            return row
    return None


def _find_nearest(
    rows: list[dict[str, str]],
    time_col: str,
    target_time: float,
    max_window_h: float | None,
) -> dict[str, str]:
    nearest = min(rows, key=lambda row: abs(float(row[time_col]) - target_time))
    distance = abs(float(nearest[time_col]) - target_time)
    if max_window_h is not None and distance > max_window_h:
        raise ValueError(
            f"No source row within {max_window_h:g} h of requested time {target_time:g} h."
        )
    return nearest


def _bracket_rows(
    rows: list[dict[str, str]],
    time_col: str,
    target_time: float,
) -> tuple[dict[str, str], dict[str, str]]:
    exact = _find_exact(rows, time_col, target_time)
    if exact is not None:
        return exact, exact

    before: dict[str, str] | None = None
    after: dict[str, str] | None = None
    for row in rows:
        row_time = float(row[time_col])
        if row_time < target_time:
            before = row
        elif row_time > target_time:
            after = row
            break
    if before is None or after is None:
        first = float(rows[0][time_col])
        last = float(rows[-1][time_col])
        raise ValueError(
            f"Requested time {target_time:g} h is outside available range {first:g}-{last:g} h."
        )
    return before, after


def _merge_row(
    *,
    lower: dict[str, str],
    upper: dict[str, str],
    target_time: float,
    time_col: str,
    fieldnames: list[str],
) -> dict[str, str]:
    lower_time = float(lower[time_col])
    upper_time = float(upper[time_col])
    if abs(upper_time - lower_time) <= 1e-12:
        ratio = 0.0
    else:
        ratio = (target_time - lower_time) / (upper_time - lower_time)
    nearest = lower if abs(target_time - lower_time) <= abs(upper_time - target_time) else upper

    row: dict[str, str] = {}
    for field in fieldnames:
        if field == time_col:
            row[field] = _format_float(target_time)
            continue
        lower_value = _to_float(lower.get(field))
        upper_value = _to_float(upper.get(field))
        if lower_value is not None and upper_value is not None:
            interpolated = lower_value + ratio * (upper_value - lower_value)
            row[field] = _format_float(interpolated)
        else:
            row[field] = nearest.get(field, "")

    for evid_col in ("evid", "EVID"):
        if evid_col in row:
            row[evid_col] = "0"
    for mdv_col in ("MDV", "mdv"):
        if mdv_col in row:
            row[mdv_col] = "0"
    for amount_col in ("amt", "AMT", "rate", "RATE"):
        if amount_col in row:
            row[amount_col] = "0"
    return row


def _sample_one(
    rows: list[dict[str, str]],
    *,
    time_col: str,
    fieldnames: list[str],
    target_time: float,
    method: Method,
    nearest_window_h: float | None,
) -> dict[str, str]:
    if method == "exact":
        exact = _find_exact(rows, time_col, target_time)
        if exact is None:
            raise ValueError(f"No exact source row at requested time {target_time:g} h.")
        return _merge_row(
            lower=exact,
            upper=exact,
            target_time=target_time,
            time_col=time_col,
            fieldnames=fieldnames,
        )
    if method == "nearest":
        nearest = _find_nearest(rows, time_col, target_time, nearest_window_h)
        return _merge_row(
            lower=nearest,
            upper=nearest,
            target_time=target_time,
            time_col=time_col,
            fieldnames=fieldnames,
        )
    if method == "linear":
        lower, upper = _bracket_rows(rows, time_col, target_time)
        return _merge_row(
            lower=lower,
            upper=upper,
            target_time=target_time,
            time_col=time_col,
            fieldnames=fieldnames,
        )
    raise ValueError(f"Unsupported sampling method: {method}")


def _actual_time(
    nominal_time_h: float,
    *,
    jitter_min: float,
    rng: random.Random,
) -> float:
    if jitter_min <= 0 or abs(nominal_time_h) < 1e-12:
        return nominal_time_h
    jitter_h = rng.uniform(-jitter_min / 60.0, jitter_min / 60.0)
    return max(0.0, nominal_time_h + jitter_h)


def sample_clinical_timepoints(
    sim_csv: Path | str,
    out_csv: Path | str,
    *,
    times_h: list[float] | None = None,
    schedule: list[SchedulePoint] | None = None,
    method: Method = "linear",
    nearest_window_h: float | None = None,
    jitter_min: float = 0.0,
    seed: int = 20260217,
) -> SamplingResult:
    sim_path = Path(sim_csv)
    out_path = Path(out_csv)
    fieldnames, rows = _read_sim_csv(sim_path)
    time_col = _time_col(fieldnames)
    id_col = _id_col(fieldnames)
    grouped = _group_observations(rows, id_col=id_col, time_col=time_col)

    sampling_schedule = schedule if schedule is not None else schedule_from_times(times_h or [])
    rng = random.Random(seed)
    extra_fields = ["NOMTIME_H", "TIME_H", "TPT", "TPTNUM", "SAMPLE_METHOD"]
    out_fields = list(fieldnames) + [field for field in extra_fields if field not in fieldnames]

    out_rows: list[dict[str, str]] = []
    for subject_id in sorted(grouped, key=lambda v: (len(v), v)):
        subject_rows = grouped[subject_id]
        for point in sampling_schedule:
            target_time = _actual_time(point.nominal_time_h, jitter_min=jitter_min, rng=rng)
            sampled = _sample_one(
                subject_rows,
                time_col=time_col,
                fieldnames=fieldnames,
                target_time=target_time,
                method=method,
                nearest_window_h=nearest_window_h,
            )
            sampled["NOMTIME_H"] = _format_float(point.nominal_time_h)
            sampled["TIME_H"] = _format_float(target_time)
            sampled["TPT"] = point.tpt
            sampled["TPTNUM"] = str(point.tptnum)
            sampled["SAMPLE_METHOD"] = method
            out_rows.append(sampled)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    return SamplingResult(
        out_csv=out_path,
        n_subjects=len(grouped),
        n_timepoints=len(sampling_schedule),
        n_rows=len(out_rows),
        method=method,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sim_csv", help="Dense raw/sim_full.csv from a simulation run.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--times", help="Comma-separated nominal sampling times in hours, e.g. 0,0.5,1,2,4,8,12,24.")
    group.add_argument("--schedule-csv", help="CSV with NOMTIME_H and optional TPT/TPTNUM columns.")
    parser.add_argument("--out", required=True, help="Output sparse clinical-sampling CSV.")
    parser.add_argument("--method", choices=["exact", "nearest", "linear"], default="linear")
    parser.add_argument("--nearest-window-h", type=float, default=None, help="Maximum allowed distance for --method nearest.")
    parser.add_argument("--jitter-min", type=float, default=0.0, help="Uniform actual-time jitter in +/- minutes.")
    parser.add_argument("--seed", type=int, default=20260217, help="Random seed for actual-time jitter.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        schedule = load_schedule_csv(Path(args.schedule_csv)) if args.schedule_csv else None
        times = parse_times(args.times) if args.times else None
        result = sample_clinical_timepoints(
            args.sim_csv,
            args.out,
            times_h=times,
            schedule=schedule,
            method=args.method,
            nearest_window_h=args.nearest_window_h,
            jitter_min=args.jitter_min,
            seed=args.seed,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Clinical sample CSV written: {result.out_csv}")
    print(f"Subjects: {result.n_subjects}")
    print(f"Nominal timepoints: {result.n_timepoints}")
    print(f"Rows: {result.n_rows}")
    print(f"Method: {result.method}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
