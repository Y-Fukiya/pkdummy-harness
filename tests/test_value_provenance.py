from __future__ import annotations

from pathlib import Path

import yaml

from tools.check_value_provenance import (
    REQUIRED_VALUE_PROVENANCE_FIELDS,
    WARNING_DRUGS,
    build_value_provenance_summary,
    value_provenance_report,
    validate_root,
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
    assert set(summary["checked_fields"]) >= set(REQUIRED_VALUE_PROVENANCE_FIELDS)
    assert "t_half_h" in summary["mismatch_acknowledged_fields"]
    assert isinstance(summary["source_ids"], list)
    assert summary["fields_needing_review"]


def test_value_provenance_summary_is_not_required_when_absent() -> None:
    summary = build_value_provenance_summary({}, {})

    assert summary["scope"] == "warning_drugs_only"
    assert summary["provenance_required"] is False
    assert summary["required_fields"] == []
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
    assert "abciximab.t_half_h" in report["unresolved_entries"]
    assert coverage["total"] == report["provenance_entries"]
    assert coverage["resolved"] == report["non_null_source_id_entries"]
    assert coverage["unresolved"] == len(report["unresolved_entries"])
    assert coverage["rate"] >= 0.5
    assert coverage_by_field["t_half_h"]["resolved"] >= 10
    assert coverage_by_field["CL_abs_L_per_h_at_70kg"]["total"] == len(WARNING_DRUGS)
    assert coverage_by_field["V_abs_L_at_70kg"]["total"] == len(WARNING_DRUGS)
    assert coverage_by_drug["abciximab"]["resolved"] == 0
    assert coverage_by_drug["felodipine"]["rate"] == 1.0


def test_value_provenance_report_explains_unresolved_review_reasons() -> None:
    report = value_provenance_report(ROOT)

    unresolved_details = {
        detail["entry"]: detail for detail in report["unresolved_entry_details"]
    }
    abciximab_half_life = unresolved_details["abciximab.t_half_h"]

    assert report["unresolved_reason_counts"]["source_id_missing"] == len(
        report["unresolved_entries"]
    )
    assert abciximab_half_life["field"] == "t_half_h"
    assert abciximab_half_life["role"] == "check_only"
    assert abciximab_half_life["priority"] == "high"
    assert abciximab_half_life["normalized_value"] == 0.3333333333333333
    assert abciximab_half_life["normalized_unit"] == "h"
    assert abciximab_half_life["reasons"] == [
        "source_id_missing",
        "needs_source_review",
    ]


def test_value_provenance_report_builds_source_review_queue() -> None:
    report = value_provenance_report(ROOT)

    queue = report["source_review_queue"]
    abciximab = queue[0]
    by_drug = {item["drug"]: item for item in queue}

    assert abciximab["drug"] == "abciximab"
    assert abciximab["highest_priority"] == "high"
    assert abciximab["coverage"]["resolved"] == 0
    assert abciximab["unresolved_fields"] == [
        "CL_abs_L_per_h_at_70kg",
        "V_abs_L_at_70kg",
        "t_half_h",
    ]
    assert abciximab["used_source_ids"] == []
    assert abciximab["available_source_ids"] == ["source_1", "source_2", "source_3", "source_4"]
    assert abciximab["unused_source_ids"] == ["source_1", "source_2", "source_3", "source_4"]
    assert by_drug["alfentanil"]["used_source_ids"] == ["source_1"]
    assert by_drug["alfentanil"]["unused_source_ids"] == []


def test_value_provenance_report_includes_source_refs_and_review_actions() -> None:
    report = value_provenance_report(ROOT)

    by_drug = {item["drug"]: item for item in report["source_review_queue"]}
    abciximab = by_drug["abciximab"]
    alfentanil = by_drug["alfentanil"]

    assert report["source_review_action_counts"]["inspect_unused_sources"] == 7
    assert report["source_review_action_counts"]["recheck_used_sources"] == 2
    assert abciximab["review_action"] == "inspect_unused_sources"
    assert abciximab["available_source_refs"][0] == {
        "id": "source_1",
        "source_kind": "drugbank",
        "source_rank": 3,
        "url": "https://go.drugbank.com/drugs/DB00054",
    }
    assert abciximab["unused_source_refs"] == abciximab["available_source_refs"]
    assert alfentanil["review_action"] == "recheck_used_sources"
    assert alfentanil["used_source_refs"] == [
        {
            "id": "source_1",
            "source_kind": "label",
            "source_rank": 0,
            "url": (
                "https://dailymed.nlm.nih.gov/dailymed/downloadpdffile.cfm?"
                "setId=c965d63f-933b-4a83-88f6-c8c74159530b"
            ),
        }
    ]


def test_value_provenance_report_prioritizes_suggested_source_refs_by_kind() -> None:
    report = value_provenance_report(ROOT)

    by_drug = {item["drug"]: item for item in report["source_review_queue"]}
    abciximab = by_drug["abciximab"]
    alfentanil = by_drug["alfentanil"]

    assert abciximab["suggested_source_refs"][0] == {
        "id": "source_2",
        "source_kind": "pubmed",
        "source_rank": 1,
        "url": "https://pubmed.ncbi.nlm.nih.gov/11907493/",
    }
    assert alfentanil["suggested_source_refs"] == alfentanil["used_source_refs"]
    assert report["suggested_source_kind_counts"]["pubmed"] == 6
    assert report["suggested_source_kind_counts"]["label"] == 3
    assert report["suggested_source_kind_counts"]["secondary"] == 3


def test_value_provenance_report_lists_fully_mapped_warning_drugs() -> None:
    report = value_provenance_report(ROOT)

    assert "fully_mapped_warning_drugs" in report
    assert "partially_mapped_warning_drugs" in report
    assert "felodipine" in report["fully_mapped_warning_drugs"]
    assert "abciximab" not in report["fully_mapped_warning_drugs"]
    assert "abciximab" in report["unmapped_warning_drugs"]


def test_value_provenance_report_prioritizes_next_review_entries() -> None:
    report = value_provenance_report(ROOT)

    next_entries = report["next_review_entries"]
    next_details = report["next_review_details"]

    assert next_entries[0] == "abciximab.t_half_h"
    assert "inulin.t_half_h" in next_entries[:3]
    assert set(next_entries) == set(report["unresolved_entries"])
    assert next_details[0]["entry"] == next_entries[0]
    assert next_details[0]["priority"] == "high"


def test_warning_half_life_source_resolution_rate_is_reported() -> None:
    report = value_provenance_report(ROOT)

    resolution = report["warning_t_half_source_id_resolution"]

    assert resolution["total"] == len(WARNING_DRUGS)
    assert resolution["resolved"] >= 10
    assert 0 < resolution["rate"] <= 1
