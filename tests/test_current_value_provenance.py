from __future__ import annotations

import copy
from pathlib import Path

import yaml

from tools.check_value_provenance import (
    REQUIRED_VALUE_PROVENANCE_FIELDS,
    WARNING_DRUGS,
    build_value_provenance_summary,
    validate_root,
    validate_value_provenance,
    value_provenance_report,
)


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_warning_drugs_have_checked_cl_v_t_half_value_provenance() -> None:
    for slug in WARNING_DRUGS:
        pk = load_yaml(ROOT / "drugs" / slug / "pk.yml")
        provenance = pk.get("value_provenance") or {}
        for field in REQUIRED_VALUE_PROVENANCE_FIELDS:
            entry = provenance.get(field) or {}
            assert entry.get("source_id"), f"{slug}: {field} is unmapped"
            assert entry.get("source_review_status") == "checked", f"{slug}: {field}"


def test_value_provenance_source_ids_and_normalized_values_resolve() -> None:
    issues = validate_root(ROOT)
    assert not [issue for issue in issues if "source_id does not resolve" in issue]
    assert not [issue for issue in issues if "normalized_value mismatch" in issue]


def test_mismatch_half_life_is_check_only_and_acknowledged() -> None:
    for slug in WARNING_DRUGS:
        pk = load_yaml(ROOT / "drugs" / slug / "pk.yml")
        targets = load_yaml(ROOT / "drugs" / slug / "targets.yml")
        half_life = (pk.get("value_provenance") or {}).get("t_half_h") or {}
        structural_mismatch = (((targets.get("targets") or {}).get("t_half") or {}).get("structural_mismatch") or {})
        assert half_life.get("role") == "check_only", slug
        assert half_life.get("fixture_limitation_status") == "acknowledged", slug
        assert structural_mismatch.get("acknowledged") is True, slug


def test_value_provenance_report_is_fully_source_mapped() -> None:
    report = value_provenance_report(ROOT)

    assert report["fields_needing_review"] == []
    assert report["unresolved_entries"] == []
    assert report["source_mapping_coverage"]["rate"] == 1.0
    assert report["source_review_status_counts"]["checked"] == report["provenance_entries"]
    assert report["source_review_queue"] == []
    assert report["next_review_entries"] == []
    assert set(report["fully_mapped_warning_drugs"]) == set(WARNING_DRUGS)
    assert report["partially_mapped_warning_drugs"] == []


def test_value_provenance_summary_reports_all_checked_fields() -> None:
    pk = load_yaml(ROOT / "drugs" / "aciclovir" / "pk.yml")
    targets = load_yaml(ROOT / "drugs" / "aciclovir" / "targets.yml")

    summary = build_value_provenance_summary(pk, targets)

    assert summary["required_fields"] == REQUIRED_VALUE_PROVENANCE_FIELDS
    assert set(summary["metadata_present_fields"]) == set(REQUIRED_VALUE_PROVENANCE_FIELDS)
    assert set(summary["source_checked_fields"]) == set(REQUIRED_VALUE_PROVENANCE_FIELDS)
    assert set(summary["fields_needing_review"]) == set()
    assert "t_half_h" in summary["mismatch_acknowledged_fields"]


def test_source_verification_contract_still_rejects_invalid_metadata() -> None:
    pk = load_yaml(ROOT / "drugs" / "inulin" / "pk.yml")
    targets = load_yaml(ROOT / "drugs" / "inulin" / "targets.yml")
    half_life = pk["value_provenance"]["t_half_h"]
    half_life["source_id"] = None
    half_life["source_review_status"] = "needs_source_review"
    half_life["source_verification"] = {
        "status": "maybe",
        "blocker": "maybe_missing",
        "next_action": "guess_source_id",
        "fixture_value_decision": "replace_by_guessing",
        "decision_reason": "",
        "reviewed_source_ids": ["missing_source"],
        "reviewed_external_queries": [],
    }

    issues = validate_value_provenance("inulin", pk, targets, required=True)
    assert any("source_verification.status has invalid enum" in issue for issue in issues)
    assert any("source_verification.blocker has invalid enum" in issue for issue in issues)
    assert any("source_verification.next_action has invalid enum" in issue for issue in issues)
    assert any("source_verification.fixture_value_decision has invalid enum" in issue for issue in issues)
    assert any("decision_reason must be non-empty" in issue for issue in issues)
    assert any("reviewed_source_ids has unresolved id" in issue for issue in issues)


def test_source_verification_contract_does_not_mutate_repository_state() -> None:
    pk = load_yaml(ROOT / "drugs" / "inulin" / "pk.yml")
    targets = load_yaml(ROOT / "drugs" / "inulin" / "targets.yml")
    mutated = copy.deepcopy(pk)
    mutated["value_provenance"]["t_half_h"]["source_id"] = None
    mutated["value_provenance"]["t_half_h"]["source_review_status"] = "needs_source_review"
    mutated["value_provenance"]["t_half_h"]["source_verification"] = {
        "status": "no_exact_public_source_match",
        "blocker": "exact_value_not_found_in_public_primary_source",
        "next_action": "add_primary_source_or_replace_fixture_value",
        "fixture_value_decision": "retain_current_fixture_value_pending_primary_source",
        "decision_reason": "synthetic unresolved fixture for validator testing",
        "reviewed_source_ids": ["source_1"],
        "reviewed_external_queries": [],
    }
    assert validate_value_provenance("inulin", mutated, targets, required=True) == []
    assert validate_root(ROOT) == []
