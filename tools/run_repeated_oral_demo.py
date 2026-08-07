#!/usr/bin/env python3
"""Generate the repeated oral trough / steady-state NCA workflow fixture.

The repeated-dose path is deliberately separate from the existing single-dose
``demo_set`` path.  It keeps dose events explicit, supports the analytical
superposition fixture and the independent R/mrgsolve ODE fixture, and produces
a dedicated steady-state NCA summary.  It is a workflow fixture, not a clinical
simulation engine.
"""

from __future__ import annotations

import csv
import math
import random
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.make_analysis_inputs import make_analysis_inputs
from tools.make_repeated_nca import make_repeated_nca
from tools.make_sdtm_like_domains import _arm_dose, _spec_drug_name, _spec_route, make_sdtm_like_domains
from tools.run_demo_set import (
    _concentration_ng_ml,
    _has_first_order_absorption,
    _load_yaml,
    _lognormal_factor,
    _residual_observation,
    _resolve_drug_files,
)
from tools.sample_clinical_timepoints import sample_clinical_timepoints


@dataclass(frozen=True)
class RepeatedOralDemoResult:
    out_dir: Path
    status: str
    files: dict[str, Path]
    counts: dict[str, int]
    warnings: list[str]


MODEL_QC_REL_THRESHOLD = 0.25


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_yaml(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(obj, handle, sort_keys=False, allow_unicode=True)


def _to_float(value: object, default: float | None = None) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_number(value: float, digits: int = 12) -> str:
    if abs(value) < 1e-12:
        value = 0.0
    return f"{value:.{digits}g}"


def _format_datetime(start: datetime, time_h: float) -> str:
    return (start + timedelta(hours=time_h)).isoformat(timespec="seconds")


def _subject_values(study_id: str, index: int, dose_mg: float) -> dict[str, Any]:
    sex = "M" if index % 2 else "F"
    wt = 70.0 + ((index % 5) - 2) * 3.0
    age = 40 + (index % 20)
    return {
        "ID": index,
        "ARM": "A",
        "WT": wt,
        "AGE": age,
        "SEX_CHAR": sex,
        "DOSE_MG": dose_mg,
        "STUDYID": study_id,
        "USUBJID": f"{study_id}-{index:03d}",
    }


def _time_grid(t_end_h: float, dt_h: float) -> list[float]:
    if t_end_h <= 0 or dt_h <= 0:
        raise ValueError("t_end_h and dt_h must be positive.")
    n_steps = int(round(t_end_h / dt_h))
    if abs(n_steps * dt_h - t_end_h) > 1e-9:
        raise ValueError("t_end_h must be an exact multiple of dt_h for exact sampling.")
    return [round(index * dt_h, 10) for index in range(n_steps + 1)]


def _study_id(config: dict[str, Any], spec: dict[str, Any]) -> str:
    override = ((config.get("study") or {}).get("id_override"))
    return str(override or ((spec.get("study") or {}).get("id")) or "OSP_repeated_oral")


def _study_start(config: dict[str, Any]) -> datetime:
    value = str(((config.get("study") or {}).get("start_datetime")) or "2026-01-01T08:00:00")
    return datetime.fromisoformat(value)


def _repeated_settings(config: dict[str, Any]) -> tuple[float, int, int, float, float]:
    simulation = config.get("simulation") or {}
    dosing = simulation.get("repeated_dosing") or {}
    interval_h = _to_float(dosing.get("interval_h"))
    dose_count_raw = dosing.get("dose_count")
    analysis_dose_raw = dosing.get("analysis_dose_number")
    t_end_h = _to_float(simulation.get("t_end_h"))
    dt_h = _to_float(simulation.get("dt_h"))
    if interval_h is None or interval_h <= 0:
        raise ValueError("simulation.repeated_dosing.interval_h must be positive.")
    try:
        dose_count = int(dose_count_raw)
        if isinstance(dose_count_raw, bool) or float(dose_count_raw) != dose_count or dose_count < 2:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("simulation.repeated_dosing.dose_count must be an integer >= 2.")
    try:
        analysis_dose_number = int(analysis_dose_raw)
        if isinstance(analysis_dose_raw, bool) or float(analysis_dose_raw) != analysis_dose_number:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("simulation.repeated_dosing.analysis_dose_number must be an integer.")
    if not 1 <= analysis_dose_number <= dose_count:
        raise ValueError("analysis_dose_number must be between 1 and dose_count.")
    if t_end_h is None or t_end_h <= 0:
        raise ValueError("simulation.t_end_h must be positive.")
    if dt_h is None or dt_h <= 0:
        raise ValueError("simulation.dt_h must be positive.")
    analysis_time_h = (analysis_dose_number - 1) * interval_h
    if t_end_h + 1e-9 < analysis_time_h + interval_h:
        raise ValueError("simulation.t_end_h must cover the full final analysis interval.")
    return interval_h, dose_count, analysis_dose_number, t_end_h, dt_h


def _sampling_settings(config: dict[str, Any], *, analysis_time_h: float, interval_h: float) -> tuple[list[float], list[float], dict[float, str]]:
    sampling = config.get("sampling") or {}
    def parse_times(values: Any, default: list[float], label: str) -> list[float]:
        raw_values = default if values is None else values
        if not isinstance(raw_values, list) or not raw_values:
            raise ValueError(f"{label} must be a non-empty list.")
        parsed: list[float] = []
        for value in raw_values:
            parsed_value = float(value)
            if not math.isfinite(parsed_value):
                raise ValueError(f"{label} must contain finite numeric values.")
            parsed.append(round(parsed_value, 10))
        return sorted(set(parsed))

    trough = parse_times(sampling.get("trough_times_h"), [0, 24, 48, 72, 96, 120, 144, 156], "sampling.trough_times_h")
    ss_after = parse_times(sampling.get("ss_times_after_dose_h"), [0, 0.5, 1, 2, 3, 4, 6, 8, 12], "sampling.ss_times_after_dose_h")
    if not trough or not ss_after:
        raise ValueError("sampling trough and SS time lists must be non-empty.")
    if any(value < -1e-9 for value in trough):
        raise ValueError("sampling.trough_times_h must be non-negative.")
    if any(value < -1e-9 or value > interval_h + 1e-9 for value in ss_after):
        raise ValueError("sampling.ss_times_after_dose_h must stay within the dosing interval.")
    absolute_ss = [round(analysis_time_h + value, 10) for value in ss_after]
    sample_times = sorted(set(round(value, 10) for value in [*trough, *absolute_ss]))
    if any(value < -1e-9 for value in sample_times):
        raise ValueError("sampling times must be non-negative.")
    if abs(ss_after[0]) > 1e-9 or abs(ss_after[-1] - interval_h) > 1e-9:
        raise ValueError("ss_times_after_dose_h must start at 0 and end at interval_h.")
    labels: dict[float, str] = {}
    for time_h in trough:
        labels[round(time_h, 10)] = "Baseline pre-dose" if abs(time_h) < 1e-9 else f"Day {int(time_h / 24) + 1} AM trough"
    for after_h in ss_after:
        absolute = round(analysis_time_h + after_h, 10)
        labels[absolute] = f"SS {_format_number(after_h)} h"
    analysis_day = int(analysis_time_h / 24.0) + 1
    labels[round(analysis_time_h, 10)] = f"Day {analysis_day} pre-dose / SS 0 h"
    labels[round(analysis_time_h + interval_h, 10)] = f"SS {_format_number(interval_h)} h / pre-next-dose"
    # Keep the raw trough schedule separate from the union of all sampling
    # times.  The latter is derived by the caller for simulation sampling;
    # TROUGHFL must only identify the explicitly requested predose points.
    return trough, ss_after, labels


def _mrgsolve_output_to_repeated_fixture(
    *,
    sim_csv: Path,
    dosing_csv: Path,
    spec: dict[str, Any],
    study_id: str,
    study_start: datetime,
) -> tuple[int, int]:
    """Normalize mrgsolve's event-aware CSV into the repeated fixture contract."""
    with sim_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if not rows or not fields:
        raise ValueError("mrgsolve returned an empty sim_full.csv.")
    required = {"ID", "time", "EVID", "AMT", "RATE", "DV", "IPRED", "USUBJID"}
    missing = sorted(required.difference(fields))
    if missing:
        raise ValueError(f"mrgsolve sim_full.csv is missing required columns: {', '.join(missing)}")
    drug_name = _spec_drug_name(spec)
    route = _spec_route(spec)
    for row in rows:
        subject_id = _to_float(row.get("ID"))
        if subject_id is None or subject_id < 1 or subject_id != int(subject_id):
            raise ValueError(f"mrgsolve sim_full.csv has invalid ID: {row.get('ID')!r}")
        row["STUDYID"] = study_id
        row["USUBJID"] = f"{study_id}-{int(subject_id):03d}"
        row["evid"] = row.get("EVID", "0")
        row["amt"] = row.get("AMT", "0")
        row["rate"] = row.get("RATE", "0")
        row["cmt"] = row.get("CMT", "")
    for field in ("STUDYID", "evid", "amt", "rate", "cmt"):
        if field not in fields:
            fields.append(field)
    _write_csv(sim_csv, rows, fields)

    event_rows = [row for row in rows if abs(_to_float(row.get("EVID")) or 0.0) == 1.0]
    event_rows.sort(key=lambda row: (int(float(row["ID"])), float(row["time"])))
    sequence_by_subject: dict[str, int] = {}
    dosing_rows: list[dict[str, Any]] = []
    for row in event_rows:
        usubjid = row["USUBJID"]
        sequence_by_subject[usubjid] = sequence_by_subject.get(usubjid, 0) + 1
        seq = sequence_by_subject[usubjid]
        dose = _to_float(row.get("AMT")) or 0.0
        rate = _to_float(row.get("RATE")) or 0.0
        time_h = _to_float(row.get("time"))
        infusion_h = dose / rate if dose > 0 and rate > 0 else 0.0
        dose_unit = str(row.get("DOSE_UNIT") or ((spec.get("regimen") or {}).get("units") or {}).get("dose") or "mg")
        dosing_rows.append(
            {
                "ID": int(float(row["ID"])),
                "time": time_h if time_h is not None else "",
                "evid": 1,
                "MDV": 1,
                "amt": dose,
                "ARM": row.get("ARM", "A"),
                "WT": row.get("WT", ""),
                "AGE": row.get("AGE", ""),
                "SEX_CHAR": row.get("SEX", row.get("SEX_CHAR", "")),
                "DOSE_MG": dose,
                "STUDYID": study_id,
                "USUBJID": usubjid,
                "DOMAIN": "EX",
                "EXSEQ": seq,
                "DOSESEQ": seq,
                "EXTIME_H": time_h if time_h is not None else "",
                "EXTRT": drug_name,
                "EXDOSE": dose,
                "EXDOSU": dose_unit,
                "EXROUTE": route,
                "EXINFH": infusion_h,
                "EXSTDTC": _format_datetime(study_start, time_h or 0.0),
                "EXENDTC": _format_datetime(study_start, time_h or 0.0),
                "EXARM": row.get("ARM", "A"),
                "EXACTARM": row.get("ARM", "A"),
            }
        )
    dosing_fields = [
        "ID", "time", "evid", "MDV", "amt", "ARM", "WT", "AGE", "SEX_CHAR", "DOSE_MG",
        "STUDYID", "USUBJID", "DOMAIN", "EXSEQ", "DOSESEQ", "EXTIME_H", "EXTRT", "EXDOSE",
        "EXDOSU", "EXROUTE", "EXINFH", "EXSTDTC", "EXENDTC", "EXARM", "EXACTARM",
    ]
    _write_csv(dosing_csv, dosing_rows, dosing_fields)
    return len(rows), len(dosing_rows)


def _generate_simulation_mrgsolve(
    *,
    spec_path: Path,
    spec: dict[str, Any],
    out_csv: Path,
    dosing_csv: Path,
    study_id: str,
    study_start: datetime,
    n_subjects: int,
    interval_h: float,
    dose_count: int,
    t_end_h: float,
    dt_h: float,
    variability: dict[str, Any] | None,
) -> tuple[int, int]:
    """Run the independent R/mrgsolve engine for repeated dosing."""
    seed = int((variability or {}).get("seed", 20260217) or 20260217)
    rscript = shutil.which("Rscript")
    if rscript is None:
        raise ValueError("simulation.engine=mrgsolve requires Rscript on PATH.")
    runner = Path(__file__).resolve().with_name("mrgsolve_runner.R")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        rscript,
        str(runner),
        "--spec", str(spec_path),
        "--out", str(out_csv),
        "--n-subjects", str(n_subjects),
        "--t-end-h", _format_number(t_end_h),
        "--dt-h", _format_number(dt_h),
        "--dose-count", str(dose_count),
        "--interval-h", _format_number(interval_h),
        "--seed", str(seed),
    ]
    completed = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if completed.returncode != 0:
        tail = "\n".join(completed.stdout.splitlines()[-20:])
        raise ValueError(f"mrgsolve repeated simulation failed (exit {completed.returncode}):\n{tail}")
    return _mrgsolve_output_to_repeated_fixture(
        sim_csv=out_csv,
        dosing_csv=dosing_csv,
        spec=spec,
        study_id=study_id,
        study_start=study_start,
    )


