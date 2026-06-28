from __future__ import annotations

from pathlib import Path

import yaml

from tools.check_value_provenance import (
    REQUIRED_VALUE_PROVENANCE_FIELDS,
    WARNING_DRUGS,
    build_value_provenance_summary,
    value_provenance_report,
    validate_root,
    validate_value_provenance,
)


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_warning_drugs_have_cl_v_t_half_value_provenance() -> None:
    for slug in WARNING_DRUGS:
        pk = load_yaml(ROOT / "drugs" / slug / "pk.yml")
        provenance = pk.get("value_provenance") or {}

        for field in REQUIRED_VALUE_PROVENANCE_FIELDS:
            assert field in provenance, f"{slug}: missing value_provenance.{field}"


def test_value_provenance_source_ids_resolve() -> None:
    issues = validate_root(ROOT)

    assert not [issue for issue in issues if "source_id does not resolve" in issue]


def test_value_provenance_normalized_values_match_pk_values() -> None:
    issues = validate_root(ROOT)

    assert not [issue for issue in issues if "normalized_value mismatch" in issue]


def test_mismatch_half_life_is_check_only_and_acknowledged() -> None:
    for slug in WARNING_DRUGS:
        pk = load_yaml(ROOT / "drugs" / slug / "pk.yml")
        targets = load_yaml(ROOT / "drugs" / slug / "targets.yml")
        half_life = (pk.get("value_provenance") or {}).get("t_half_h") or {}
        target_half_life = ((targets.get("targets") or {}).get("t_half") or {})
        structural_mismatch = target_half_life.get("structural_mismatch") or {}

        assert half_life.get("role") == "check_only", slug
        assert half_life.get("source_review_status") in {"checked", "needs_source_review"}, slug
        assert half_life.get("fixture_limitation_status") == "acknowledged", slug
        assert structural_mismatch.get("acknowledged") is True, slug


def test_value_provenance_separates_source_review_from_fixture_limitation() -> None:
    for slug in WARNING_DRUGS:
        pk = load_yaml(ROOT / "drugs" / slug / "pk.yml")
        provenance = pk.get("value_provenance") or {}

        for field in REQUIRED_VALUE_PROVENANCE_FIELDS:
            entry = provenance[field]
            assert entry.get("source_review_status") in {"checked", "needs_source_review"}, f"{slug}.{field}"
            assert entry.get("fixture_limitation_status") in {"acknowledged", "not_applicable"}, f"{slug}.{field}"
        assert provenance["t_half_h"]["fixture_limitation_status"] == "acknowledged", slug


def test_value_provenance_summary_reports_checked_and_review_fields() -> None:
    pk = load_yaml(ROOT / "drugs" / "aciclovir" / "pk.yml")
    targets = load_yaml(ROOT / "drugs" / "aciclovir" / "targets.yml")

    summary = build_value_provenance_summary(pk, targets)

    assert summary["required_fields"] == REQUIRED_VALUE_PROVENANCE_FIELDS
    assert set(summary["metadata_present_fields"]) >= set(REQUIRED_VALUE_PROVENANCE_FIELDS)
    assert set(summary["source_checked_fields"]) < set(REQUIRED_VALUE_PROVENANCE_FIELDS)
    assert set(summary["checked_fields"]) >= set(REQUIRED_VALUE_PROVENANCE_FIELDS)
    assert "t_half_h" in summary["mismatch_acknowledged_fields"]
    assert isinstance(summary["source_ids"], list)
    assert summary["fields_needing_review"]


def test_value_provenance_summary_is_not_required_when_absent() -> None:
    summary = build_value_provenance_summary({}, {})

    assert summary["scope"] == "warning_drugs_only"
    assert summary["provenance_required"] is False
    assert summary["required_fields"] == []
    assert summary["metadata_present_fields"] == []
    assert summary["source_checked_fields"] == []
    assert summary["checked_fields"] == []
    assert summary["fields_needing_review"] == []


def test_value_provenance_report_lists_fields_needing_review() -> None:
    issues, report = validate_root(ROOT, include_report=True)

    assert issues == []
    assert "fields_needing_review" in report
    assert "abciximab.CL_abs_L_per_h_at_70kg" in report["fields_needing_review"]


