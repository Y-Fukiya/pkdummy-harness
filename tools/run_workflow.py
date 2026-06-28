#!/usr/bin/env python3
"""Run the deterministic post-simulation PK fixture workflow.

This orchestrates existing tools after a dense `sim_full.csv` has been created:
1. validate PK simulation output
2. sample clinical nominal time points
3. generate limited SDTM-like DM/VS/LB/EX/PC CSVs
4. generate ADPC-like/NCA/PopPK smoke-test input CSVs
5. write a run-level manifest and trace log

It does not run mrgsolve and does not modify pk.yml, targets.yml, or specs.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.make_analysis_inputs import make_analysis_inputs
from tools.make_sdtm_like_domains import make_sdtm_like_domains
from tools.sample_clinical_timepoints import (
    Method,
    load_schedule_csv,
    parse_times,
    sample_clinical_timepoints,
)
from tools.check_value_provenance import build_value_provenance_summary
from tools.target_metadata import build_target_metadata
from tools.validate_simulation import (
    SimulationTolerances,
    render_markdown,
    validate_simulation_run,
)


@dataclass(frozen=True)
class WorkflowResult:
    out_dir: Path
    status: str
    validation_status: str
    files: dict[str, Path]
    counts: dict[str, int]
    warnings: list[str]


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_yaml(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)


def _write_trace(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _resolve_drug_paths(drug: str, *, drugs_dir: Path) -> tuple[Path, Path, Path]:
    drug_dir = drugs_dir / drug
    if not drug_dir.is_dir():
        raise ValueError(f"Drug directory not found: {drug_dir}")
    pk_yml = drug_dir / "pk.yml"
    targets_yml = drug_dir / "targets.yml"
    spec_files = sorted(drug_dir.glob("spec_pk1_*.yml"))
    if not pk_yml.exists():
        raise ValueError(f"pk.yml not found: {pk_yml}")
    if not targets_yml.exists():
        raise ValueError(f"targets.yml not found: {targets_yml}")
    if len(spec_files) != 1:
        raise ValueError(f"Expected exactly one spec_pk1_*.yml in {drug_dir}, found {len(spec_files)}")
    return pk_yml, targets_yml, spec_files[0]


def _workflow_manifest(
    *,
    status: str,
    sim_full: Path,
    pk_yml: Path,
    targets_yml: Path,
    spec_yml: Path,
    subjects_csv: Path | None,
    dm_csv: Path | None,
    vs_csv: Path | None,
    lb_csv: Path | None,
    ex_csv: Path | None,
    pc_csv: Path | None,
    validation_status: str,
    validation_attempts: int,
    files: dict[str, Path],
    counts: dict[str, int],
    warnings: list[str],
    settings: dict[str, Any],
    target_metadata: dict[str, Any],
    value_provenance_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "purpose": "pk_fixture_post_simulation_workflow",
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "sim_full_csv": str(sim_full),
            "pk_yml": str(pk_yml),
            "targets_yml": str(targets_yml),
            "spec_yml": str(spec_yml),
            "subjects_csv": str(subjects_csv) if subjects_csv else None,
            "dm_csv": str(dm_csv) if dm_csv else None,
            "vs_csv": str(vs_csv) if vs_csv else None,
            "lb_csv": str(lb_csv) if lb_csv else None,
            "ex_csv": str(ex_csv) if ex_csv else None,
            "pc_csv": str(pc_csv) if pc_csv else None,
        },
        "validation": {
            "status": validation_status,
            "attempts": validation_attempts,
        },
        "target_metadata": target_metadata,
        "value_provenance_summary": value_provenance_summary,
        "outputs": {key: str(value) for key, value in files.items()},
        "counts": counts,
        "warnings": warnings,
        "settings": settings,
        "safeguards": [
            "This workflow does not modify pk.yml, targets.yml, or spec files.",
            "Validation WARN/FAILED is recorded; canonical PK values are not calibrated automatically.",
            "SDTM-like outputs are workflow fixtures, not submission-ready SDTM/XPT datasets.",
            "Analysis input outputs are smoke-test fixtures, not submission-ready ADaM or model-specific NONMEM datasets.",
        ],
    }


def run_workflow(
    *,
    sim_full_csv: Path | str,
    out_dir: Path | str,
    pk_yml: Path | str | None = None,
    targets_yml: Path | str | None = None,
    spec_yml: Path | str | None = None,
    drug: str | None = None,
    drugs_dir: Path | str = "drugs",
    subjects_csv: Path | str | None = None,
    dm_csv: Path | str | None = None,
    vs_csv: Path | str | None = None,
    lb_csv: Path | str | None = None,
    ex_csv: Path | str | None = None,
    pc_csv: Path | str | None = None,
    times_h: list[float] | None = None,
    schedule_csv: Path | str | None = None,
    method: Method = "linear",
    nearest_window_h: float | None = None,
    jitter_min: float = 0.0,
    seed: int = 20260217,
    predose_mdv1: bool = False,
    study_start: str = "2026-01-01T08:00:00",
    pc_conc_col: str = "DV",
    pc_conc_unit: str | None = None,
    dose_cmt: str = "1",
    observation_cmt: str = "2",
    strict_subject_match: bool = False,
    overwrite_existing_pc_conc: bool = False,
    warn_rel: float = 0.25,
    fail_rel: float = 0.50,
    allow_validation_failed: bool = False,
) -> WorkflowResult:
    sim_path = Path(sim_full_csv)
    out_path = Path(out_dir)
    trace_path = out_path / "trace.log"
    manifest_path = out_path / "MANIFEST.yml"
    trace_lines = [f"{datetime.now().isoformat(timespec='seconds')} START workflow"]

    if drug and not (pk_yml and targets_yml and spec_yml):
        resolved_pk, resolved_targets, resolved_spec = _resolve_drug_paths(drug, drugs_dir=Path(drugs_dir))
        pk_path = Path(pk_yml) if pk_yml else resolved_pk
        targets_path = Path(targets_yml) if targets_yml else resolved_targets
        spec_path = Path(spec_yml) if spec_yml else resolved_spec
    elif pk_yml and targets_yml and spec_yml:
        pk_path = Path(pk_yml)
        targets_path = Path(targets_yml)
        spec_path = Path(spec_yml)
    else:
        raise ValueError("Provide either --drug or all of --pk, --targets, and --spec.")

    out_path.mkdir(parents=True, exist_ok=True)
    reports_dir = out_path / "reports"
    raw_dir = out_path / "raw"
    sdtm_dir = out_path / "sdtm_like"
    analysis_dir = out_path / "analysis_inputs"
    validation_md = reports_dir / "simulation_validation.md"
    clinical_samples = raw_dir / "clinical_samples.csv"
    pk_data = _load_yaml(pk_path)
    targets_data = _load_yaml(targets_path)
    target_metadata = build_target_metadata(drug, pk_data, targets_data)
    value_provenance_summary = build_value_provenance_summary(pk_data, targets_data)

    validation_run = validate_simulation_run(
        sim_path,
        pk_path,
        targets_path,
        tolerances=SimulationTolerances(warn_rel=warn_rel, fail_rel=fail_rel),
    )
    validation_result = validation_run.final_result
    reports_dir.mkdir(parents=True, exist_ok=True)
    validation_md.write_text(render_markdown(validation_result, sim_path, pk_path, targets_path, run=validation_run), encoding="utf-8")
    trace_lines.append(
        f"{datetime.now().isoformat(timespec='seconds')} VALIDATE status={validation_result.status} attempts={len(validation_run.attempts)}/1"
    )

    base_files = {
        "trace_log": trace_path,
        "manifest": manifest_path,
        "simulation_validation_md": validation_md,
    }
    warnings = list(validation_result.warnings)
    if validation_result.status == "FAILED" and not allow_validation_failed:
        warnings.extend(validation_result.failures)
        trace_lines.append(f"{datetime.now().isoformat(timespec='seconds')} STOP validation_failed")
        result = WorkflowResult(
            out_dir=out_path,
            status="FAILED",
            validation_status=validation_result.status,
            files=base_files,
            counts={},
            warnings=warnings,
        )
        _write_yaml(
            manifest_path,
            _workflow_manifest(
                status=result.status,
                sim_full=sim_path,
                pk_yml=pk_path,
                targets_yml=targets_path,
                spec_yml=spec_path,
                subjects_csv=Path(subjects_csv) if subjects_csv else None,
                dm_csv=Path(dm_csv) if dm_csv else None,
                vs_csv=Path(vs_csv) if vs_csv else None,
                lb_csv=Path(lb_csv) if lb_csv else None,
                ex_csv=Path(ex_csv) if ex_csv else None,
                pc_csv=Path(pc_csv) if pc_csv else None,
                validation_status=result.validation_status,
                validation_attempts=len(validation_run.attempts),
                files=result.files,
                counts=result.counts,
                warnings=result.warnings,
                settings={
                    "validation_mode": "single_deterministic",
                    "warn_rel": warn_rel,
                    "fail_rel": fail_rel,
                    "allow_validation_failed": allow_validation_failed,
                },
                target_metadata=target_metadata,
                value_provenance_summary=value_provenance_summary,
            ),
        )
        _write_trace(trace_path, trace_lines)
        return result
    if validation_result.status == "FAILED":
        warnings.extend(f"validation failure allowed: {failure}" for failure in validation_result.failures)

    schedule = load_schedule_csv(Path(schedule_csv)) if schedule_csv else None
    if schedule is None and not times_h:
        raise ValueError("Provide either times_h or schedule_csv.")
    sampling_result = sample_clinical_timepoints(
        sim_path,
        clinical_samples,
        times_h=times_h,
        schedule=schedule,
        method=method,
        nearest_window_h=nearest_window_h,
        jitter_min=jitter_min,
        seed=seed,
        predose_mdv1=predose_mdv1,
    )
    trace_lines.append(
        f"{datetime.now().isoformat(timespec='seconds')} SAMPLE rows={sampling_result.n_rows} method={sampling_result.method}"
    )

    sdtm_result = make_sdtm_like_domains(
        clinical_samples_csv=clinical_samples,
        spec_yml=spec_path,
        out_dir=sdtm_dir,
        subjects_csv=subjects_csv,
        dm_csv=dm_csv,
        vs_csv=vs_csv,
        lb_csv=lb_csv,
        ex_csv=ex_csv,
        pc_csv=pc_csv,
        study_start=study_start,
        seed=seed,
        pc_conc_col=pc_conc_col,
        pc_conc_unit=pc_conc_unit,
        strict_subject_match=strict_subject_match,
        overwrite_existing_pc_conc=overwrite_existing_pc_conc,
    )
    trace_lines.append(
        f"{datetime.now().isoformat(timespec='seconds')} SDTM_LIKE counts={sdtm_result.counts}"
    )

    analysis_result = make_analysis_inputs(
        sdtm_like_dir=sdtm_dir,
        out_dir=analysis_dir,
        dose_cmt=dose_cmt,
        observation_cmt=observation_cmt,
    )
    trace_lines.append(
        f"{datetime.now().isoformat(timespec='seconds')} ANALYSIS_INPUTS status={analysis_result.status} counts={analysis_result.counts}"
    )

    files = {
        **base_files,
        "clinical_samples_csv": clinical_samples,
        "sdtm_like_manifest": sdtm_result.files["MANIFEST"],
        "dm_csv": sdtm_result.files["DM"],
        "vs_csv": sdtm_result.files["VS"],
        "lb_csv": sdtm_result.files["LB"],
        "ex_csv": sdtm_result.files["EX"],
        "pc_csv": sdtm_result.files["PC"],
        "analysis_inputs_manifest": analysis_result.files["MANIFEST"],
        "adpc_csv": analysis_result.files["ADPC"],
        "nca_input_csv": analysis_result.files["NCA_INPUT"],
        "poppk_input_csv": analysis_result.files["POPPK_INPUT"],
    }
    has_provenance_review_gap = bool(value_provenance_summary.get("fields_needing_review"))
    status = (
        "WARN"
        if (
            validation_result.status != "OK"
            or sdtm_result.warnings
            or analysis_result.status != "OK"
            or has_provenance_review_gap
        )
        else "OK"
    )
    warnings.extend(sdtm_result.warnings)
    warnings.extend(analysis_result.warnings)
    counts = {
        "clinical_sample_rows": sampling_result.n_rows,
        "clinical_sample_subjects": sampling_result.n_subjects,
        "clinical_sample_timepoints": sampling_result.n_timepoints,
        **{f"sdtm_like_{key.lower()}_rows": value for key, value in sdtm_result.counts.items()},
        **{f"analysis_{key}": value for key, value in analysis_result.counts.items()},
    }
    result = WorkflowResult(
        out_dir=out_path,
        status=status,
        validation_status=validation_result.status,
        files=files,
        counts=counts,
        warnings=warnings,
    )
    trace_lines.append(f"{datetime.now().isoformat(timespec='seconds')} END status={result.status}")
    _write_yaml(
        manifest_path,
        _workflow_manifest(
            status=result.status,
            sim_full=sim_path,
            pk_yml=pk_path,
            targets_yml=targets_path,
            spec_yml=spec_path,
            subjects_csv=Path(subjects_csv) if subjects_csv else None,
            dm_csv=Path(dm_csv) if dm_csv else None,
            vs_csv=Path(vs_csv) if vs_csv else None,
            lb_csv=Path(lb_csv) if lb_csv else None,
            ex_csv=Path(ex_csv) if ex_csv else None,
            pc_csv=Path(pc_csv) if pc_csv else None,
            validation_status=result.validation_status,
            validation_attempts=len(validation_run.attempts),
            files=result.files,
            counts=result.counts,
            warnings=result.warnings,
            settings={
                "times_h": times_h,
                "schedule_csv": str(schedule_csv) if schedule_csv else None,
                "method": method,
                "nearest_window_h": nearest_window_h,
                "jitter_min": jitter_min,
                "predose_mdv1": predose_mdv1,
                "seed": seed,
                "study_start": study_start,
                "pc_conc_col": pc_conc_col,
                "pc_conc_unit": pc_conc_unit,
                "dose_cmt": dose_cmt,
                "observation_cmt": observation_cmt,
                "strict_subject_match": strict_subject_match,
                "overwrite_existing_pc_conc": overwrite_existing_pc_conc,
                "validation_mode": "single_deterministic",
                "warn_rel": warn_rel,
                "fail_rel": fail_rel,
                "allow_validation_failed": allow_validation_failed,
            },
            target_metadata=target_metadata,
            value_provenance_summary=value_provenance_summary,
        ),
    )
    _write_trace(trace_path, trace_lines)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sim-full", required=True, type=Path, help="Dense raw/sim_full.csv from an external simulation runner")
    parser.add_argument("--out-dir", required=True, type=Path, help="Workflow output directory")
    parser.add_argument("--drug", default=None, help="Drug slug under drugs/. Used to infer pk/targets/spec")
    parser.add_argument("--drugs-dir", type=Path, default=Path("drugs"))
    parser.add_argument("--pk", type=Path, default=None, help="Explicit pk.yml")
    parser.add_argument("--targets", type=Path, default=None, help="Explicit targets.yml")
    parser.add_argument("--spec", type=Path, default=None, help="Explicit spec_pk1_*.yml")
    parser.add_argument("--subjects-csv", type=Path, default=None)
    parser.add_argument("--dm-csv", type=Path, default=None, help="Optional existing DM CSV to reuse")
    parser.add_argument("--vs-csv", type=Path, default=None, help="Optional existing VS CSV to reuse")
    parser.add_argument("--lb-csv", type=Path, default=None, help="Optional existing LB CSV to reuse")
    parser.add_argument("--ex-csv", type=Path, default=None, help="Optional existing EX CSV to reuse")
    parser.add_argument("--pc-csv", type=Path, default=None, help="Optional existing PC skeleton CSV to fill with concentrations")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--times", help="Comma-separated nominal sampling times in hours")
    group.add_argument("--schedule-csv", type=Path, help="CSV with NOMTIME_H and optional TPT/TPTNUM")
    parser.add_argument("--method", choices=["exact", "nearest", "linear", "log-linear"], default="linear")
    parser.add_argument("--nearest-window-h", type=float, default=None)
    parser.add_argument("--jitter-min", type=float, default=0.0)
    parser.add_argument("--predose-mdv1", action="store_true", help="Mark nominal predose samples as MDV=1 in downstream PopPK fixtures.")
    parser.add_argument("--seed", type=int, default=20260217)
    parser.add_argument("--study-start", default="2026-01-01T08:00:00")
    parser.add_argument("--pc-conc-col", default="DV")
    parser.add_argument("--pc-conc-unit", default=None, help="Optional concentration unit override for generated PC units")
    parser.add_argument("--dose-cmt", default="1", help="CMT value for PopPK dosing rows")
    parser.add_argument("--observation-cmt", default="2", help="CMT value for PopPK observation rows")
    parser.add_argument("--strict-subject-match", action="store_true")
    parser.add_argument("--overwrite-existing-pc-conc", action="store_true")
    parser.add_argument("--warn-rel", type=float, default=0.25)
    parser.add_argument("--fail-rel", type=float, default=0.50)
    parser.add_argument("--allow-validation-failed", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = run_workflow(
            sim_full_csv=args.sim_full,
            out_dir=args.out_dir,
            pk_yml=args.pk,
            targets_yml=args.targets,
            spec_yml=args.spec,
            drug=args.drug,
            drugs_dir=args.drugs_dir,
            subjects_csv=args.subjects_csv,
            dm_csv=args.dm_csv,
            vs_csv=args.vs_csv,
            lb_csv=args.lb_csv,
            ex_csv=args.ex_csv,
            pc_csv=args.pc_csv,
            times_h=parse_times(args.times) if args.times else None,
            schedule_csv=args.schedule_csv,
            method=args.method,
            nearest_window_h=args.nearest_window_h,
            jitter_min=args.jitter_min,
            predose_mdv1=args.predose_mdv1,
            seed=args.seed,
            study_start=args.study_start,
            pc_conc_col=args.pc_conc_col,
            pc_conc_unit=args.pc_conc_unit,
            dose_cmt=args.dose_cmt,
            observation_cmt=args.observation_cmt,
            strict_subject_match=args.strict_subject_match,
            overwrite_existing_pc_conc=args.overwrite_existing_pc_conc,
            warn_rel=args.warn_rel,
            fail_rel=args.fail_rel,
            allow_validation_failed=args.allow_validation_failed,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Workflow: {result.status}")
    print(f"Validation: {result.validation_status}")
    print(f"Output directory: {result.out_dir}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for key in sorted(result.files):
        print(f"{key}: {result.files[key]}")
    return 1 if result.status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