def _generate_simulation(
    *,
    spec: dict[str, Any],
    out_csv: Path,
    dosing_csv: Path,
    study_id: str,
    study_start: datetime,
    n_subjects: int,
    interval_h: float,
    dose_count: int,
    t_end_h: float,
    dt_h: float,
    variability: dict[str, Any] | None,
) -> tuple[int, int]:
    route = _spec_route(spec)
    if route not in {"ORAL", "PO"}:
        raise ValueError("repeated_oral_demo requires an oral route in the canonical spec.")
    arms = (spec.get("regimen") or {}).get("arms") or {}
    if len(arms) != 1:
        raise ValueError("repeated_oral_demo requires a single-arm canonical spec.")
    dose_mg = _arm_dose(spec, "A")
    if dose_mg is None or dose_mg <= 0:
        raise ValueError("canonical Arm A dose_mg must be positive.")
    var = variability or {}
    drug_name = _spec_drug_name(spec)
    regimen_units = (spec.get("regimen") or {}).get("units") or {}
    dose_unit = str(regimen_units.get("dose") or "mg")
    conc_unit = str(((spec.get("model") or {}).get("units") or {}).get("conc") or "ng/mL")
    iiv_cv = float(var.get("iiv_cv", 0.0) or 0.0)
    residual_cv = float(var.get("residual_cv", 0.0) or 0.0)
    seed = int(var.get("seed", 20260217) or 20260217)
    rng = random.Random(seed)
    times = _time_grid(t_end_h, dt_h)
    dose_times = [round(index * interval_h, 10) for index in range(dose_count)]
    sim_rows: list[dict[str, Any]] = []
    dosing_rows: list[dict[str, Any]] = []
    for subject_index in range(1, n_subjects + 1):
        subject = _subject_values(study_id, subject_index, dose_mg)
        cl_factor = _lognormal_factor(rng, iiv_cv)
        v_factor = _lognormal_factor(rng, iiv_cv)
        ka_factor = _lognormal_factor(rng, iiv_cv) if _has_first_order_absorption(spec, "oral") else 1.0
        for dose_seq, dose_time in enumerate(dose_times, start=1):
            dosing_rows.append(
                {
                    **subject,
                    "DOMAIN": "EX",
                    "EXSEQ": dose_seq,
                    "DOSESEQ": dose_seq,
                    "EXTIME_H": dose_time,
                    "time": dose_time,
                    "evid": 1,
                    "MDV": 1,
                    "amt": dose_mg,
                    "EXTRT": drug_name,
                    "EXDOSE": dose_mg,
                    "EXDOSU": dose_unit,
                    "EXROUTE": _spec_route(spec),
                    "EXINFH": 0,
                    "EXSTDTC": _format_datetime(study_start, dose_time),
                    "EXENDTC": _format_datetime(study_start, dose_time),
                    "EXARM": "A",
                    "EXACTARM": "A",
                }
            )
        for time_h in times:
            ipred = sum(
                _concentration_ng_ml(
                    spec,
                    dose_mg=dose_mg,
                    time_h=time_h - dose_time,
                    cl_factor=cl_factor,
                    v_factor=v_factor,
                    ka_factor=ka_factor,
                )
                for dose_time in dose_times
                if time_h >= dose_time
            )
            dv = _residual_observation(rng, ipred, residual_cv)
            sim_rows.append(
                {
                    **subject,
                    "time": time_h,
                    "evid": 0,
                    "MDV": 0,
                    "amt": 0,
                    "CP": ipred,
                    "IPRED": ipred,
                    "DV": dv,
                    "DV_UNIT": conc_unit,
                    "IPRED_UNIT": conc_unit,
                    "CP_UNIT": conc_unit,
                    "CL_FACTOR": cl_factor,
                    "V_FACTOR": v_factor,
                    "KA_FACTOR": ka_factor,
                }
            )
    sim_fields = [
        "ID",
        "time",
        "evid",
        "MDV",
        "CP",
        "IPRED",
        "DV",
        "DV_UNIT",
        "IPRED_UNIT",
        "CP_UNIT",
        "CL_FACTOR",
        "V_FACTOR",
        "KA_FACTOR",
        "ARM",
        "WT",
        "AGE",
        "SEX_CHAR",
        "DOSE_MG",
        "STUDYID",
        "USUBJID",
    ]
    dosing_fields = [
        "ID",
        "time",
        "evid",
        "MDV",
        "amt",
        "ARM",
        "WT",
        "AGE",
        "SEX_CHAR",
        "DOSE_MG",
        "STUDYID",
        "USUBJID",
        "DOMAIN",
        "EXSEQ",
        "DOSESEQ",
        "EXTIME_H",
        "EXTRT",
        "EXDOSE",
        "EXDOSU",
        "EXROUTE",
        "EXINFH",
        "EXSTDTC",
        "EXENDTC",
        "EXARM",
        "EXACTARM",
    ]
    _write_csv(out_csv, sim_rows, sim_fields)
    _write_csv(dosing_csv, dosing_rows, dosing_fields)
    return len(sim_rows), len(dosing_rows)


