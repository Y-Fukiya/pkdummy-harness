"""Build machine-readable target provenance metadata for workflow manifests."""

from __future__ import annotations

import math
from typing import Any


ATTAINABILITY_WARN_REL = 0.25


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _notes_text(*blocks: Any) -> str:
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, list):
            parts.extend(str(item) for item in block)
        elif block:
            parts.append(str(block))
    return "\n".join(parts).lower()


def infer_auc_metadata(targets: dict[str, Any], notes_text: str) -> dict[str, Any]:
    auc = ((targets.get("targets") or {}).get("auc") or {})
    has_auc = bool(auc)
    explicit_basis = auc.get("basis")
    if explicit_basis:
        basis = str(explicit_basis)
    elif has_auc and ("dose/cl" in notes_text or "computed as dose/cl" in notes_text):
        basis = "dose_over_cl"
    elif has_auc:
        basis = "unspecified"
    else:
        basis = "not_provided"

    if basis == "dose_over_cl":
        target_basis = str(auc.get("target_basis") or "dose_over_cl_not_literature_auc")
        independent = bool(auc.get("independent_literature_target", False))
    elif has_auc:
        target_basis = str(auc.get("target_basis") or "unspecified_auc_target")
        independent = auc.get("independent_literature_target")
    else:
        target_basis = "not_provided"
        independent = None

    return {
        "basis": basis,
        "target_basis": target_basis,
        "independent_literature_target": independent,
        "source_value": auc.get("source_value"),
        "role": auc.get("role"),
        "value": auc.get("value"),
        "unit": auc.get("unit"),
        "summary": auc.get("summary"),
    }


def infer_t_half_metadata(pk: dict[str, Any], targets: dict[str, Any], notes_text: str) -> dict[str, Any]:
    parsed = pk.get("pk_parsed") or {}
    derived = pk.get("derived") or {}
    target = ((targets.get("targets") or {}).get("t_half") or {})
    mismatch = target.get("structural_mismatch") if isinstance(target.get("structural_mismatch"), dict) else {}

    t_half = _to_float(parsed.get("half_life_h"))
    target_t_half = _to_float(target.get("value"))
    cl_abs = _to_float(derived.get("CL_abs_L_per_h_at_70kg"))
    v_abs = _to_float(derived.get("V_abs_L_at_70kg"))
    implied_t_half = None
    rel_error = None
    status = "NA"
    if t_half and cl_abs and v_abs and cl_abs > 0:
        implied_t_half = math.log(2.0) * v_abs / cl_abs
        rel_error = abs(implied_t_half - t_half) / abs(t_half)
        status = "WARN" if rel_error > ATTAINABILITY_WARN_REL else "OK"

    detected = bool(status == "WARN")
    note_marks_acknowledged = "known 1-compartment attainability issue" in notes_text
    acknowledged = bool(mismatch.get("acknowledged", note_marks_acknowledged))
    return {
        "basis": str(target.get("basis") or ("literature_target_retained_as_check" if "not used to recalibrate" in notes_text else "target_check")),
        "role": target.get("role"),
        "used_to_calibrate_cl_v": target.get("used_to_calibrate_cl_v"),
        "value": target.get("value"),
        "unit": target.get("unit"),
        "summary": target.get("summary"),
        "pk_parsed_half_life_h": t_half,
        "target_half_life_h": target_t_half,
        "cl_v_implied_half_life_h": implied_t_half,
        "relative_error": rel_error,
        "warning_threshold": ATTAINABILITY_WARN_REL,
        "attainability_status": status,
        "detected_structural_mismatch": detected,
        "acknowledged_structural_mismatch": acknowledged,
        "structural_mismatch_reason": mismatch.get("reason"),
    }


def build_target_metadata(drug: str | None, pk: dict[str, Any], targets: dict[str, Any]) -> dict[str, Any]:
    notes = _notes_text(targets.get("notes"))
    parsed = pk.get("pk_parsed") or {}
    return {
        "drug": drug,
        "parameter_pair_policy": "spec_theta_uses_pk_yml_derived_cl_v_abs",
        "clearance_basis": parsed.get("clearance_basis"),
        "volume_basis": parsed.get("volume_basis"),
        "auc": infer_auc_metadata(targets, notes),
        "t_half": infer_t_half_metadata(pk, targets, notes),
        "limitations": [
            "AUC targets marked dose_over_cl are integration consistency checks, not independent literature AUC validation.",
            "Detected structural mismatches mean CL/V and t_half cannot both be exactly attained by this 1-compartment fixture.",
            "Acknowledged structural mismatches are retained intentionally as fixture limitations or stress-test labels.",
        ],
    }