def test_value_provenance_report_counts_review_statuses() -> None:
    report = value_provenance_report(ROOT)

    source_counts = report["source_review_status_counts"]
    fixture_counts = report["fixture_limitation_status_counts"]

    assert sum(source_counts.values()) == report["provenance_entries"]
    assert sum(fixture_counts.values()) == report["provenance_entries"]
    assert source_counts["checked"] == report["non_null_source_id_entries"]
    assert fixture_counts["acknowledged"] == len(WARNING_DRUGS)


def test_value_provenance_report_lists_resolved_entries() -> None:
    report = value_provenance_report(ROOT)

    assert "resolved_entries" in report
    assert "resolved_source_refs" in report
    assert "montelukast.CL_abs_L_per_h_at_70kg -> source_1" in report["resolved_entries"]
    assert "montelukast.source_1" in report["resolved_source_refs"]


def test_value_provenance_report_lists_unresolved_entries_and_coverage() -> None:
    report = value_provenance_report(ROOT)

    coverage = report["source_mapping_coverage"]
    coverage_by_field = report["source_mapping_coverage_by_field"]
    coverage_by_drug = report["source_mapping_coverage_by_drug"]

    assert "unresolved_entries" in report
    assert "inulin.t_half_h" in report["unresolved_entries"]
    assert coverage["total"] == report["provenance_entries"]
    assert coverage["resolved"] == report["non_null_source_id_entries"]
    assert coverage["unresolved"] == len(report["unresolved_entries"])
    assert coverage["rate"] >= 0.5
    assert coverage_by_field["t_half_h"]["resolved"] >= 12
    assert coverage_by_field["CL_abs_L_per_h_at_70kg"]["total"] == len(WARNING_DRUGS)
    assert coverage_by_field["V_abs_L_at_70kg"]["total"] == len(WARNING_DRUGS)
    assert coverage_by_drug["abciximab"]["resolved"] >= 1
    assert coverage_by_drug["alfentanil"]["rate"] == 1.0
    assert coverage_by_drug["felodipine"]["rate"] == 1.0


def test_value_provenance_report_explains_unresolved_review_reasons() -> None:
    report = value_provenance_report(ROOT)

    unresolved_details = {
        detail["entry"]: detail for detail in report["unresolved_entry_details"]
    }
    inulin_half_life = unresolved_details["inulin.t_half_h"]

    assert report["unresolved_reason_counts"]["source_id_missing"] == len(
        report["unresolved_entries"]
    )
    assert inulin_half_life["field"] == "t_half_h"
    assert inulin_half_life["role"] == "check_only"
    assert inulin_half_life["priority"] == "high"
    assert inulin_half_life["normalized_value"] == 3.0
    assert inulin_half_life["normalized_unit"] == "h"
    assert inulin_half_life["reasons"] == [
        "source_id_missing",
        "needs_source_review",
    ]


def test_value_provenance_report_surfaces_source_verification_blockers() -> None:
    report = value_provenance_report(ROOT)

    unresolved_details = {
        detail["entry"]: detail for detail in report["unresolved_entry_details"]
    }
    inulin_half_life = unresolved_details["inulin.t_half_h"]

    assert inulin_half_life["source_verification_status"] == "no_exact_public_source_match"
    assert inulin_half_life["source_review_blocker"] == "exact_value_not_found_in_public_primary_source"
    assert inulin_half_life["reviewed_source_ids"] == ["source_1", "source_2"]
    assert inulin_half_life["next_source_review_action"] == "add_primary_source_or_replace_fixture_value"
    assert (
        inulin_half_life["fixture_value_decision"]
        == "retain_current_fixture_value_pending_primary_source"
    )
    assert (
        inulin_half_life["fixture_value_decision_reason"]
        .startswith("Retain the current 2-4 h fixture half-life")
    )


def test_value_provenance_validates_source_verification_contract() -> None:
    pk = load_yaml(ROOT / "drugs" / "inulin" / "pk.yml")
    targets = load_yaml(ROOT / "drugs" / "inulin" / "targets.yml")
    half_life = pk["value_provenance"]["t_half_h"]

    half_life["source_verification"]["status"] = "maybe"
    half_life["source_verification"]["blocker"] = "maybe_missing"
    half_life["source_verification"]["next_action"] = "guess_source_id"
    half_life["source_verification"]["reviewed_source_ids"] = ["missing_source"]

    issues = validate_value_provenance("inulin", pk, targets, required=True)

    assert "inulin: value_provenance.t_half_h.source_verification.status has invalid enum" in issues
    assert "inulin: value_provenance.t_half_h.source_verification.blocker has invalid enum" in issues
    assert "inulin: value_provenance.t_half_h.source_verification.next_action has invalid enum" in issues
    assert (
        "inulin: value_provenance.t_half_h.source_verification.reviewed_source_ids "
        "has unresolved id: missing_source"
    ) in issues