def _enrich_samples(
    *,
    clinical_csv: Path,
    trough_times: list[float],
    ss_after: list[float],
    analysis_time_h: float,
    interval_h: float,
    labels: dict[float, str],
    analysis_dose_number: int,
) -> None:
    with clinical_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    helper_fields = ["TROUGHFL", "SSNCAFL", "TAD_H", "DOSESEQ_REF", "DOSESEQ_NEXT", "ANALYSIS_PHASE"]
    fields.extend(field for field in helper_fields if field not in fields)
    ss_times = {round(analysis_time_h + value, 10) for value in ss_after}
    trough_set = {round(value, 10) for value in trough_times}
    for row in rows:
        time_h = float(row.get("NOMTIME_H") or row.get("TIME_H") or 0.0)
        time_key = round(time_h, 10)
        row["TPT"] = labels.get(time_key, row.get("TPT", ""))
        row["TPTNUM"] = str(sorted(set(trough_set) | ss_times).index(time_key) + 1)
        is_trough = time_key in trough_set
        is_ss = time_key in ss_times
        row["TROUGHFL"] = "Y" if is_trough else "N"
        row["SSNCAFL"] = "Y" if is_ss else "N"
        row["TAD_H"] = _format_number(time_h - analysis_time_h) if is_ss else ""
        row["DOSESEQ_REF"] = str(analysis_dose_number) if is_ss else ""
        row["DOSESEQ_NEXT"] = str(int(round(time_h / interval_h)) + 1) if is_trough else ""
        row["ANALYSIS_PHASE"] = "SS_NCA" if is_ss else "TROUGH" if is_trough else ""
        row["MDV"] = "1" if abs(time_h) < 1e-9 else "0"
    with clinical_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _patch_dm_end_date(dm_csv: Path, end_date: str) -> None:
    with dm_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if "RFENDTC" not in fields:
        return
    for row in rows:
        row["RFENDTC"] = end_date
    _write_csv(dm_csv, rows, fields)


