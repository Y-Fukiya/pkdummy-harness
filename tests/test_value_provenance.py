from __future__ import annotations

from pathlib import Path

import yaml

from tools.check_value_provenance import (
    REQUIRED_VALUE_PROVENANCE_FIELDS,
    WARNING_DRUGS,
    build_value_provenance_summary,
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
        assert half_life.get("reviewer_status") == "acknowledged_fixture_limitation", slug
        assert structural_mismatch.get("acknowledged") is True, slug


def test_value_provenance_summary_reports_checked_and_review_fields() -> None:
    pk = load_yaml(ROOT / "drugs" / "aciclovir" / "pk.yml")
    targets = load_yaml(ROOT / "drugs" / "aciclovir" / "targets.yml")

    summary = build_value_provenance_summary(pk, targets)

    assert summary["required_fields"] == REQUIRED_VALUE_PROVENANCE_FIELDS
    assert set(summary["checked_fields"]) >= set(REQUIRED_VALUE_PROVENANCE_FIELDS)
    assert "t_half_h" in summary["mismatch_acknowledged_fields"]
    assert isinstance(summary["source_ids"], list)
    assert summary["fields_needing_review"]
