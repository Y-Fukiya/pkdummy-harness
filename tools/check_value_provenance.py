#!/usr/bin/env python3
"""Validate value-level provenance metadata for PK fixture parameters."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import yaml


WARNING_DRUGS = [
    "abciximab",
    "aciclovir",
    "alfentanil",
    "amikacin",
    "cimetidine",
    "clarithromycin",
    "felodipine",
    "inulin",
    "itraconazole",
    "moclobemide",
    "montelukast",
    "omeprazole",
    "verapamil",
]

REQUIRED_VALUE_PROVENANCE_FIELDS = [
    "CL_abs_L_per_h_at_70kg",
    "V_abs_L_at_70kg",
    "t_half_h",
]

VALUE_BASIS = {
    "label_reported",
    "literature_reported",
    "derived_from_reported",
    "fixture_policy",
    "unknown_needs_review",
}
CONVERSION_METHODS = {
    "direct",
    "unit_conversion",
    "body_weight_scaled",
    "derived_formula",
    "not_applicable",
    "unknown_needs_review",
}
ROLES = {
    "simulation_parameter",
    "check_only",
    "consistency_check",
    "derived_output",
    "metadata_only",
}
REVIEWER_STATUSES = {
    "checked",
    "acknowledged_fixture_limitation",
    "needs_source_review",
    "needs_unit_review",
    "not_applicable",
}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = yaml.safe_load(f)
    return obj if isinstance(obj, dict) else {}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _approx(a: float, b: float, *, rel_tol: float = 1e-6, abs_tol: float = 1e-8) -> bool:
    return math.isclose(float(a), float(b), rel_tol=rel_tol, abs_tol=abs_tol)


def _source_ids(pk: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for source in pk.get("sources") or []:
        if isinstance(source, dict) and source.get("id"):
            ids.add(str(source["id"]))
    return ids


def canonical_value(pk: dict[str, Any], field: str) -> float | None:
    parsed = pk.get("pk_parsed") or {}
    derived = pk.get("derived") or {}
    if field == "CL_abs_L_per_h_at_70kg":
        value = derived.get("CL_abs_L_per_h_at_70kg")
    elif field == "V_abs_L_at_70kg":
        value = derived.get("V_abs_L_at_70kg")
    elif field == "t_half_h":
        value = parsed.get("half_life_h")
    else:
        value = None
    return float(value) if _is_number(value) else None


def validate_value_provenance(
    slug: str,
    pk: dict[str, Any],
    targets: dict[str, Any] | None = None,
    *,
    required: bool,
) -> list[str]:
    issues: list[str] = []
    provenance = pk.get("value_provenance")
    if provenance is None:
        if required:
            issues.append(f"{slug}: missing value_provenance")
        return issues
    if not isinstance(provenance, dict):
        return [f"{slug}: value_provenance must be a mapping"]

    known_source_ids = _source_ids(pk)
    for field in REQUIRED_VALUE_PROVENANCE_FIELDS:
        entry = provenance.get(field)
        if entry is None:
            if required:
                issues.append(f"{slug}: missing value_provenance.{field}")
            continue
        if not isinstance(entry, dict):
            issues.append(f"{slug}: value_provenance.{field} must be a mapping")
            continue

        source_id = entry.get("source_id")
        if source_id is not None and str(source_id) not in known_source_ids:
            issues.append(f"{slug}: value_provenance.{field}.source_id does not resolve: {source_id}")

        if entry.get("value_basis") not in VALUE_BASIS:
            issues.append(f"{slug}: value_provenance.{field}.value_basis has invalid enum")
        if entry.get("role") not in ROLES:
            issues.append(f"{slug}: value_provenance.{field}.role has invalid enum")
        if entry.get("reviewer_status") not in REVIEWER_STATUSES:
            issues.append(f"{slug}: value_provenance.{field}.reviewer_status has invalid enum")

        conversion = entry.get("conversion")
        if not isinstance(conversion, dict):
            issues.append(f"{slug}: value_provenance.{field}.conversion must be a mapping")
            conversion = {}
        method = conversion.get("method")
        if method not in CONVERSION_METHODS:
            issues.append(f"{slug}: value_provenance.{field}.conversion.method has invalid enum")
        formula = conversion.get("formula")
        assumptions = conversion.get("assumptions")
        if method in {"unit_conversion", "body_weight_scaled", "derived_formula"} or entry.get("value_basis") == "derived_from_reported":
            if not formula and not assumptions:
                issues.append(f"{slug}: value_provenance.{field}.conversion needs formula or assumptions")

        normalized = entry.get("normalized_value")
        expected = canonical_value(pk, field)
        if _is_number(normalized) and expected is not None and not _approx(float(normalized), expected):
            issues.append(
                f"{slug}: value_provenance.{field}.normalized_value mismatch "
                f"(got {normalized}, expected {expected})"
            )

    target_half_life = (((targets or {}).get("targets") or {}).get("t_half") or {})
    structural_mismatch = target_half_life.get("structural_mismatch") if isinstance(target_half_life, dict) else {}
    if isinstance(structural_mismatch, dict) and structural_mismatch.get("acknowledged") is True:
        half_life = provenance.get("t_half_h") if isinstance(provenance, dict) else None
        if not isinstance(half_life, dict):
            issues.append(f"{slug}: acknowledged t_half mismatch requires value_provenance.t_half_h")
        else:
            if half_life.get("role") != "check_only":
                issues.append(f"{slug}: value_provenance.t_half_h.role must be check_only for acknowledged mismatch")
            if half_life.get("reviewer_status") != "acknowledged_fixture_limitation":
                issues.append(
                    f"{slug}: value_provenance.t_half_h.reviewer_status must be acknowledged_fixture_limitation"
                )
    return issues


def build_value_provenance_summary(pk: dict[str, Any], targets: dict[str, Any] | None = None) -> dict[str, Any]:
    provenance = pk.get("value_provenance") if isinstance(pk.get("value_provenance"), dict) else {}
    checked_fields: list[str] = []
    fields_needing_review: list[str] = []
    source_ids: list[str] = []
    mismatch_acknowledged_fields: list[str] = []

    for field in REQUIRED_VALUE_PROVENANCE_FIELDS:
        entry = provenance.get(field)
        if not isinstance(entry, dict):
            fields_needing_review.append(field)
            continue
        checked_fields.append(field)
        source_id = entry.get("source_id")
        if source_id:
            source_ids.append(str(source_id))
        if source_id is None or entry.get("reviewer_status") in {"needs_source_review", "needs_unit_review"}:
            fields_needing_review.append(field)

    target_half_life = (((targets or {}).get("targets") or {}).get("t_half") or {})
    structural_mismatch = target_half_life.get("structural_mismatch") if isinstance(target_half_life, dict) else {}
    half_life = provenance.get("t_half_h")
    if (
        isinstance(structural_mismatch, dict)
        and structural_mismatch.get("acknowledged") is True
        and isinstance(half_life, dict)
        and half_life.get("reviewer_status") == "acknowledged_fixture_limitation"
    ):
        mismatch_acknowledged_fields.append("t_half_h")

    return {
        "required_fields": list(REQUIRED_VALUE_PROVENANCE_FIELDS),
        "checked_fields": checked_fields,
        "fields_needing_review": fields_needing_review,
        "source_ids": sorted(set(source_ids)),
        "mismatch_acknowledged_fields": mismatch_acknowledged_fields,
    }


def validate_root(root: Path | str) -> list[str]:
    root_path = Path(root)
    issues: list[str] = []
    for slug in WARNING_DRUGS:
        drug_dir = root_path / "drugs" / slug
        pk_path = drug_dir / "pk.yml"
        targets_path = drug_dir / "targets.yml"
        if not pk_path.exists():
            issues.append(f"{slug}: missing pk.yml")
            continue
        pk = load_yaml(pk_path)
        targets = load_yaml(targets_path) if targets_path.exists() else {}
        issues.extend(validate_value_provenance(slug, pk, targets, required=True))
    return issues


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    issues = validate_root(args.root)
    if issues:
        print("Value provenance check: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Value provenance check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
