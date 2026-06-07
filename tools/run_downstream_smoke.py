#!/usr/bin/env python3
"""Run fixture-level downstream E2E smoke checks for NCA and PopPK inputs."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.make_downstream_adapters import make_downstream_adapters
from tools.validate_downstream_adapters import AdapterValidationResult, validate_adapter_dir


@dataclass(frozen=True)
class DownstreamSmokeResult:
    out_dir: Path
    status: str
    files: dict[str, Path]
    counts: dict[str, int]
    warnings: list[str]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV is empty: {path}")
        return list(reader)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row.get(field, "")) for field in fieldnames})


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_yaml(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)


def _to_float(value: Any) -> float | None:
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


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return _format_number(value)
    return str(value)


def _linear_auc(points: list[tuple[float, float]]) -> float:
    auc = 0.0
    for (t0, c0), (t1, c1) in zip(points, points[1:]):
        auc += (t1 - t0) * (c0 + c1) / 2.0
    return auc


def _nca_rows(analysis_dir: Path) -> list[dict[str, str]]:
    nca_path = analysis_dir / "NCA_INPUT.csv"
    if nca_path.exists():
        return _read_csv(nca_path)
    adpc_rows = _read_csv(analysis_dir / "ADPC.csv")
    return [
        {
            "USUBJID": row.get("USUBJID", ""),
            "TIME_H": row.get("TIME_H", ""),
            "CONC": row.get("AVAL", ""),
            "CONC_UNIT": row.get("AVALU", ""),
            "DOSE_MG": row.get("DOSE_MG", ""),
            "ROUTE": row.get("ROUTE", ""),
        }
        for row in adpc_rows
    ]


def _make_nca_summary(analysis_dir: Path, out_csv: Path) -> tuple[int, list[str]]:
    rows = _nca_rows(analysis_dir)
    by_subject: dict[str, list[dict[str, str]]] = {}
    warnings: list[str] = []
    for row in rows:
        by_subject.setdefault(str(row.get("USUBJID") or "").strip(), []).append(row)

    out_rows: list[dict[str, Any]] = []
    for usubjid in sorted(subject for subject in by_subject if subject):
        subject_rows = by_subject[usubjid]
        points: list[tuple[float, float]] = []
        for row in subject_rows:
            time_h = _to_float(row.get("TIME_H"))
            conc = _to_float(row.get("CONC"))
            if time_h is not None and conc is not None:
                points.append((time_h, conc))
        points = sorted(points)
        if len(points) < 2:
            warnings.append(f"{usubjid}: fewer than 2 usable NCA points")
            continue
        cmax_time, cmax = max(points, key=lambda point: point[1])
        first = subject_rows[0]
        out_rows.append(
            {
                "USUBJID": usubjid,
                "N_POINTS": len(points),
                "CMAX": cmax,
                "TMAX_H": cmax_time,
                "AUCLAST": _linear_auc(points),
                "AUC_UNIT": f"{first.get('CONC_UNIT', 'ng/mL')}*h",
                "DOSE_MG": first.get("DOSE_MG", ""),
                "ROUTE": first.get("ROUTE", ""),
            }
        )
    if not out_rows:
        raise ValueError("No subjects had enough concentration-time points for NCA smoke summary.")
    _write_csv(out_csv, out_rows, ["USUBJID", "N_POINTS", "CMAX", "TMAX_H", "AUCLAST", "AUC_UNIT", "DOSE_MG", "ROUTE"])
    return len(out_rows), warnings


def _make_poppk_smoke(analysis_dir: Path, summary_yml: Path, nonmem_ctl: Path, nlmixr2_r: Path) -> tuple[int, list[str]]:
    rows = _read_csv(analysis_dir / "POPPK_INPUT.csv")
    warnings: list[str] = []
    by_id: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_id.setdefault(str(row.get("ID") or "").strip(), []).append(row)
    if not by_id:
        raise ValueError("POPPK_INPUT.csv has no ID values.")

    subject_summaries: list[dict[str, Any]] = []
    for subject_id in sorted(by_id, key=lambda value: int(value) if value.isdigit() else value):
        subject_rows = by_id[subject_id]
        dose_rows = [row for row in subject_rows if str(row.get("EVID")).strip() == "1"]
        obs_rows = [row for row in subject_rows if str(row.get("EVID")).strip() == "0"]
        if not dose_rows:
            warnings.append(f"ID {subject_id}: no dose row")
        if not obs_rows:
            warnings.append(f"ID {subject_id}: no observation rows")
        subject_summaries.append(
            {
                "id": subject_id,
                "usubjid": subject_rows[0].get("USUBJID", ""),
                "dose_rows": len(dose_rows),
                "observation_rows": len(obs_rows),
            }
        )

    _write_yaml(
        summary_yml,
        {
            "purpose": "poppk_parser_smoke_summary",
            "status": "WARN" if warnings else "OK",
            "subjects": subject_summaries,
            "warnings": warnings,
            "notes": [
                "This confirms parser/control-template readiness only.",
                "It does not run NONMEM, nlmixr2, or parameter estimation.",
            ],
        },
    )
    _write_text(
        nonmem_ctl,
        "\n".join(
            [
                "$PROBLEM PK fixture parser smoke template",
                "$INPUT ID TIME EVID MDV AMT DV CMT RATE DOSE ROUTE WT AGE SEX BSA CREAT USUBJID",
                "$DATA poppk_nonmem.csv IGNORE=@",
                "$SUBROUTINES ADVAN2 TRANS2",
                "$PK",
                "CL = THETA(1)",
                "V  = THETA(2)",
                "S2 = V",
                "$ERROR",
                "Y = F",
                "$THETA (0, 1) (0, 10)",
                "$ESTIMATION MAXEVAL=0",
                "",
            ]
        ),
    )
    _write_text(
        nlmixr2_r,
        "\n".join(
            [
                "# nlmixr2 parser smoke template for poppk_nlmixr2.csv",
                "model <- function() {",
                "  ini({",
                "    tcl <- log(1)",
                "    tv <- log(10)",
                "    add.err <- 1",
                "  })",
                "  model({",
                "    cl <- exp(tcl)",
                "    v <- exp(tv)",
                "    d/dt(central) <- -cl / v * central",
                "    cp <- central / v",
                "    cp ~ add(add.err)",
                "  })",
                "}",
                "",
            ]
        ),
    )
    return len(by_id), warnings


def _adapter_payload(result: AdapterValidationResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "files_checked": result.files_checked,
        "issues": result.issues,
        "warnings": result.warnings,
    }


def run_downstream_smoke(*, analysis_dir: Path | str, out_dir: Path | str) -> DownstreamSmokeResult:
    analysis_path = Path(analysis_dir)
    out_path = Path(out_dir)
    adapter_dir = out_path / "adapters"
    nca_dir = out_path / "nca_smoke"
    poppk_dir = out_path / "poppk_smoke"
    manifest = out_path / "DOWNSTREAM_SMOKE_MANIFEST.yml"

    adapter_result = make_downstream_adapters(analysis_dir=analysis_path, out_dir=adapter_dir)
    adapter_validation = validate_adapter_dir(adapter_dir)
    nca_subjects, nca_warnings = _make_nca_summary(analysis_path, nca_dir / "NCA_SUMMARY.csv")
    poppk_subjects, poppk_warnings = _make_poppk_smoke(
        analysis_path,
        poppk_dir / "POPPK_PARSE_SUMMARY.yml",
        poppk_dir / "nonmem_parser_template.ctl",
        poppk_dir / "nlmixr2_parser_template.R",
    )
    warnings = list(adapter_result.warnings) + list(adapter_validation.warnings) + nca_warnings + poppk_warnings
    if adapter_validation.status == "FAILED":
        warnings.extend(adapter_validation.issues)
    status = "FAILED" if adapter_validation.status == "FAILED" else "WARN" if warnings else "OK"
    files = {
        "manifest": manifest,
        "adapter_manifest": adapter_result.files["manifest"],
        "nca_summary_csv": nca_dir / "NCA_SUMMARY.csv",
        "poppk_summary_yml": poppk_dir / "POPPK_PARSE_SUMMARY.yml",
        "nonmem_control_template": poppk_dir / "nonmem_parser_template.ctl",
        "nlmixr2_model_template": poppk_dir / "nlmixr2_parser_template.R",
    }
    counts = {
        "adapter_targets": adapter_result.counts["targets"],
        "nca_subjects": nca_subjects,
        "poppk_subjects": poppk_subjects,
    }
    _write_yaml(
        manifest,
        {
            "purpose": "downstream_e2e_smoke_fixture",
            "status": status,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "inputs": {"analysis_dir": str(analysis_path)},
            "outputs": {key: str(path) for key, path in files.items()},
            "counts": counts,
            "adapter_validation": _adapter_payload(adapter_validation),
            "warnings": warnings,
            "limitations": [
                "This is a fixture-level E2E smoke check, not a certified Phoenix, NONMEM, or nlmixr2 validation.",
                "NCA summary uses simple linear trapezoidal AUClast for parser/workflow confirmation.",
                "PopPK smoke writes parser/control templates and does not run external estimation software.",
            ],
        },
    )
    return DownstreamSmokeResult(out_path, status, files, counts, warnings)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        result = run_downstream_smoke(analysis_dir=args.analysis_dir, out_dir=args.out_dir)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Downstream smoke: {result.status}")
    print(f"Output directory: {result.out_dir}")
    for key in sorted(result.files):
        print(f"{key}: {result.files[key]}")
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    return 1 if result.status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
