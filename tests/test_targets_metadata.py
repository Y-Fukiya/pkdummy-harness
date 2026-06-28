from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WARNING_SLUGS = {
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
}


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_targets_have_structured_auc_and_t_half_metadata() -> None:
    target_paths = sorted((ROOT / "drugs").glob("*/targets.yml"))
    assert target_paths

    for path in target_paths:
        targets = (load_yaml(path).get("targets") or {})
        auc = targets.get("auc") or {}
        t_half = targets.get("t_half") or {}
        assert auc.get("basis") == "dose_over_cl", path
        assert auc.get("target_basis") == "dose_over_cl_not_literature_auc", path
        assert auc.get("independent_literature_target") is False, path
        assert auc.get("source_value") == "CL_abs_L_per_h_at_70kg", path
        assert auc.get("role") == "consistency_check", path
        assert t_half.get("role") == "check_only", path
        assert t_half.get("used_to_calibrate_cl_v") is False, path
        assert isinstance(t_half.get("structural_mismatch"), dict), path
        assert isinstance(t_half["structural_mismatch"].get("acknowledged"), bool), path


def test_warning_targets_have_acknowledged_provenance_review() -> None:
    for slug in WARNING_SLUGS:
        targets = load_yaml(ROOT / "drugs" / slug / "targets.yml")
        mismatch = ((targets.get("targets") or {}).get("t_half") or {}).get("structural_mismatch") or {}
        review = targets.get("provenance_review") or {}
        assert mismatch.get("acknowledged") is True, slug
        assert mismatch.get("reason") == "one_compartment_fixture_approximation", slug
        assert review.get("status") == "acknowledged_fixture_limitation", slug
        assert review.get("reviewed_fields") == ["CL", "V", "t_half"], slug
        assert "not jointly calibrated" in str(review.get("reviewer_note") or ""), slug