def test_value_provenance_validates_source_verification_decision_fields() -> None:
    pk = load_yaml(ROOT / "drugs" / "inulin" / "pk.yml")
    targets = load_yaml(ROOT / "drugs" / "inulin" / "targets.yml")
    half_life = pk["value_provenance"]["t_half_h"]

    half_life["source_verification"]["fixture_value_decision"] = "replace_by_guessing"
    half_life["source_verification"]["decision_reason"] = ""

    issues = validate_value_provenance("inulin", pk, targets, required=True)

    assert (
        "inulin: value_provenance.t_half_h.source_verification.fixture_value_decision "
        "has invalid enum"
    ) in issues
    assert (
        "inulin: value_provenance.t_half_h.source_verification.decision_reason "
        "must be non-empty"
    ) in issues


def test_value_provenance_rejects_no_match_verification_with_source_id() -> None:
    pk = load_yaml(ROOT / "drugs" / "inulin" / "pk.yml")
    targets = load_yaml(ROOT / "drugs" / "inulin" / "targets.yml")
    half_life = pk["value_provenance"]["t_half_h"]

    half_life["source_id"] = "source_1"
    half_life["source_review_status"] = "checked"

    issues = validate_value_provenance("inulin", pk, targets, required=True)

    assert (
        "inulin: value_provenance.t_half_h.source_id must stay null when "
        "source_verification.status is no_exact_public_source_match"
    ) in issues


def test_value_provenance_requires_source_verification_for_unresolved_half_life() -> None:
    pk = load_yaml(ROOT / "drugs" / "inulin" / "pk.yml")
    targets = load_yaml(ROOT / "drugs" / "inulin" / "targets.yml")
    half_life = pk["value_provenance"]["t_half_h"]

    half_life.pop("source_verification")

    issues = validate_value_provenance("inulin", pk, targets, required=True)

    assert (
        "inulin: value_provenance.t_half_h.source_verification is required when "
        "t_half_h source_id is missing"
    ) in issues


def test_value_provenance_report_counts_source_verification_statuses() -> None:
    report = value_provenance_report(ROOT)

    assert report["source_verification_status_counts"]["no_exact_public_source_match"] == 1
    assert report["source_verification_status_counts"]["not_recorded"] == (
        len(report["unresolved_entries"]) - 1
    )
    assert (
        report["source_review_blocker_counts"][
            "exact_value_not_found_in_public_primary_source"
        ]
        == 1
    )
    assert "abciximab.CL_abs_L_per_h_at_70kg" in report[
        "unresolved_entries_missing_source_verification"
    ]
    assert "inulin.t_half_h" not in report["unresolved_entries_missing_source_verification"]


def test_value_provenance_report_counts_fixture_value_decisions() -> None:
    report = value_provenance_report(ROOT)

    assert report["fixture_value_decision_counts"] == {
        "retain_current_fixture_value_pending_primary_source": 1
    }
    assert report["fixture_value_decision_entries"] == [
        {
            "entry": "inulin.t_half_h",
            "decision": "retain_current_fixture_value_pending_primary_source",
            "reason": (
                "Retain the current 2-4 h fixture half-life for deterministic "
                "regression continuity while keeping source_id null. This value "
                "must not be treated as source-verified until a primary source "
                "exact match is added, or until the fixture value is deliberately "
                "replaced with a source-verified value."
            ),
        }
    ]


def test_value_provenance_report_counts_source_verification_coverage_by_priority() -> None:
    report = value_provenance_report(ROOT)
    coverage = report["source_verification_coverage"]
    coverage_by_priority = report["source_verification_coverage_by_priority"]

    assert coverage["total_unresolved"] == len(report["unresolved_entries"])
    assert coverage["with_source_verification"] == 1
    assert coverage["missing_source_verification"] == len(report["unresolved_entries"]) - 1
    assert coverage_by_priority["high"]["total_unresolved"] == 1
    assert coverage_by_priority["high"]["with_source_verification"] == 1
    assert coverage_by_priority["high"]["missing_source_verification"] == 0
    assert coverage_by_priority["medium"]["missing_source_verification"] == (
        len(report["unresolved_entries"]) - 1
    )


