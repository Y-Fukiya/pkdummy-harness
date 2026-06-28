from __future__ import annotations

import math

from tools.target_metadata import build_target_metadata


def test_build_target_metadata_prefers_structured_target_fields_over_notes() -> None:
    pk = {
        "pk_parsed": {
            "half_life_h": 2.5,
            "clearance_basis": "systemic",
            "volume_basis": "systemic",
        },
        "derived": {
            "CL_abs_L_per_h_at_70kg": 10.0,
            "V_abs_L_at_70kg": 100.0,
        },
    }
    targets = {
        "targets": {
            "auc": {
                "value": 10000.0,
                "unit": "ng*h/mL",
                "summary": "geometric_mean",
                "basis": "dose_over_cl",
                "target_basis": "dose_over_cl_not_literature_auc",
                "independent_literature_target": False,
                "source_value": "CL_abs_L_per_h_at_70kg",
                "role": "consistency_check",
            },
            "t_half": {
                "value": 2.5,
                "unit": "h",
                "summary": "arithmetic_mean",
                "role": "check_only",
                "used_to_calibrate_cl_v": False,
                "structural_mismatch": {
                    "acknowledged": True,
                    "reason": "one_compartment_fixture_approximation",
                },
            },
        },
        "notes": ["This note intentionally does not contain Dose/CL."],
    }

    metadata = build_target_metadata("demo", pk, targets)

    assert metadata["drug"] == "demo"
    assert metadata["auc"]["basis"] == "dose_over_cl"
    assert metadata["auc"]["target_basis"] == "dose_over_cl_not_literature_auc"
    assert metadata["auc"]["independent_literature_target"] is False
    assert metadata["auc"]["source_value"] == "CL_abs_L_per_h_at_70kg"
    assert metadata["auc"]["role"] == "consistency_check"
    assert metadata["t_half"]["detected_structural_mismatch"] is True
    assert metadata["t_half"]["acknowledged_structural_mismatch"] is True
    assert metadata["t_half"]["structural_mismatch_reason"] == "one_compartment_fixture_approximation"
    assert metadata["t_half"]["used_to_calibrate_cl_v"] is False
    assert math.isclose(metadata["t_half"]["relative_error"], 1.7725887222397811)


def test_build_target_metadata_distinguishes_detected_from_acknowledged_mismatch() -> None:
    pk = {
        "pk_parsed": {"half_life_h": 2.5},
        "derived": {
            "CL_abs_L_per_h_at_70kg": 10.0,
            "V_abs_L_at_70kg": 100.0,
        },
    }
    targets = {
        "targets": {
            "auc": {"value": 10000.0, "unit": "ng*h/mL"},
            "t_half": {
                "value": 2.5,
                "unit": "h",
                "structural_mismatch": {"acknowledged": False},
            },
        }
    }

    metadata = build_target_metadata("unreviewed", pk, targets)

    assert metadata["t_half"]["detected_structural_mismatch"] is True
    assert metadata["t_half"]["acknowledged_structural_mismatch"] is False
    assert "known_structural_mismatch" not in metadata["t_half"]
