#!/usr/bin/env python3
"""Run a multi-drug demo set through the PK fixture workflow.

This tool creates deterministic demo-only `sim_full.csv` files from existing
1-compartment specs, then runs `tools/run_workflow.py` for each drug. It is a
smoke-test/demo harness for downstream SDTM-like -> ADPC/NCA/PopPK workflow
connections. It is not a replacement for an mrgsolve runner.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from tools.run_workflow import WorkflowResult, run_workflow
from tools.sample_clinical_timepoints import parse_times


DEFAULT_DEMO_DRUGS = ["albuterol", "alprazolam", "aciclovir", "abciximab", "felodipine"]
DEFAULT_SAMPLE_TIMES_H = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 12.0, 24.0]


@dataclass(frozen=True)
class DemoSetResult:
    out_dir: Path
    status: str
    files: dict[str, Path]
    counts: dict[str, int]
    workflows: dict[str, WorkflowResult]
    warnings: list[str]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_yaml(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row.get(field, "")) for field in fieldnames})


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


def _to_float(value: object, default: float | None = None) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolve_drug_files(drugs_dir: Path, slug: str) -> tuple[Path, Path, Path]:
    drug_dir = drugs_dir / slug
    pk_yml = drug_dir / "pk.yml"
    targets_yml = drug_dir / "targets.yml"
    spec_files = sorted(drug_dir.glob("spec_pk1_*.yml"))
    if not drug_dir.is_dir():
        raise ValueError(f"Drug directory not found: {drug_dir}")
    if not pk_yml.exists():
        raise ValueError(f"pk.yml not found: {pk_yml}")
    if not targets_yml.exists():
        raise ValueError(f"targets.yml not found: {targets_yml}")
    if len(spec_files) != 1:
        raise ValueError(f"Expected exactly one spec_pk1_*.yml in {drug_dir}, found {len(spec_files)}")
    return pk_yml, targets_yml, spec_files[0]


def _time_grid(spec: dict[str, Any]) -> list[float]:
    sampling = spec.get("sampling") or {}
    t_end = _to_float(sampling.get("t_end_h"), 24.0) or 24.0
    dt = _to_float(sampling.get("dt_h"), 0.5) or 0.5
    include_t0 = bool(sampling.get("include_t0", True))
    if dt <= 0:
        raise ValueError("sampling.dt_h must be positive.")
    times: list[float] = [0.0] if include_t0 else []
    current = dt
    while current <= t_end + 1e-9:
        times.append(round(current, 10))
        current += dt
    if not times:
        raise ValueError("Sampling settings produced no time points.")
    return times


def _arms(spec: dict[str, Any]) -> list[tuple[str, int, float]]:
    regimen = spec.get("regimen") or {}
    arms = regimen.get("arms") or {"A": {"n": (spec.get("population") or {}).get("n", 1), "dose_mg": 100.0}}
    out: list[tuple[str, int, float]] = []
    for arm, block in arms.items():
        n = int(_to_float((block or {}).get("n"), (spec.get("population") or {}).get("n", 1)) or 1)
        dose = _to_float((block or {}).get("dose_mg"), 100.0) or 100.0
        out.append((str(arm), n, dose))
    return out


def _is_oral(spec: dict[str, Any]) -> bool:
    route = str(((spec.get("regimen") or {}).get("route")) or "").strip().lower()
    template = str(((spec.get("model") or {}).get("template")) or "").strip().lower()
    return route in {"oral", "po"} or "oral" in template


def _concentration_ng_ml(spec: dict[str, Any], *, dose_mg: float, time_h: float) -> float:
    model = spec.get("model") or {}
    theta = model.get("theta") or {}
    units = model.get("units") or {}
    cl = _to_float(theta.get("CL"))
    v = _to_float(theta.get("V"))
    mult = _to_float(units.get("mult"), 1000.0) or 1000.0
    if cl is None or v is None or cl <= 0 or v <= 0:
        raise ValueError("model.theta.CL and model.theta.V must be positive for demo simulation.")
    ke = cl / v
    if _is_oral(spec):
        ka = _to_float(theta.get("KA"), 1.0) or 1.0
        f1 = _to_float(theta.get("F1"), 1.0) or 1.0
        alag = _to_float(theta.get("ALAG1"), 0.0) or 0.0
        tau = time_h - alag
        if tau <= 0:
            return 0.0
        if abs(ka - ke) <= 1e-9:
            conc_mg_l = f1 * dose_mg / v * ka * tau * math.exp(-ke * tau)
        else:
            conc_mg_l = f1 * dose_mg * ka / (v * (ka - ke)) * (math.exp(-ke * tau) - math.exp(-ka * tau))
        return max(0.0, conc_mg_l * mult)
    return max(0.0, dose_mg / v * math.exp(-ke * time_h) * mult)


def _subject_row_values(study_id: str, subject_index: int, arm: str, dose_mg: float) -> dict[str, Any]:
    sex = "M" if subject_index % 2 else "F"
    wt = 70.0 + ((subject_index % 5) - 2) * 3.0
    age = 40 + (subject_index % 20)
    return {
        "ID": subject_index,
        "ARM": arm,
        "WT": wt,
        "AGE": age,
        "SEX_CHAR": sex,
        "DOSE_MG": dose_mg,
        "STUDYID": study_id,
        "USUBJID": f"{study_id}-{subject_index:03d}",
    }


def make_demo_sim_full(
    *,
    spec_yml: Path | str,
    out_csv: Path | str,
) -> Path:
    spec_path = Path(spec_yml)
    out_path = Path(out_csv)
    spec = _load_yaml(spec_path)
    study_id = str(((spec.get("study") or {}).get("id")) or spec_path.parent.name)
    rows: list[dict[str, Any]] = []
    subject_index = 1
    for arm, n_subjects, dose_mg in _arms(spec):
        for _ in range(n_subjects):
            subject = _subject_row_values(study_id, subject_index, arm, dose_mg)
            for time_h in _time_grid(spec):
                conc = _concentration_ng_ml(spec, dose_mg=dose_mg, time_h=time_h)
                rows.append(
                    {
                        **subject,
                        "time": time_h,
                        "evid": 0,
                        "MDV": 0,
                        "amt": 0,
                        "CP": conc,
                        "DV": conc,
                    }
                )
            subject_index += 1
    _write_csv(
        out_path,
        rows,
        ["ID", "time", "evid", "MDV", "amt", "CP", "DV", "ARM", "WT", "AGE", "SEX_CHAR", "DOSE_MG", "STUDYID", "USUBJID"],
    )
    return out_path


def _summary_row(slug: str, workflow: WorkflowResult) -> dict[str, Any]:
    return {
        "drug": slug,
        "workflow_status": workflow.status,
        "validation_status": workflow.validation_status,
        "clinical_sample_rows": workflow.counts.get("clinical_sample_rows", ""),
        "sdtm_like_pc_rows": workflow.counts.get("sdtm_like_pc_rows", ""),
        "analysis_adpc_rows": workflow.counts.get("analysis_adpc_rows", ""),
        "analysis_nca_rows": workflow.counts.get("analysis_nca_rows", ""),
        "analysis_poppk_rows": workflow.counts.get("analysis_poppk_rows", ""),
        "warnings_n": len(workflow.warnings),
        "warnings": " | ".join(workflow.warnings),
        "run_dir": workflow.out_dir,
    }


def _write_summary_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Multi-drug Demo Summary",
        "",
        "These outputs are workflow smoke-test fixtures. They are not clinical validation outputs.",
        "",
        "| Drug | Workflow | Validation | ADPC rows | NCA rows | PopPK rows | Warnings |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {drug} | {workflow_status} | {validation_status} | {analysis_adpc_rows} | "
            "{analysis_nca_rows} | {analysis_poppk_rows} | {warnings_n} |".format(**row)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_demo_set(
    *,
    drugs: list[str],
    out_dir: Path | str,
    drugs_dir: Path | str = "drugs",
    sample_times_h: list[float] | None = None,
    allow_validation_failed: bool = True,
) -> DemoSetResult:
    if not drugs:
        raise ValueError("At least one drug slug is required.")
    out_path = Path(out_dir)
    drugs_path = Path(drugs_dir)
    times = sample_times_h or DEFAULT_SAMPLE_TIMES_H
    workflows: dict[str, WorkflowResult] = {}
    summary_rows: list[dict[str, Any]] = []
    all_warnings: list[str] = []

    for slug in drugs:
        _, _, spec_yml = _resolve_drug_files(drugs_path, slug)
        drug_out = out_path / slug
        sim_full = drug_out / "raw" / "sim_full.csv"
        make_demo_sim_full(spec_yml=spec_yml, out_csv=sim_full)
        workflow = run_workflow(
            sim_full_csv=sim_full,
            out_dir=drug_out / "workflow",
            drug=slug,
            drugs_dir=drugs_path,
            times_h=times,
            allow_validation_failed=allow_validation_failed,
        )
        workflows[slug] = workflow
        summary_rows.append(_summary_row(slug, workflow))
        all_warnings.extend(f"{slug}: {warning}" for warning in workflow.warnings)

    summary_csv = out_path / "summary.csv"
    summary_md = out_path / "summary.md"
    manifest = out_path / "DEMO_MANIFEST.yml"
    summary_fields = [
        "drug",
        "workflow_status",
        "validation_status",
        "clinical_sample_rows",
        "sdtm_like_pc_rows",
        "analysis_adpc_rows",
        "analysis_nca_rows",
        "analysis_poppk_rows",
        "warnings_n",
        "warnings",
        "run_dir",
    ]
    _write_csv(summary_csv, summary_rows, summary_fields)
    _write_summary_md(summary_md, summary_rows)

    if any(workflow.status == "FAILED" for workflow in workflows.values()):
        status = "FAILED"
    elif any(workflow.status == "WARN" or workflow.validation_status != "OK" for workflow in workflows.values()):
        status = "WARN"
    else:
        status = "OK"

    files = {
        "summary_csv": summary_csv,
        "summary_md": summary_md,
        "manifest": manifest,
    }
    counts = {
        "drugs": len(drugs),
        "ok_workflows": sum(1 for workflow in workflows.values() if workflow.status == "OK"),
        "warn_workflows": sum(1 for workflow in workflows.values() if workflow.status == "WARN"),
        "failed_workflows": sum(1 for workflow in workflows.values() if workflow.status == "FAILED"),
    }
    _write_yaml(
        manifest,
        {
            "purpose": "multi_drug_demo_set",
            "status": status,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "drugs": drugs,
            "settings": {
                "drugs_dir": str(drugs_path),
                "sample_times_h": times,
                "allow_validation_failed": allow_validation_failed,
                "demo_simulator": "analytical_1comp_fixture_generator_not_mrgsolve",
            },
            "outputs": {key: str(value) for key, value in files.items()},
            "counts": counts,
            "warnings": all_warnings,
            "notes": [
                "Demo sim_full.csv files are generated from existing spec theta values for workflow smoke testing.",
                "This tool does not modify pk.yml, targets.yml, or spec files.",
                "Use an external mrgsolve runner for production-like simulation demos.",
            ],
        },
    )
    return DemoSetResult(
        out_dir=out_path,
        status=status,
        files=files,
        counts=counts,
        workflows=workflows,
        warnings=all_warnings,
    )


def _parse_drugs(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drugs", default=",".join(DEFAULT_DEMO_DRUGS), help="Comma-separated drug slugs")
    parser.add_argument("--drugs-dir", type=Path, default=Path("drugs"))
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/demo_set_milestone7"))
    parser.add_argument("--times", default=",".join(_format_number(t) for t in DEFAULT_SAMPLE_TIMES_H))
    parser.add_argument(
        "--stop-on-validation-failed",
        action="store_true",
        help="Do not continue run_workflow outputs when validation is FAILED.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = run_demo_set(
            drugs=_parse_drugs(args.drugs),
            drugs_dir=args.drugs_dir,
            out_dir=args.out_dir,
            sample_times_h=parse_times(args.times),
            allow_validation_failed=not args.stop_on_validation_failed,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Demo set: {result.status}")
    print(f"Output directory: {result.out_dir}")
    print(f"summary_csv: {result.files['summary_csv']}")
    print(f"summary_md: {result.files['summary_md']}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    return 1 if result.status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