def test_value_provenance_report_builds_source_review_queue() -> None:
    report = value_provenance_report(ROOT)

    queue = report["source_review_queue"]
    inulin = queue[0]
    by_drug = {item["drug"]: item for item in queue}

    assert inulin["drug"] == "inulin"
    assert inulin["highest_priority"] == "high"
    assert inulin["coverage"]["resolved"] == 0
    assert inulin["unresolved_fields"] == [
        "CL_abs_L_per_h_at_70kg",
        "V_abs_L_at_70kg",
        "t_half_h",
    ]
    assert inulin["used_source_ids"] == []
    assert inulin["available_source_ids"] == ["source_1", "source_2"]
    assert inulin["unused_source_ids"] == ["source_1", "source_2"]
    assert by_drug["abciximab"]["used_source_ids"] == ["source_5"]
    assert by_drug["abciximab"]["unused_source_ids"] == ["source_1", "source_2", "source_3", "source_4"]
    assert "alfentanil" not in by_drug


def test_value_provenance_report_includes_source_refs_and_review_actions() -> None:
    report = value_provenance_report(ROOT)

    by_drug = {item["drug"]: item for item in report["source_review_queue"]}
    abciximab = by_drug["abciximab"]

    assert report["source_review_action_counts"]["inspect_unused_sources"] == 7
    assert report["source_review_action_counts"]["recheck_used_sources"] == 1
    assert abciximab["review_action"] == "inspect_unused_sources"
    assert abciximab["available_source_refs"][0] == {
        "id": "source_1",
        "source_kind": "drugbank",
        "source_rank": 3,
        "url": "https://go.drugbank.com/drugs/DB00054",
    }
    assert abciximab["used_source_refs"] == [
        {
            "id": "source_5",
            "source_kind": "pubmed",
            "source_rank": 1,
            "url": "https://pubmed.ncbi.nlm.nih.gov/14618072/",
        }
    ]
    assert [ref["id"] for ref in abciximab["unused_source_refs"]] == [
        "source_1",
        "source_2",
        "source_3",
        "source_4",
    ]


def test_value_provenance_report_prioritizes_suggested_source_refs_by_kind() -> None:
    report = value_provenance_report(ROOT)

    by_drug = {item["drug"]: item for item in report["source_review_queue"]}
    abciximab = by_drug["abciximab"]

    assert abciximab["suggested_source_refs"][0] == {
        "id": "source_2",
        "source_kind": "pubmed",
        "source_rank": 1,
        "url": "https://pubmed.ncbi.nlm.nih.gov/11907493/",
    }
    assert report["suggested_source_kind_counts"]["pubmed"] == 6
    assert report["suggested_source_kind_counts"]["label"] == 2
    assert report["suggested_source_kind_counts"]["secondary"] == 3


def test_value_provenance_report_lists_fully_mapped_warning_drugs() -> None:
    report = value_provenance_report(ROOT)

    assert "fully_mapped_warning_drugs" in report
    assert "partially_mapped_warning_drugs" in report
    assert "alfentanil" in report["fully_mapped_warning_drugs"]
    assert "felodipine" in report["fully_mapped_warning_drugs"]
    assert "abciximab" not in report["fully_mapped_warning_drugs"]
    assert "abciximab" in report["partially_mapped_warning_drugs"]
    assert "abciximab" not in report["unmapped_warning_drugs"]


def test_value_provenance_report_prioritizes_next_review_entries() -> None:
    report = value_provenance_report(ROOT)

    next_entries = report["next_review_entries"]
    next_details = report["next_review_details"]

    assert next_entries[0] == "inulin.t_half_h"
    assert set(next_entries) == set(report["unresolved_entries"])
    assert next_details[0]["entry"] == next_entries[0]
    assert next_details[0]["priority"] == "high"


def test_warning_half_life_source_resolution_rate_is_reported() -> None:
    report = value_provenance_report(ROOT)

    resolution = report["warning_t_half_source_id_resolution"]

    assert resolution["total"] == len(WARNING_DRUGS)
    assert resolution["resolved"] >= 12
    assert 0 < resolution["rate"] <= 1
