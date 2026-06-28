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
SOURCE_REVIEW_STATUSES = {"checked", "needs_source_review", "needs_unit_review", "not_applicable"}
FIXTURE_LIMITATION_STATUSES = {"acknowledged", "not_applicable"}
SOURCE_KIND_RANKS = {
    "label": 0,
    "pubmed": 1,
    "journal": 2,
    "drugbank": 3,
    "pubchem": 4,
    "wikipedia": 5,
    "secondary": 6,
    "other": 9,
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


def _source_id_list(pk: dict[str, Any]) -> list[str]:
    return sorted(_source_ids(pk))


def _source_kind(url: str) -> str:
    url_lower = url.lower()
    if "dailymed.nlm.nih.gov" in url_lower:
        return "label"
    if "pubmed.ncbi.nlm.nih.gov" in url_lower:
        return "pubmed"
    if "journals.asm.org" in url_lower or "sciencedirect.com/science/article" in url_lower:
        return "journal"
    if "go.drugbank.com" in url_lower:
        return "drugbank"
    if "pubchem.ncbi.nlm.nih.gov" in url_lower:
        return "pubchem"
    if "wikipedia.org" in url_lower:
        return "wikipedia"
    if "researchgate.net" in url_lower or "sciencedirect.com/topics" in url_lower:
        return "secondary"
    return "other"


def _source_refs(pk: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for source in pk.get("sources") or []:
        if isinstance(source, dict) and source.get("id"):
            url = str(source.get("url") or "")
            source_kind = _source_kind(url)
            refs.append(
                {
                    "id": str(source["id"]),
                    "source_kind": source_kind,
                    "source_rank": SOURCE_KIND_RANKS[source_kind],
                    "url": url,
                }
            )
    return sorted(refs, key=lambda ref: ref["id"])


def _filter_source_refs(source_refs: list[dict[str, Any]], source_ids: set[str]) -> list[dict[str, Any]]:
    return [ref for ref in source_refs if ref["id"] in source_ids]


def _sort_source_refs_for_review(source_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(source_refs, key=lambda ref: (ref["source_rank"], ref["id"]))


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
        source_review_status = entry.get("source_review_status")
        if source_review_status not in SOURCE_REVIEW_STATUSES:
            issues.append(f"{slug}: value_provenance.{field}.source_review_status has invalid enum")
        fixture_limitation_status = entry.get("fixture_limitation_status")
        if fixture_limitation_status not in FIXTURE_LIMITATION_STATUSES:
            issues.append(f"{slug}: value_provenance.{field}.fixture_limitation_status has invalid enum")
        if entry.get("source_id") is not None and source_review_status != "checked":
            issues.append(f"{slug}: value_provenance.{field}.source_review_status must be checked when source_id is set")

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
            if half_life.get("fixture_limitation_status") != "acknowledged":
                issues.append(
                    f"{slug}: value_provenance.t_half_h.fixture_limitation_status must be acknowledged"
                )
    return issues


def build_value_provenance_summary(pk: dict[str, Any], targets: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(pk.get("value_provenance"), dict):
        return {
            "scope": "warning_drugs_only",
            "provenance_required": False,
            "required_fields": [],
            "checked_fields": [],
            "fields_needing_review": [],
            "source_ids": [],
            "mismatch_acknowledged_fields": [],
        }

    provenance = pk.get("value_provenance") or {}
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
        source_review_status = entry.get("source_review_status", entry.get("reviewer_status"))
        if source_id is None or source_review_status in {"needs_source_review", "needs_unit_review"}:
            fields_needing_review.append(field)

    target_half_life = (((targets or {}).get("targets") or {}).get("t_half") or {})
    structural_mismatch = target_half_life.get("structural_mismatch") if isinstance(target_half_life, dict) else {}
    half_life = provenance.get("t_half_h")
    if (
        isinstance(structural_mismatch, dict)
        and structural_mismatch.get("acknowledged") is True
        and isinstance(half_life, dict)
        and half_life.get("fixture_limitation_status", half_life.get("reviewer_status")) in {
            "acknowledged",
            "acknowledged_fixture_limitation",
        }
    ):
        mismatch_acknowledged_fields.append("t_half_h")

    return {
        "scope": "value_provenance_present",
        "provenance_required": True,
        "required_fields": list(REQUIRED_VALUE_PROVENANCE_FIELDS),
        "checked_fields": checked_fields,
        "fields_needing_review": fields_needing_review,
        "source_ids": sorted(set(source_ids)),
        "mismatch_acknowledged_fields": mismatch_acknowledged_fields,
    }


def _empty_coverage() -> dict[str, int | float]:
    return {"resolved": 0, "unresolved": 0, "total": 0, "rate": 0.0}


def _review_priority(field: str) -> str:
    if field == "t_half_h":
        return "high"
    return "medium"


def _priority_rank(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 99)


def _review_action(available_source_ids: list[str], used_source_ids: set[str]) -> str:
    unused_source_ids = set(available_source_ids) - used_source_ids
    if unused_source_ids:
        return "inspect_unused_sources"
    if available_source_ids:
        return "recheck_used_sources"
    return "add_source_before_mapping"


def _unresolved_reasons(entry: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if entry.get("source_id") is None:
        reasons.append("source_id_missing")
    source_review_status = entry.get("source_review_status")
    if source_review_status in {"needs_source_review", "needs_unit_review"}:
        reasons.append(str(source_review_status))
    elif source_review_status != "checked":
        reasons.append("source_review_status_not_checked")
    return reasons


def _unresolved_entry_detail(
    slug: str,
    field: str,
    entry: dict[str, Any],
    *,
    source_review_status: Any,
    available_source_ids: list[str],
    available_source_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    detail = {
        "entry": f"{slug}.{field}",
        "drug": slug,
        "field": field,
        "priority": _review_priority(field),
        "reasons": _unresolved_reasons(entry),
        "role": entry.get("role"),
        "value_basis": entry.get("value_basis"),
        "source_review_status": source_review_status,
        "fixture_limitation_status": entry.get("fixture_limitation_status"),
        "source_field": entry.get("source_field"),
        "raw_value": entry.get("raw_value"),
        "raw_unit": entry.get("raw_unit"),
        "normalized_value": entry.get("normalized_value"),
        "normalized_unit": entry.get("normalized_unit"),
        "available_source_ids": available_source_ids,
        "available_source_refs": available_source_refs,
    }
    source_verification = entry.get("source_verification")
    if isinstance(source_verification, dict):
        detail.update(
            {
                "source_verification_status": source_verification.get("status"),
                "source_review_blocker": source_verification.get("blocker"),
                "reviewed_source_ids": list(source_verification.get("reviewed_source_ids") or []),
                "reviewed_external_queries": list(
                    source_verification.get("reviewed_external_queries") or []
                ),
                "next_source_review_action": source_verification.get("next_action"),
                "source_verification_note": source_verification.get("reviewer_note"),
            }
        )
    return detail


def _source_review_queue_item(
    slug: str,
    unresolved_fields: list[str],
    coverage: dict[str, int | float],
    *,
    available_source_ids: list[str],
    used_source_ids: set[str],
    available_source_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    unresolved_priorities = [_review_priority(field) for field in unresolved_fields]
    highest_priority = sorted(unresolved_priorities, key=_priority_rank)[0]
    unused_source_ids = set(available_source_ids) - used_source_ids
    used_source_refs = _filter_source_refs(available_source_refs, used_source_ids)
    unused_source_refs = _filter_source_refs(available_source_refs, unused_source_ids)
    suggested_source_refs = _sort_source_refs_for_review(unused_source_refs or used_source_refs)

    return {
        "drug": slug,
        "highest_priority": highest_priority,
        "review_action": _review_action(available_source_ids, used_source_ids),
        "unresolved_fields": unresolved_fields,
        "unresolved_entries": [f"{slug}.{field}" for field in unresolved_fields],
        "coverage": dict(coverage),
        "available_source_ids": available_source_ids,
        "used_source_ids": sorted(used_source_ids),
        "unused_source_ids": sorted(unused_source_ids),
        "available_source_refs": available_source_refs,
        "used_source_refs": used_source_refs,
        "unused_source_refs": unused_source_refs,
        "suggested_source_refs": suggested_source_refs,
    }


def _count_queue_suggestions(
    item: dict[str, Any],
    *,
    source_review_action_counts: dict[str, int],
    suggested_source_kind_counts: dict[str, int],
) -> None:
    action = str(item["review_action"])
    source_review_action_counts[action] = source_review_action_counts.get(action, 0) + 1
    for source_ref in item["suggested_source_refs"]:
        source_kind = source_ref["source_kind"]
        suggested_source_kind_counts[source_kind] = suggested_source_kind_counts.get(source_kind, 0) + 1


def _apply_coverage_rates(
    coverage_by_field: dict[str, dict[str, int | float]],
    coverage_by_drug: dict[str, dict[str, int | float]],
) -> None:
    for field_coverage in coverage_by_field.values():
        total = field_coverage["total"]
        field_coverage["rate"] = field_coverage["resolved"] / total if total else 0.0
    for drug_coverage in coverage_by_drug.values():
        total = drug_coverage["total"]
        drug_coverage["rate"] = drug_coverage["resolved"] / total if total else 0.0


def _next_review_items(
    unresolved_entries: list[str],
    unresolved_entry_details: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, Any]]]:
    field_priority = {
        "t_half_h": 0,
        "CL_abs_L_per_h_at_70kg": 1,
        "V_abs_L_at_70kg": 2,
    }
    detail_by_entry = {detail["entry"]: detail for detail in unresolved_entry_details}
    next_review_entries = sorted(
        unresolved_entries,
        key=lambda entry: (field_priority.get(entry.split(".", 1)[1], 99), entry),
    )
    next_review_details = [
        detail_by_entry[entry] for entry in next_review_entries if entry in detail_by_entry
    ]
    return next_review_entries, next_review_details


def _sort_source_review_queue(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        queue,
        key=lambda item: (
            _priority_rank(str(item["highest_priority"])),
            item["coverage"]["resolved"],
            -item["coverage"]["unresolved"],
            item["drug"],
        ),
    )


def value_provenance_report(root: Path | str) -> dict[str, Any]:
    root_path = Path(root)
    fields_needing_review: list[str] = []
    source_ids: set[str] = set()
    resolved_entries: list[str] = []
    resolved_source_refs: set[str] = set()
    unresolved_entries: list[str] = []
    unresolved_entry_details: list[dict[str, Any]] = []
    unresolved_reason_counts: dict[str, int] = {}
    coverage_by_field = {
        field: _empty_coverage()
        for field in REQUIRED_VALUE_PROVENANCE_FIELDS
    }
    coverage_by_drug: dict[str, dict[str, int | float]] = {}
    fully_mapped_warning_drugs: list[str] = []
    partially_mapped_warning_drugs: list[str] = []
    unmapped_warning_drugs: list[str] = []
    source_review_queue: list[dict[str, Any]] = []
    source_review_action_counts: dict[str, int] = {}
    suggested_source_kind_counts: dict[str, int] = {}
    source_review_status_counts = {status: 0 for status in sorted(SOURCE_REVIEW_STATUSES)}
    fixture_limitation_status_counts = {status: 0 for status in sorted(FIXTURE_LIMITATION_STATUSES)}
    non_null_source_id_entries = 0
    warning_t_half_total = 0
    warning_t_half_resolved = 0
    entries = 0
    for slug in WARNING_DRUGS:
        drug_dir = root_path / "drugs" / slug
        pk_path = drug_dir / "pk.yml"
        targets_path = drug_dir / "targets.yml"
        if not pk_path.exists():
            continue
        pk = load_yaml(pk_path)
        targets = load_yaml(targets_path) if targets_path.exists() else {}
        summary = build_value_provenance_summary(pk, targets)
        available_source_ids = _source_id_list(pk)
        available_source_refs = _source_refs(pk)
        used_source_ids_for_drug: set[str] = set()
        unresolved_for_drug = {
            f"{slug}.{field}" for field in summary.get("fields_needing_review") or []
        }
        unresolved_fields_for_drug = [
            field
            for field in REQUIRED_VALUE_PROVENANCE_FIELDS
            if f"{slug}.{field}" in unresolved_for_drug
        ]
        entries += len(summary.get("checked_fields") or [])
        source_ids.update(str(source_id) for source_id in summary.get("source_ids") or [])
        for field in summary.get("fields_needing_review") or []:
            unresolved_entry = f"{slug}.{field}"
            fields_needing_review.append(unresolved_entry)
            unresolved_entries.append(unresolved_entry)

        provenance = pk.get("value_provenance") or {}
        if not isinstance(provenance, dict):
            continue
        mapped_fields_for_drug = 0
        coverage_by_drug[slug] = _empty_coverage()
        for field in REQUIRED_VALUE_PROVENANCE_FIELDS:
            entry = provenance.get(field)
            if not isinstance(entry, dict):
                continue
            entry_name = f"{slug}.{field}"
            coverage_by_drug[slug]["total"] += 1
            coverage_by_field[field]["total"] += 1
            source_review_status = entry.get("source_review_status")
            if source_review_status in source_review_status_counts:
                source_review_status_counts[source_review_status] += 1
            fixture_limitation_status = entry.get("fixture_limitation_status")
            if fixture_limitation_status in fixture_limitation_status_counts:
                fixture_limitation_status_counts[fixture_limitation_status] += 1
            if entry.get("source_id") is not None:
                non_null_source_id_entries += 1
                source_id = str(entry["source_id"])
                resolved_entries.append(f"{slug}.{field} -> {source_id}")
                resolved_source_refs.add(f"{slug}.{source_id}")
                used_source_ids_for_drug.add(source_id)
                mapped_fields_for_drug += 1
                coverage_by_field[field]["resolved"] += 1
                coverage_by_drug[slug]["resolved"] += 1
            else:
                coverage_by_field[field]["unresolved"] += 1
                coverage_by_drug[slug]["unresolved"] += 1
            if entry_name in unresolved_for_drug:
                reasons = _unresolved_reasons(entry)
                for reason in reasons:
                    unresolved_reason_counts[reason] = unresolved_reason_counts.get(reason, 0) + 1
                unresolved_entry_details.append(
                    _unresolved_entry_detail(
                        slug,
                        field,
                        entry,
                        source_review_status=source_review_status,
                        available_source_ids=available_source_ids,
                        available_source_refs=available_source_refs,
                    )
                )

        half_life = provenance.get("t_half_h")
        if isinstance(half_life, dict):
            warning_t_half_total += 1
            if half_life.get("source_id") is not None:
                warning_t_half_resolved += 1

        if mapped_fields_for_drug == len(REQUIRED_VALUE_PROVENANCE_FIELDS):
            fully_mapped_warning_drugs.append(slug)
        elif mapped_fields_for_drug:
            partially_mapped_warning_drugs.append(slug)
        else:
            unmapped_warning_drugs.append(slug)

        if unresolved_fields_for_drug:
            queue_item = _source_review_queue_item(
                slug,
                unresolved_fields_for_drug,
                coverage_by_drug[slug],
                available_source_ids=available_source_ids,
                used_source_ids=used_source_ids_for_drug,
                available_source_refs=available_source_refs,
            )
            _count_queue_suggestions(
                queue_item,
                source_review_action_counts=source_review_action_counts,
                suggested_source_kind_counts=suggested_source_kind_counts,
            )
            source_review_queue.append(queue_item)

    t_half_rate = warning_t_half_resolved / warning_t_half_total if warning_t_half_total else 0.0
    source_mapping_rate = non_null_source_id_entries / entries if entries else 0.0
    _apply_coverage_rates(coverage_by_field, coverage_by_drug)
    next_review_entries, next_review_details = _next_review_items(
        unresolved_entries,
        unresolved_entry_details,
    )
    source_review_queue = _sort_source_review_queue(source_review_queue)
    return {
        "warning_drugs": list(WARNING_DRUGS),
        "provenance_entries": entries,
        "non_null_source_ids": sorted(source_ids),
        "non_null_source_id_entries": non_null_source_id_entries,
        "resolved_entries": sorted(resolved_entries),
        "resolved_source_refs": sorted(resolved_source_refs),
        "unresolved_entries": sorted(unresolved_entries),
        "unresolved_entry_details": sorted(unresolved_entry_details, key=lambda detail: detail["entry"]),
        "unresolved_reason_counts": dict(sorted(unresolved_reason_counts.items())),
        "source_mapping_coverage": {
            "resolved": non_null_source_id_entries,
            "unresolved": len(unresolved_entries),
            "total": entries,
            "rate": source_mapping_rate,
        },
        "source_mapping_coverage_by_field": coverage_by_field,
        "source_mapping_coverage_by_drug": dict(sorted(coverage_by_drug.items())),
        "next_review_entries": next_review_entries,
        "next_review_details": next_review_details,
        "source_review_queue": source_review_queue,
        "source_review_action_counts": dict(sorted(source_review_action_counts.items())),
        "suggested_source_kind_counts": dict(sorted(suggested_source_kind_counts.items())),
        "fully_mapped_warning_drugs": sorted(fully_mapped_warning_drugs),
        "partially_mapped_warning_drugs": sorted(partially_mapped_warning_drugs),
        "unmapped_warning_drugs": sorted(unmapped_warning_drugs),
        "fields_needing_review": fields_needing_review,
        "source_review_status_counts": source_review_status_counts,
        "fixture_limitation_status_counts": fixture_limitation_status_counts,
        "warning_t_half_source_id_resolution": {
            "resolved": warning_t_half_resolved,
            "total": warning_t_half_total,
            "rate": t_half_rate,
        },
    }


def validate_root(root: Path | str, *, include_report: bool = False) -> list[str] | tuple[list[str], dict[str, Any]]:
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
    if include_report:
        return issues, value_provenance_report(root_path)
    return issues


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--report", action="store_true", help="Print fields still needing source/unit review")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.report:
        issues, report = validate_root(args.root, include_report=True)
    else:
        issues = validate_root(args.root)
        report = None
    if issues:
        print("Value provenance check: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Value provenance check: OK")
    if report is not None:
        print("fields_needing_review:")
        for field in report["fields_needing_review"]:
            print(f"- {field}")
        print("non_null_source_ids:")
        for source_id in report["non_null_source_ids"]:
            print(f"- {source_id}")
        print("non_null_source_id_entries:")
        print(f"- {report['non_null_source_id_entries']}")
        print("resolved_source_refs:")
        for source_ref in report["resolved_source_refs"]:
            print(f"- {source_ref}")
        print("resolved_entries:")
        for entry in report["resolved_entries"]:
            print(f"- {entry}")
        print("unresolved_entries:")
        for entry in report["unresolved_entries"]:
            print(f"- {entry}")
        print("unresolved_entry_details:")
        for detail in report["unresolved_entry_details"]:
            reasons = ",".join(detail["reasons"])
            line = (
                f"- {detail['entry']}: priority={detail['priority']} "
                f"reasons={reasons} normalized={detail['normalized_value']} {detail['normalized_unit']} "
                f"role={detail['role']}"
            )
            if detail.get("source_verification_status"):
                line += (
                    f" source_verification_status={detail['source_verification_status']}"
                    f" blocker={detail.get('source_review_blocker')}"
                    f" next_action={detail.get('next_source_review_action')}"
                )
            print(line)
        print("unresolved_reason_counts:")
        for reason, count in report["unresolved_reason_counts"].items():
            print(f"- {reason}: {count}")
        coverage = report["source_mapping_coverage"]
        print("source_mapping_coverage:")
        print(f"- resolved: {coverage['resolved']}")
        print(f"- unresolved: {coverage['unresolved']}")
        print(f"- total: {coverage['total']}")
        print(f"- rate: {coverage['rate']:.3f}")
        print("source_mapping_coverage_by_field:")
        for field, field_coverage in report["source_mapping_coverage_by_field"].items():
            print(
                f"- {field}: resolved={field_coverage['resolved']} "
                f"unresolved={field_coverage['unresolved']} "
                f"total={field_coverage['total']} rate={field_coverage['rate']:.3f}"
            )
        print("source_mapping_coverage_by_drug:")
        for slug, drug_coverage in report["source_mapping_coverage_by_drug"].items():
            print(
                f"- {slug}: resolved={drug_coverage['resolved']} "
                f"unresolved={drug_coverage['unresolved']} "
                f"total={drug_coverage['total']} rate={drug_coverage['rate']:.3f}"
            )
        print("next_review_entries:")
        for entry in report["next_review_entries"]:
            print(f"- {entry}")
        print("next_review_details:")
        for detail in report["next_review_details"]:
            reasons = ",".join(detail["reasons"])
            line = f"- {detail['entry']}: priority={detail['priority']} reasons={reasons}"
            if detail.get("source_verification_status"):
                line += (
                    f" source_verification_status={detail['source_verification_status']}"
                    f" blocker={detail.get('source_review_blocker')}"
                    f" next_action={detail.get('next_source_review_action')}"
                )
            print(line)
        print("source_review_queue:")
        for item in report["source_review_queue"]:
            fields = ",".join(item["unresolved_fields"])
            available = ",".join(item["available_source_ids"])
            used = ",".join(item["used_source_ids"])
            unused = ",".join(item["unused_source_ids"])
            available_refs = ";".join(f"{ref['id']}={ref['url']}" for ref in item["available_source_refs"])
            used_refs = ";".join(f"{ref['id']}={ref['url']}" for ref in item["used_source_refs"])
            unused_refs = ";".join(f"{ref['id']}={ref['url']}" for ref in item["unused_source_refs"])
            suggested_refs = ";".join(
                f"{ref['id']}:{ref['source_kind']}={ref['url']}"
                for ref in item["suggested_source_refs"]
            )
            coverage = item["coverage"]
            print(
                f"- {item['drug']}: priority={item['highest_priority']} "
                f"action={item['review_action']} "
                f"resolved={coverage['resolved']} unresolved={coverage['unresolved']} "
                f"fields={fields} available_sources={available} "
                f"used_sources={used} unused_sources={unused} "
                f"available_source_refs={available_refs} "
                f"used_source_refs={used_refs} unused_source_refs={unused_refs} "
                f"suggested_source_refs={suggested_refs}"
            )
        print("source_review_action_counts:")
        for action, count in report["source_review_action_counts"].items():
            print(f"- {action}: {count}")
        print("suggested_source_kind_counts:")
        for source_kind, count in report["suggested_source_kind_counts"].items():
            print(f"- {source_kind}: {count}")
        print("fully_mapped_warning_drugs:")
        for slug in report["fully_mapped_warning_drugs"]:
            print(f"- {slug}")
        print("partially_mapped_warning_drugs:")
        for slug in report["partially_mapped_warning_drugs"]:
            print(f"- {slug}")
        print("unmapped_warning_drugs:")
        for slug in report["unmapped_warning_drugs"]:
            print(f"- {slug}")
        print("source_review_status:")
        for status, count in report["source_review_status_counts"].items():
            print(f"- {status}: {count}")
        print("fixture_limitation_status:")
        for status, count in report["fixture_limitation_status_counts"].items():
            print(f"- {status}: {count}")
        resolution = report["warning_t_half_source_id_resolution"]
        print("warning_t_half_source_id_resolution:")
        print(f"- resolved: {resolution['resolved']}")
        print(f"- total: {resolution['total']}")
        print(f"- rate: {resolution['rate']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
