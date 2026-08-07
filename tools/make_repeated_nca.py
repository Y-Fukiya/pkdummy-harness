#!/usr/bin/env python3
"""Create trough and steady-state partial-NCA fixture outputs.

This adapter is intentionally small and deterministic.  It consumes the sparse
clinical sample fixture plus the repeated-dose reference time and does not
claim to be a submission-ready NCA engine.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass(frozen=True)
class RepeatedNcaResult:
    out_dir: Path
    status: str
    files: dict[str, Path]
    counts: dict[str, int]
    warnings: list[str]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV is empty: {path}")
        return list(reader.fieldnames), list(reader)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row.get(field, "")) for field in fieldnames})


def _write_yaml(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(obj, handle, sort_keys=False, allow_unicode=True)


def _to_float(value: object) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: float, digits: int = 12) -> str:
    if abs(value) < 1e-12:
        value = 0.0
    return f"{value:.{digits}g}"


def _format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return _format_number(value)
    return str(value)


def _norm(value: object) -> str:
    return str(value or "").strip()


def _time_key(value: float) -> str:
    return _format_number(value)


def _groups(rows: Iterable[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        usubjid = _norm(row.get("USUBJID"))
        if usubjid:
            grouped.setdefault(usubjid, []).append(row)
    return grouped


def _row_time(row: dict[str, str]) -> float:
    parsed = _to_float(row.get("TIME_H") or row.get("NOMTIME_H"))
    if parsed is None:
        raise ValueError(f"Clinical sample is missing TIME_H: {row}")
    return parsed


def _row_conc(row: dict[str, str], column: str) -> float:
    parsed = _to_float(row.get(column))
    if parsed is None:
        raise ValueError(f"Clinical sample is missing numeric {column}: {row}")
    if parsed < 0:
        raise ValueError(f"Clinical sample has negative {column}: {row}")
    return parsed


def _integrate(points: list[tuple[float, float]], start: float, end: float) -> float:
    selected = [(time, conc) for time, conc in points if start - 1e-12 <= time <= end + 1e-12]
    if not selected or abs(selected[0][0] - start) > 1e-9 or abs(selected[-1][0] - end) > 1e-9:
        raise ValueError(f"NCA interval {start:g}-{end:g} h is missing an exact boundary point.")
    total = 0.0
    for (time1, conc1), (time2, conc2) in zip(selected, selected[1:]):
        delta = time2 - time1
        if delta <= 0:
            raise ValueError("NCA points must be strictly increasing within a subject.")
        if conc1 > 0 and conc2 > 0 and conc2 < conc1:
            total += (conc1 - conc2) / math.log(conc1 / conc2) * delta
        else:
            total += (conc1 + conc2) * delta / 2.0
    return total


def _flagged(row: dict[str, str], field: str) -> bool:
    return _norm(row.get(field)).upper() in {"Y", "1", "TRUE"}


def _time_label(time_h: float) -> str:
    return f"{_time_key(time_h).replace('.', 'P')}H"


def _auc_unit(concentration_unit: str) -> str:
    unit = _norm(concentration_unit) or "ng/mL"
    parts = unit.split("/", 1)
    if len(parts) == 2:
        return f"{parts[0]}*h/{parts[1]}"
    return f"{unit}*h"


def _auc_paramcd(start: float, end: float) -> str:
    return f"AUC{_time_key(start).replace('.', 'P')}_{_time_key(end).replace('.', 'P')}_SS"


def make_repeated_nca(
    *,
    clinical_samples_csv: Path | str,
    out_dir: Path | str,
    analysis_dose_time_h: float,
    interval_h: float = 12.0,
    trough_times_h: list[float] | None = None,
    ss_times_after_dose_h: list[float] | None = None,
    partial_intervals_h: list[tuple[float, float]] | None = None,
    concentration_col: str = "DV",
    stable_rel_threshold: float = 0.05,
) -> RepeatedNcaResult:
    if interval_h <= 0:
        raise ValueError("interval_h must be positive.")
    if stable_rel_threshold < 0:
        raise ValueError("stable_rel_threshold must be non-negative.")
    trough_times = sorted(set(trough_times_h or [0, 24, 48, 72, 96, 120, 144, 156]))
    ss_times = sorted(set(ss_times_after_dose_h or [0, 0.5, 1, 2, 3, 4, 6, 8, 12]))
    partials = partial_intervals_h or [(0.0, 4.0), (4.0, 12.0)]
    partials = sorted((float(start), float(end)) for start, end in partials)
    if not {120.0, 144.0}.issubset({float(value) for value in trough_times}):
        raise ValueError("trough_times_h must include 120 and 144 h for predicted stability QC.")
    if abs(ss_times[0]) > 1e-9 or abs(ss_times[-1] - interval_h) > 1e-9:
        raise ValueError("ss_times_after_dose_h must start at 0 and end at interval_h.")
    if any(value < 0 or value > interval_h for value in ss_times):
        raise ValueError("ss_times_after_dose_h must be within the NCA interval.")
    if any(start < -1e-9 or end > interval_h + 1e-9 or end <= start for start, end in partials):
        raise ValueError("partial NCA intervals must be within 0-interval_h and have end > start.")
    if not partials or abs(partials[0][0]) > 1e-9 or abs(partials[-1][1] - interval_h) > 1e-9:
        raise ValueError("partial NCA intervals must cover the complete interval.")
    if any(abs(partials[index][1] - partials[index + 1][0]) > 1e-9 for index in range(len(partials) - 1)):
        raise ValueError("partial NCA intervals must be contiguous and cover the complete interval.")

    _, rows = _read_csv(Path(clinical_samples_csv))
    if not rows:
        raise ValueError("clinical_samples.csv has no rows.")
    grouped = _groups(rows)
    if not grouped:
        raise ValueError("clinical_samples.csv has no USUBJID values.")

    trough_input: list[dict[str, Any]] = []
    ss_input: list[dict[str, Any]] = []
    trough_summary: list[dict[str, Any]] = []
    nca_summary: list[dict[str, Any]] = []
    warnings: list[str] = []

    trough_fields = [
        "STUDYID",
        "USUBJID",
        "TIME_H",
        "STUDY_DAY",
        "DOSESEQ_NEXT",
        "DV",
        "IPRED",
        "CONC_UNIT",
        "MDV",
        "TROUGHFL",
    ]
    ss_fields = [
        "STUDYID",
        "USUBJID",
        "ABS_TIME_H",
        "TIME_H",
        "TAD_H",
        "DV",
        "IPRED",
        "CONC_UNIT",
        "MDV",
        "SSNCAFL",
        "DOSESEQ_REF",
    ]
    trough_label_fields = []
    for time_h in trough_times:
        trough_label_fields.extend([f"DV_TROUGH_{_time_label(time_h)}", f"IPRED_TROUGH_{_time_label(time_h)}"])

    for usubjid in sorted(grouped):
        subject_rows = sorted(grouped[usubjid], key=_row_time)
        trough_rows = [row for row in subject_rows if _flagged(row, "TROUGHFL")]
        ss_rows = [row for row in subject_rows if _flagged(row, "SSNCAFL")]
        if not trough_rows:
            trough_rows = [row for row in subject_rows if any(abs(_row_time(row) - target) < 1e-9 for target in trough_times)]
        if not ss_rows:
            ss_rows = [
                row
                for row in subject_rows
                if analysis_dose_time_h - 1e-9 <= _row_time(row) <= analysis_dose_time_h + interval_h + 1e-9
            ]
        if len(trough_rows) != len(trough_times):
            raise ValueError(f"{usubjid} has {len(trough_rows)} trough rows; expected {len(trough_times)}.")
        if len(ss_rows) != len(ss_times):
            raise ValueError(f"{usubjid} has {len(ss_rows)} SS NCA rows; expected {len(ss_times)}.")

        study_id = _norm(subject_rows[0].get("STUDYID"))
        trough_row_map = {_time_key(_row_time(row)): row for row in trough_rows}
        summary: dict[str, Any] = {"STUDYID": study_id, "USUBJID": usubjid}
        for target in trough_times:
            row = trough_row_map.get(_time_key(target))
            if row is None:
                raise ValueError(f"{usubjid} is missing trough time {target:g} h.")
            summary[f"DV_TROUGH_{_time_label(target)}"] = _row_conc(row, concentration_col)
            summary[f"IPRED_TROUGH_{_time_label(target)}"] = _row_conc(row, "IPRED")
            trough_input.append(
                {
                    "STUDYID": study_id,
                    "USUBJID": usubjid,
                    "TIME_H": target,
                    "STUDY_DAY": target / 24.0 + 1.0,
                    "DOSESEQ_NEXT": row.get("DOSESEQ_NEXT") or "",
                    "DV": _row_conc(row, concentration_col),
                    "IPRED": _row_conc(row, "IPRED"),
                    "CONC_UNIT": row.get("DV_UNIT") or row.get("CONC_UNIT") or "ng/mL",
                    "MDV": row.get("MDV") or "0",
                    "TROUGHFL": "Y",
                }
            )
        ipred_120 = _row_conc(trough_row_map[_time_key(120.0)], "IPRED")
        ipred_144 = _row_conc(trough_row_map[_time_key(144.0)], "IPRED")
        rel_change = abs(ipred_144 - ipred_120) / ipred_144 if ipred_144 > 0 else float("inf")
        summary["PRED_TROUGH_REL_CHANGE_120_144"] = rel_change
        summary["PRED_TROUGH_STABLE_QC"] = "PASS" if rel_change <= stable_rel_threshold else "FAIL"
        if rel_change > stable_rel_threshold:
            warnings.append(f"{usubjid}: predicted trough relative change {rel_change:.6g} exceeds {stable_rel_threshold:.6g}")
        trough_summary.append(summary)

        points: list[tuple[float, float]] = []
        for row in sorted(ss_rows, key=_row_time):
            abs_time = _row_time(row)
            tad = _to_float(row.get("TAD_H"))
            if tad is None:
                tad = abs_time - analysis_dose_time_h
            if tad < -1e-9 or tad > interval_h + 1e-9:
                raise ValueError(f"{usubjid} has SS NCA TAD outside 0-{interval_h:g} h: {tad}")
            conc = _row_conc(row, concentration_col)
            points.append((tad, conc))
            ss_input.append(
                {
                    "STUDYID": study_id,
                    "USUBJID": usubjid,
                    "ABS_TIME_H": abs_time,
                    "TIME_H": tad,
                    "TAD_H": tad,
                    "DV": conc,
                    "IPRED": _row_conc(row, "IPRED"),
                    "CONC_UNIT": row.get("DV_UNIT") or row.get("CONC_UNIT") or "ng/mL",
                    "MDV": row.get("MDV") or "0",
                    "SSNCAFL": "Y",
                    "DOSESEQ_REF": row.get("DOSESEQ_REF") or "",
                }
            )
        points.sort()
        aucs = [_integrate(points, start, end) for start, end in partials]
        auc_tau = sum(aucs)
        cmax_time, cmax = max(points, key=lambda item: (item[1], -item[0]))
        cmin = min(conc for _, conc in points)
        c_trough = next((conc for time, conc in points if abs(time - interval_h) < 1e-9), None)
        if c_trough is None:
            raise ValueError(f"{usubjid} is missing the final trough at {interval_h:g} h.")
        unit = ss_rows[0].get("DV_UNIT") or ss_rows[0].get("CONC_UNIT") or "ng/mL"
        summary = {
            "STUDYID": study_id,
            "USUBJID": usubjid,
            "AUCTAU_SS": auc_tau,
            "CMAX_SS": cmax,
            "TMAX_SS_H": cmax_time,
            "CPREDOSE_SS": points[0][1],
            "CTROUGH_SS": c_trough,
            "CMIN_SS": cmin,
            "CAVG_SS": auc_tau / interval_h,
            "FLUCT_PCT_SS": ((cmax - cmin) / (auc_tau / interval_h) * 100.0) if auc_tau > 0 else "",
            "N_POINTS": len(points),
            "AUC_UNIT": _auc_unit(unit),
        }
        for partial, auc in zip(partials, aucs):
            summary[_auc_paramcd(*partial)] = auc
        nca_summary.append(summary)

    output = Path(out_dir)
    files = {
        "TROUGH_INPUT": output / "TROUGH_INPUT.csv",
        "TROUGH_SUMMARY": output / "TROUGH_SUMMARY.csv",
        "NCA_SS_INPUT": output / "NCA_SS_INPUT.csv",
        "NCA_SS_SUMMARY": output / "NCA_SS_SUMMARY.csv",
        "MANIFEST": output / "REPEATED_NCA_MANIFEST.yml",
    }
    partial_fields = [_auc_paramcd(start, end) for start, end in partials]
    nca_fields = [
        "STUDYID",
        "USUBJID",
        *partial_fields,
        "AUCTAU_SS",
        "CMAX_SS",
        "TMAX_SS_H",
        "CPREDOSE_SS",
        "CTROUGH_SS",
        "CMIN_SS",
        "CAVG_SS",
        "FLUCT_PCT_SS",
        "N_POINTS",
        "AUC_UNIT",
    ]
    trough_summary_fields = ["STUDYID", "USUBJID", *trough_label_fields, "PRED_TROUGH_REL_CHANGE_120_144", "PRED_TROUGH_STABLE_QC"]
    _write_csv(files["TROUGH_INPUT"], trough_input, trough_fields)
    _write_csv(files["TROUGH_SUMMARY"], trough_summary, trough_summary_fields)
    _write_csv(files["NCA_SS_INPUT"], ss_input, ss_fields)
    _write_csv(files["NCA_SS_SUMMARY"], nca_summary, nca_fields)
    status = "WARN" if warnings else "OK"
    counts = {
        "subjects": len(grouped),
        "trough_rows": len(trough_input),
        "ss_nca_rows": len(ss_input),
        "trough_summary_rows": len(trough_summary),
        "ss_nca_summary_rows": len(nca_summary),
    }
    _write_yaml(
        files["MANIFEST"],
        {
            "purpose": "repeated_oral_trough_steady_state_nca_fixture",
            "status": status,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "inputs": {"clinical_samples_csv": str(clinical_samples_csv)},
            "outputs": {key: str(value) for key, value in files.items()},
            "settings": {
                "analysis_dose_time_h": analysis_dose_time_h,
                "interval_h": interval_h,
                "trough_times_h": trough_times,
                "ss_times_after_dose_h": ss_times,
                "partial_intervals_h": partials,
                "concentration_col": concentration_col,
                "stable_rel_threshold": stable_rel_threshold,
                "integration": "linear-up-log-down",
            },
            "counts": counts,
            "warnings": warnings,
            "notes": [
                "Outputs are workflow fixtures, not submission-ready NCA or ADaM datasets.",
                "DV is used for observed NCA; IPRED is used only for predicted trough stability QC.",
                "AUCinf and terminal half-life are intentionally not calculated from the final dosing interval.",
            ],
        },
    )
    return RepeatedNcaResult(out_dir=output, status=status, files=files, counts=counts, warnings=warnings)


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clinical-samples", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--analysis-dose-time-h", required=True, type=float)
    parser.add_argument("--interval-h", default=12.0, type=float)
    parser.add_argument("--trough-times", default="0,24,48,72,96,120,144,156")
    parser.add_argument("--ss-times-after-dose", default="0,0.5,1,2,3,4,6,8,12")
    parser.add_argument("--concentration-col", default="DV")
    parser.add_argument("--stable-rel-threshold", default=0.05, type=float)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = make_repeated_nca(
            clinical_samples_csv=args.clinical_samples,
            out_dir=args.out_dir,
            analysis_dose_time_h=args.analysis_dose_time_h,
            interval_h=args.interval_h,
            trough_times_h=_parse_float_list(args.trough_times),
            ss_times_after_dose_h=_parse_float_list(args.ss_times_after_dose),
            concentration_col=args.concentration_col,
            stable_rel_threshold=args.stable_rel_threshold,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Repeated NCA fixtures: {result.status}")
    print(f"Output directory: {result.out_dir}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for key in sorted(result.files):
        print(f"{key}: {result.files[key]}")
    return 1 if result.status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