def _integrate_profile(points: list[tuple[float, float]]) -> float:
    """Integrate a dense profile with the same linear-up/log-down rule as NCA."""
    if len(points) < 2:
        raise ValueError("Model QC requires at least two IPRED points.")
    total = 0.0
    for (time1, conc1), (time2, conc2) in zip(points, points[1:]):
        delta = time2 - time1
        if delta <= 0:
            raise ValueError("Model QC points must be strictly increasing.")
        if conc1 > 0 and conc2 > 0 and conc2 < conc1:
            total += (conc1 - conc2) / math.log(conc1 / conc2) * delta
        else:
            total += (conc1 + conc2) * delta / 2.0
    return total


def _make_model_qc(
    *,
    sim_csv: Path,
    out_csv: Path,
    spec: dict[str, Any],
    analysis_time_h: float,
    interval_h: float,
    dose_mg: float,
    rel_threshold: float = 0.25,
) -> tuple[int, list[str]]:
    with sim_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if abs(_to_float(row.get("EVID", row.get("evid", "0"))) or 0.0) != 0.0:
            continue
        usubjid = str(row.get("USUBJID") or "").strip()
        time_h = _to_float(row.get("time"))
        in_interval = time_h is not None and analysis_time_h - 1e-9 <= time_h <= analysis_time_h + interval_h + 1e-9
        if not usubjid or not in_interval:
            continue
        grouped.setdefault(usubjid, []).append(row)

    theta = (spec.get("model") or {}).get("theta") or {}
    units = (spec.get("model") or {}).get("units") or {}
    cl = _to_float(theta.get("CL"))
    f1 = _to_float(theta.get("F1"), 1.0)
    if f1 is None:
        f1 = 1.0
    mult = _to_float(units.get("mult"), 1000.0) or 1000.0
    if cl is None or cl <= 0:
        raise ValueError("model.theta.CL must be positive for model QC.")
    target_base = f1 * dose_mg * mult / cl
    qc_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for usubjid in sorted(grouped):
        subject_rows = sorted(grouped[usubjid], key=lambda row: float(row["time"]))
        points = [(float(row["time"]), float(row["IPRED"])) for row in subject_rows]
        has_boundaries = points and abs(points[0][0] - analysis_time_h) <= 1e-9 and abs(points[-1][0] - (analysis_time_h + interval_h)) <= 1e-9
        if not has_boundaries:
            raise ValueError(f"{usubjid} model QC profile is missing an interval boundary.")
        auc = _integrate_profile(points)
        cl_i = _to_float(subject_rows[0].get("CL_I"))
        if cl_i is not None and cl_i > 0:
            target = f1 * dose_mg * mult / cl_i
        else:
            cl_factor = _to_float(subject_rows[0].get("CL_FACTOR"), 1.0) or 1.0
            target = target_base / cl_factor
        rel_diff = abs(auc - target) / target if target > 0 else float("inf")
        status = "PASS" if rel_diff <= rel_threshold else "WARN"
        if status != "PASS":
            warnings.append(
                f"{usubjid}: dense IPRED AUC relative difference {rel_diff:.6g} "
                f"exceeds {rel_threshold:.6g}"
            )
        qc_rows.append(
            {
                "STUDYID": subject_rows[0].get("STUDYID", ""),
                "USUBJID": usubjid,
                "ANALYSIS_DOSE_TIME_H": analysis_time_h,
                "INTERVAL_H": interval_h,
                "AUC0_TAU_IPRED": auc,
                "AUC_TARGET_DERIVED": target,
                "REL_DIFF": rel_diff,
                "QC_STATUS": status,
            }
        )
    _write_csv(
        out_csv,
        qc_rows,
        [
            "STUDYID",
            "USUBJID",
            "ANALYSIS_DOSE_TIME_H",
            "INTERVAL_H",
            "AUC0_TAU_IPRED",
            "AUC_TARGET_DERIVED",
            "REL_DIFF",
            "QC_STATUS",
        ],
    )
    return len(qc_rows), warnings


