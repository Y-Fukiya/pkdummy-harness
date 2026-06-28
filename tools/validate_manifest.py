#!/usr/bin/env python3
"""Validate PK fixture harness MANIFEST.yml files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


REQUIRED_FIELDS = ["purpose", "status", "outputs"]
WORKFLOW_REQUIRED_FIELDS = ["purpose", "status", "outputs", "target_metadata", "value_provenance_summary"]
SDTM_LIKE_REQUIRED_FIELDS = ["purpose", "domains", "inputs"]
WORKFLOW_PURPOSE = "pk_fixture_post_simulation_workflow"
SDTM_LIKE_PURPOSE = "workflow_fixture_not_submission_ready_sdtm"
ALLOWED_STATUS = {"OK", "WARN", "FAILED"}
ALLOWED_T_HALF_ATTAINABILITY_STATUS = {"NA", "OK", "WARN"}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = yaml.safe_load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"{path.name}: manifest must be a mapping")
    return obj


def _is_number_or_none(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return value is None
    return isinstance(value, (int, float))


def _validate_target_metadata(obj: Any, *, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(obj, dict):
        return [f"{label}: target_metadata must be a mapping"]

    auc = obj.get("auc")
    if not isinstance(auc, dict):
        issues.append(f"{label}: target_metadata.auc must be a mapping")
    else:
        basis = auc.get("basis")
        if basis is None or not str(basis).strip():
            issues.append(f"{label}: target_metadata.auc.basis must be non-empty")
        independent = auc.get("independent_literature_target")
        if independent is not None and not isinstance(independent, bool):
            issues.append(f"{label}: target_metadata.auc.independent_literature_target must be boolean or null")
        if basis == "dose_over_cl" and independent is True:
            issues.append(f"{label}: target_metadata.auc dose_over_cl cannot be an independent literature target")

    t_half = obj.get("t_half")
    if not isinstance(t_half, dict):
        issues.append(f"{label}: target_metadata.t_half must be a mapping")
    else:
        status = t_half.get("attainability_status")
        if status not in ALLOWED_T_HALF_ATTAINABILITY_STATUS:
            issues.append(
                f"{label}: target_metadata.t_half.attainability_status must be one of {sorted(ALLOWED_T_HALF_ATTAINABILITY_STATUS)}"
            )
        for field in ("detected_structural_mismatch", "acknowledged_structural_mismatch"):
            if not isinstance(t_half.get(field), bool):
                issues.append(f"{label}: target_metadata.t_half.{field} must be boolean")
        if "relative_error" not in t_half:
            issues.append(f"{label}: target_metadata.t_half.relative_error must be numeric or null")
        elif not _is_number_or_none(t_half.get("relative_error")):
            issues.append(f"{label}: target_metadata.t_half.relative_error must be numeric or null")
    return issues


def _validate_value_provenance_summary(obj: Any, *, status: Any, label: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(obj, dict):
        return [f"{label}: value_provenance_summary must be a mapping"]

    for field in (
        "scope",
        "provenance_required",
        "required_fields",
        "checked_fields",
        "fields_needing_review",
        "source_ids",
        "mismatch_acknowledged_fields",
    ):
        if field not in obj:
            issues.append(f"{label}: value_provenance_summary.{field} is required")
        elif field == "scope" and not str(obj.get(field) or "").strip():
            issues.append(f"{label}: value_provenance_summary.scope must be non-empty")
        elif field == "provenance_required" and not isinstance(obj.get(field), bool):
            issues.append(f"{label}: value_provenance_summary.provenance_required must be boolean")
        elif field not in {"scope", "provenance_required"} and not isinstance(obj.get(field), list):
            issues.append(f"{label}: value_provenance_summary.{field} must be a list")

    required = obj.get("required_fields")
    checked = obj.get("checked_fields")
    provenance_required = obj.get("provenance_required") is True
    if provenance_required and isinstance(required, list) and not required:
        issues.append(f"{label}: value_provenance_summary.required_fields must be non-empty")
    if isinstance(required, list) and isinstance(checked, list) and not set(required).issubset(set(checked)):
        issues.append(f"{label}: value_provenance_summary.checked_fields must include required_fields")
    fields_needing_review = obj.get("fields_needing_review")
    if isinstance(fields_needing_review, list) and fields_needing_review and status == "OK":
        issues.append(f"{label}: status must be WARN when value_provenance_summary.fields_needing_review is non-empty")
    return issues


def validate_manifest_obj(obj: dict[str, Any], *, label: str = "MANIFEST.yml") -> list[str]:
    issues: list[str] = []
    purpose = str(obj.get("purpose") or "")
    if purpose == WORKFLOW_PURPOSE:
        required_fields = WORKFLOW_REQUIRED_FIELDS
    elif purpose == SDTM_LIKE_PURPOSE:
        required_fields = SDTM_LIKE_REQUIRED_FIELDS
    else:
        required_fields = REQUIRED_FIELDS
    for field in required_fields:
        if field not in obj:
            issues.append(f"{label}: missing required field: {field}")
    status = obj.get("status")
    if status is not None and status not in ALLOWED_STATUS:
        issues.append(f"{label}: status must be one of {sorted(ALLOWED_STATUS)}, got {status!r}")
    if "purpose" in obj and not str(obj.get("purpose") or "").strip():
        issues.append(f"{label}: purpose must be non-empty")
    for field in ("inputs", "outputs", "counts", "render"):
        if field in obj and not isinstance(obj.get(field), dict):
            issues.append(f"{label}: {field} must be a mapping")
    if "domains" in obj:
        domains = obj.get("domains")
        if purpose == SDTM_LIKE_PURPOSE:
            if not isinstance(domains, (dict, list)):
                issues.append(f"{label}: domains must be a mapping or list")
        elif not isinstance(domains, dict):
            issues.append(f"{label}: domains must be a mapping")
    if "warnings" in obj and not isinstance(obj.get("warnings"), list):
        issues.append(f"{label}: warnings must be a list")
    if "safeguards" in obj and not isinstance(obj.get("safeguards"), list):
        issues.append(f"{label}: safeguards must be a list")
    if "target_metadata" in obj:
        issues.extend(_validate_target_metadata(obj.get("target_metadata"), label=label))
    if "value_provenance_summary" in obj:
        issues.extend(
            _validate_value_provenance_summary(
                obj.get("value_provenance_summary"),
                status=status,
                label=label,
            )
        )
    return issues


def validate_manifest_file(path: Path | str) -> list[str]:
    manifest_path = Path(path)
    try:
        obj = _load_yaml(manifest_path)
    except Exception as exc:
        return [f"{manifest_path.name}: {exc}"]
    return validate_manifest_obj(obj, label=manifest_path.name)


def _collect_paths(paths: list[Path], *, recursive: bool) -> list[Path]:
    out: list[Path] = []
    for path in paths:
        if path.is_dir():
            pattern = "**/*MANIFEST.yml" if recursive else "*MANIFEST.yml"
            out.extend(sorted(path.glob(pattern)))
        else:
            out.append(path)
    return out


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--recursive", action="store_true", help="Search directories recursively for *MANIFEST.yml")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    paths = _collect_paths(args.paths, recursive=args.recursive)
    issues: list[str] = []
    for path in paths:
        issues.extend(validate_manifest_file(path))
    if issues:
        print("Manifest validation: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Manifest validation: OK")
    for path in paths:
        print(f"checked: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