def _write_summary(out_dir: Path, counts: dict[str, int], status: str, warnings: list[str]) -> dict[str, Path]:
    summary_csv = out_dir / "summary.csv"
    summary_md = out_dir / "summary.md"
    _write_csv(summary_csv, [{"status": status, **counts, "warnings": " | ".join(warnings)}], ["status", *counts.keys(), "warnings"])
    lines = [
        "# Repeated Oral Demo Summary",
        "",
        "Workflow fixture only; not clinical validation output.",
        "",
        f"- Status: `{status}`",
        f"- Warnings: {len(warnings)}",
        "",
        "| Count | Value |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {key} | {value} |" for key, value in counts.items())
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"summary_csv": summary_csv, "summary_md": summary_md}


def _write_repeated_workflow_artifacts(
    *,
    workflow_dir: Path,
    status: str,
    validation_status: str,
    sim_csv: Path,
    dosing_csv: Path,
    spec_path: Path,
    simulation_engine: str,
    counts: dict[str, int],
    warnings: list[str],
) -> dict[str, Path]:
    """Write the run-level artifacts promised by the repeated-dose spec.

    This is intentionally a small repeated-dose manifest rather than calling
    the single-dose ``run_workflow.py`` validator: that validator assumes one
    dose and would misinterpret the repeated event stream.
    """
    reports_dir = workflow_dir / "reports"
    manifest = workflow_dir / "MANIFEST.yml"
    trace = workflow_dir / "trace.log"
    validation_md = reports_dir / "simulation_validation.md"
    _write_yaml(
        manifest,
        {
            "purpose": "pk_fixture_repeated_oral_workflow",
            "status": status,
            "validation_status": validation_status,
            "inputs": {
                "sim_full_csv": str(sim_csv),
                "dosing_events_csv": str(dosing_csv),
                "spec_yml": str(spec_path),
                "simulation_engine": simulation_engine,
            },
            "counts": counts,
            "warnings": warnings,
            "validation": {
                "status": validation_status,
                "method": "repeated-dose model QC and NCA shape checks",
                "single_dose_validator": "not_used",
            },
            "safeguards": [
                "This is a repeated-dose workflow fixture, not clinical validation.",
                "The single-dose run_workflow.py validator is not applied to this event stream.",
                "Canonical PK files and spec files are read-only inputs.",
            ],
        },
    )
    trace.parent.mkdir(parents=True, exist_ok=True)
    trace.write_text(
        "\n".join(
            [
                "START repeated_oral_demo",
                f"SIMULATION rows={counts['sim_full_rows']} dose_events={counts['dosing_event_rows']}",
                f"SDTM_LIKE DM={counts['dm_rows']} EX={counts['ex_rows']} PC={counts['pc_rows']}",
                f"NCA trough={counts['trough_rows']} ss={counts['ss_nca_rows']}",
                f"VALIDATION status={validation_status} method=repeated-dose-model-qc",
                f"END status={status}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    validation_md.parent.mkdir(parents=True, exist_ok=True)
    validation_md.write_text(
        "\n".join(
            [
                "# Repeated-dose simulation validation",
                "",
                "This report is a workflow-fixture check, not clinical or regulatory validation.",
                "",
                f"- Workflow status: `{status}`",
                f"- Validation status: `{validation_status}`",
                "- Method: repeated-dose model QC plus NCA/trough shape checks",
                "- Single-dose `run_workflow.py` validator: not used (it assumes one dose)",
                "",
                "## Warnings",
                "",
                *([f"- {warning}" for warning in warnings] if warnings else ["- None"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "workflow_manifest": manifest,
        "trace_log": trace,
        "simulation_validation_md": validation_md,
    }


def run_repeated_oral_demo(
    *,
    config: dict[str, Any],
    out_dir: Path | str,
    drugs_dir: Path | str = "drugs",
) -> RepeatedOralDemoResult:
    drugs = config.get("drugs")
    if not isinstance(drugs, list) or len(drugs) != 1:
        raise ValueError("repeated_oral_demo requires exactly one drug slug.")
    slug = str(drugs[0])
    drugs_path = Path(drugs_dir)
    _, _, spec_path = _resolve_drug_files(drugs_path, slug)
    spec = _load_yaml(spec_path)
    if _spec_route(spec) not in {"ORAL", "PO"}:
        raise ValueError("repeated_oral_demo requires an oral route in the canonical spec.")
    if len((spec.get("regimen") or {}).get("arms") or {}) != 1:
        raise ValueError("repeated_oral_demo requires a single-arm canonical spec.")
    conc_unit = str((((spec.get("model") or {}).get("units") or {}).get("conc")) or "ng/mL")
    simulation = config.get("simulation") or {}
    engine = str(simulation.get("engine") or "analytical_demo").strip().lower()
    if engine not in {"analytical_demo", "mrgsolve"}:
        raise ValueError("simulation.engine must be analytical_demo or mrgsolve for repeated_oral_demo.")
    n_subjects_raw = simulation.get("n_subjects")
    try:
        n_subjects = int(n_subjects_raw)
        if isinstance(n_subjects_raw, bool) or float(n_subjects_raw) != n_subjects or n_subjects < 1:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("simulation.n_subjects must be a positive integer.")
    interval_h, dose_count, analysis_dose_number, t_end_h, dt_h = _repeated_settings(config)
    analysis_time_h = (analysis_dose_number - 1) * interval_h
    trough_times, ss_after, labels = _sampling_settings(config, analysis_time_h=analysis_time_h, interval_h=interval_h)
    if abs(t_end_h - round(t_end_h / dt_h) * dt_h) > 1e-9:
        raise ValueError("simulation.t_end_h must be an exact multiple of simulation.dt_h.")
    sample_times = sorted(set(trough_times + [analysis_time_h + value for value in ss_after]))
    if any(time_h > t_end_h + 1e-9 for time_h in sample_times):
        raise ValueError("All sampling times must fall within simulation.t_end_h.")
    if any(abs(round(time_h / dt_h) * dt_h - time_h) > 1e-9 for time_h in sample_times):
        raise ValueError("All sampling times must be on the dense simulation grid.")
    study_id = _study_id(config, spec)
    study_start = _study_start(config)
    output = Path(out_dir)
    drug_out = output / slug
    raw_dir = drug_out / "raw"
    workflow_dir = drug_out / "workflow"
    sim_csv = raw_dir / "sim_full.csv"
    dosing_csv = raw_dir / "dosing_events.csv"
    clinical_csv = workflow_dir / "raw" / "clinical_samples.csv"
    variability = simulation.get("variability") or {}
    if engine == "mrgsolve":
        sim_rows, dosing_rows = _generate_simulation_mrgsolve(
            spec_path=spec_path,
            spec=spec,
            out_csv=sim_csv,
            dosing_csv=dosing_csv,
            study_id=study_id,
            study_start=study_start,
            n_subjects=n_subjects,
            interval_h=interval_h,
            dose_count=dose_count,
            t_end_h=t_end_h,
            dt_h=dt_h,
            variability=variability,
        )
    else:
        sim_rows, dosing_rows = _generate_simulation(
            spec=spec,
            out_csv=sim_csv,
            dosing_csv=dosing_csv,
            study_id=study_id,
            study_start=study_start,
            n_subjects=n_subjects,
            interval_h=interval_h,
            dose_count=dose_count,
            t_end_h=t_end_h,
            dt_h=dt_h,
            variability=variability,
        )
    expected_dose_rows = n_subjects * dose_count
    if dosing_rows != expected_dose_rows:
        raise ValueError(
            f"Repeated simulation produced {dosing_rows} dose events; expected {expected_dose_rows}."
        )
    expected_observation_rows = n_subjects * len(_time_grid(t_end_h, dt_h))
    expected_sim_rows = expected_observation_rows + (expected_dose_rows if engine == "mrgsolve" else 0)
    if sim_rows != expected_sim_rows:
        raise ValueError(
            f"Repeated simulation produced {sim_rows} sim rows; expected {expected_sim_rows} for engine={engine}."
        )
    sampling_result = sample_clinical_timepoints(
        sim_csv,
        clinical_csv,
        times_h=sample_times,
        method="exact",
        predose_mdv1=False,
        seed=int(variability.get("seed", 20260217) or 20260217),
    )
    _enrich_samples(
        clinical_csv=clinical_csv,
        trough_times=trough_times,
        ss_after=ss_after,
        analysis_time_h=analysis_time_h,
        interval_h=interval_h,
        labels=labels,
        analysis_dose_number=analysis_dose_number,
    )
    sdtm_dir = workflow_dir / "sdtm_like"
    sdtm_result = make_sdtm_like_domains(
        clinical_samples_csv=clinical_csv,
        spec_yml=spec_path,
        out_dir=sdtm_dir,
        ex_csv=dosing_csv,
        study_start=study_start.isoformat(timespec="seconds"),
        seed=int(variability.get("seed", 20260217) or 20260217),
        pc_conc_col="DV",
        pc_conc_unit=conc_unit,
        strict_subject_match=True,
    )
    end_date = (study_start + timedelta(hours=t_end_h)).date().isoformat()
    _patch_dm_end_date(sdtm_result.files["DM"], end_date)
    analysis_dir = workflow_dir / "analysis_inputs"
    analysis_result = make_analysis_inputs(sdtm_like_dir=sdtm_dir, out_dir=analysis_dir)
    nca_config = config.get("nca") or {}
    partial_intervals = [
        (float(pair[0]), float(pair[1]))
        for pair in (nca_config.get("partial_intervals_h") or [(0.0, 4.0), (4.0, 12.0)])
    ]
    nca_result = make_repeated_nca(
        clinical_samples_csv=clinical_csv,
        out_dir=analysis_dir,
        analysis_dose_time_h=analysis_time_h,
        interval_h=interval_h,
        trough_times_h=trough_times,
        ss_times_after_dose_h=ss_after,
        partial_intervals_h=partial_intervals,
        concentration_col="DV",
    )
    model_qc_rows, model_qc_warnings = _make_model_qc(
        sim_csv=sim_csv,
        out_csv=analysis_dir / "MODEL_QC.csv",
        spec=spec,
        analysis_time_h=analysis_time_h,
        interval_h=interval_h,
        dose_mg=float(_arm_dose(spec, "A") or 0.0),
        rel_threshold=MODEL_QC_REL_THRESHOLD,
    )
    warnings = [*sdtm_result.warnings, *analysis_result.warnings, *nca_result.warnings, *model_qc_warnings]
    status = "WARN" if warnings else "OK"
    counts = {
        "subjects": n_subjects,
        "sim_full_rows": sim_rows,
        "dosing_event_rows": dosing_rows,
        "clinical_sample_rows": sampling_result.n_rows,
        "dm_rows": sdtm_result.counts["DM"],
        "ex_rows": sdtm_result.counts["EX"],
        "pc_rows": sdtm_result.counts["PC"],
        "vs_rows": sdtm_result.counts["VS"],
        "lb_rows": sdtm_result.counts["LB"],
        "adpc_rows": analysis_result.counts["adpc_rows"],
        "nca_input_rows": analysis_result.counts["nca_rows"],
        "trough_rows": nca_result.counts["trough_rows"],
        "ss_nca_rows": nca_result.counts["ss_nca_rows"],
        "model_qc_rows": model_qc_rows,
        "poppk_rows": analysis_result.counts["poppk_rows"],
    }
    validation_status = "WARN" if model_qc_warnings else "OK"
    workflow_artifacts = _write_repeated_workflow_artifacts(
        workflow_dir=workflow_dir,
        status=status,
        validation_status=validation_status,
        sim_csv=sim_csv,
        dosing_csv=dosing_csv,
        spec_path=spec_path,
        simulation_engine=engine,
        counts=counts,
        warnings=warnings,
    )
    summary_files = _write_summary(output, counts, status, warnings)
    demo_manifest = output / "DEMO_MANIFEST.yml"
    outputs = {
        "sim_full": sim_csv,
        "dosing_events": dosing_csv,
        "clinical_samples": clinical_csv,
        "dm_csv": sdtm_result.files["DM"],
        "ex_csv": sdtm_result.files["EX"],
        "pc_csv": sdtm_result.files["PC"],
        "adpc_csv": analysis_result.files["ADPC"],
        "nca_input_csv": analysis_result.files["NCA_INPUT"],
        "trough_input_csv": nca_result.files["TROUGH_INPUT"],
        "trough_summary_csv": nca_result.files["TROUGH_SUMMARY"],
        "nca_ss_input_csv": nca_result.files["NCA_SS_INPUT"],
        "nca_ss_summary_csv": nca_result.files["NCA_SS_SUMMARY"],
        "poppk_input_csv": analysis_result.files["POPPK_INPUT"],
        "model_qc_csv": analysis_dir / "MODEL_QC.csv",
        **summary_files,
        "sdtm_manifest": sdtm_result.files["MANIFEST"],
        "analysis_manifest": analysis_result.files["MANIFEST"],
        "nca_manifest": nca_result.files["MANIFEST"],
        **workflow_artifacts,
    }
    if engine == "mrgsolve":
        mrgsolve_manifest = Path(f"{sim_csv}.manifest.yml")
        if mrgsolve_manifest.exists():
            outputs["mrgsolve_manifest"] = mrgsolve_manifest
    _write_yaml(
        demo_manifest,
        {
            "purpose": "repeated_oral_trough_steady_state_demo_set",
            "status": status,
            "validation_status": validation_status,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "drug": slug,
            "study_id": study_id,
            "settings": {
                "n_subjects": n_subjects,
                "interval_h": interval_h,
                "dose_count": dose_count,
                "analysis_dose_number": analysis_dose_number,
                "analysis_dose_time_h": analysis_time_h,
                "t_end_h": t_end_h,
                "dt_h": dt_h,
                "trough_times_h": trough_times,
                "ss_times_after_dose_h": ss_after,
                "variability": variability,
                "simulation_engine": engine,
                "model_qc_rel_threshold": MODEL_QC_REL_THRESHOLD,
            },
            "outputs": {key: str(value) for key, value in outputs.items()},
            "counts": counts,
            "warnings": warnings,
            "validation": {
                "status": validation_status,
                "method": "repeated-dose model QC and NCA shape checks",
                "single_dose_validator": "not_used",
            },
            "notes": [
                "This is a repeated-dose workflow fixture, not a clinical steady-state qualification dataset.",
                "Dose events are the source of truth for EX and PopPK dosing rows.",
                "The canonical drug files are read-only inputs and are not modified.",
            ],
        },
    )
    outputs["manifest"] = demo_manifest
    return RepeatedOralDemoResult(out_dir=output, status=status, files=outputs, counts=counts, warnings=warnings)


def build_arg_parser() -> Any:
    parser = __import__("argparse").ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    config = _load_yaml(args.config)
    try:
        result = run_repeated_oral_demo(
            config=config,
            out_dir=config.get("out_dir"),
            drugs_dir=config.get("drugs_dir", "drugs"),
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Repeated oral demo: {result.status}")
    print(f"Output directory: {result.out_dir}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for key in sorted(result.files):
        print(f"{key}: {result.files[key]}")
    return 1 if result.status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
