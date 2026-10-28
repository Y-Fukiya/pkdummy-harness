"""Separate declared clinical assessment from computed fixture screening."""

from __future__ import annotations

import copy
import math
import re
from typing import Any


DEPENDENCY_FIELDS = {"CL_abs_L_per_h_at_70kg", "V_abs_L_at_70kg", "t_half_h"}
HALF_LIFE_THRESHOLD_FOLD = 1.5
SIMULATION_STATUSES = {"not_assessed", "clinical_hold"}
FIXTURE_PURPOSE = "computational_stress_test"
SELECTION_RULES = {
    "recorded_point_value", "range_midpoint", "range_midpoint_mixed_contexts",
    "upper_bound", "lower_bound", "censored_lower_bound", "derived_value", "legacy_fixture_value",
}
PROSE_IDENTIFIERS = {"F1", "CDA1", "V1", "V2", "m2", "t1"}


def _authored_prose(pk: dict[str, Any]) -> list[tuple[str, Any]]:
    validity = pk.get("simulation_validity") or {}
    fields = []
    for key in ("reasons", "correction_notes"):
        values = validity.get(key)
        if isinstance(values, list):
            fields.extend((f"simulation_validity.{key}[{index}]", value) for index, value in enumerate(values))
    fields.extend((f"pk_parsed.{key}", value) for key, value in (pk.get("pk_parsed") or {}).items() if key.endswith("_note"))
    for key, entry in (pk.get("value_provenance") or {}).items():
        prefix = f"value_provenance.{key}"
        fields.extend((f"{prefix}.{field}", entry.get(field)) for field in ("reviewer_note", "source_locator"))
        fields.append((f"{prefix}.selection.rationale", (entry.get("selection") or {}).get("rationale")))
        fields.extend((f"{prefix}.review_update.{field}", (entry.get("review_update") or {}).get(field)) for field in ("note", "note_en"))
    fields.extend(
        (f"fixture_limitations[{index}].{key}", entry.get(key))
        for index, entry in enumerate(pk.get("fixture_limitations") or [])
        for key in ("statement", "source_locator")
    )
    fields.extend((f"derived.notes[{index}]", value) for index, value in enumerate((pk.get("derived") or {}).get("notes") or []))
    return fields


def _editorial_issues(pk: dict[str, Any]) -> list[str]:
    issues = []
    validity = pk.get("simulation_validity") or {}
    def normalize(value: str) -> str:
        return " ".join(value.split()).casefold().rstrip(" .!?。！？")
    reason_values = validity.get("reasons")
    reasons = {normalize(value) for value in reason_values if isinstance(value, str)} if isinstance(reason_values, list) else set()
    notes = validity.get("correction_notes")
    if isinstance(notes, list):
        for note in notes:
            if isinstance(note, str) and normalize(note) in reasons:
                issues.append("simulation_validity.reasons and correction_notes contain a duplicate explanation")
    for path, value in _authored_prose(pk):
        if not isinstance(value, str):
            continue
        prose = re.sub(r"https?://\S+|`[^`]*`", " ", value)
        for token in re.findall(r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9-]*(?:\.\d+)*(?![A-Za-z0-9_])", prose):
            if re.search(r"[A-Za-z]\d", token) and token not in PROSE_IDENTIFIERS and not re.fullmatch(r"CYP\d+[A-Za-z]?\d*(?:-[A-Za-z]+)*|q\d+(?:-\d+)?h?", token):
                issues.append(f"{path}: missing space before numeric value in {token!r}")
    return issues


def _positive_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None


def validate_fixture_context(pk: dict[str, Any], spec: dict[str, Any], targets: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    validity = pk.get("simulation_validity")
    if not isinstance(validity, dict) or validity.get("status") not in SIMULATION_STATUSES:
        issues.append("simulation_validity.status must be explicit not_assessed or clinical_hold")
    else:
        reasons = validity.get("reasons")
        if not isinstance(reasons, list) or any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
            issues.append("simulation_validity.reasons must be a list of nonempty strings")
        elif validity["status"] == "clinical_hold" and not reasons:
            issues.append("simulation_validity.reasons must explain clinical_hold")
        if validity.get("source_correction_date"):
            notes = validity.get("correction_notes")
            if not isinstance(notes, list) or not notes or any(not isinstance(note, str) or not note.strip() for note in notes):
                issues.append("simulation_validity.correction_notes must record source corrections separately")
        issues.extend(_editorial_issues(pk))
    for field, entry in (pk.get("value_provenance") or {}).items():
        selection = entry.get("selection") or {}
        if selection.get("rule") not in SELECTION_RULES or not str(selection.get("rationale") or "").strip():
            issues.append(f"value_provenance.{field}.selection requires an explicit rule and rationale")
        dependencies = selection.get("depends_on", [])
        if not isinstance(dependencies, list) or any(not isinstance(item, str) or item not in DEPENDENCY_FIELDS for item in dependencies):
            issues.append(f"value_provenance.{field}.selection.depends_on must list recognized CL/V/half-life inputs")
        if selection.get("rule") == "derived_value" and not dependencies:
            issues.append(f"value_provenance.{field}.selection requires explicit depends_on inputs for a derived value")
    source_ids = {source.get("id") for source in pk.get("sources") or []}
    for limitation in pk.get("fixture_limitations") or []:
        if limitation.get("source_id") not in source_ids or not all(limitation.get(key) for key in ("code", "statement", "source_locator")):
            issues.append("fixture_limitations require a resolved source_id, code, statement and locator")
    scenario = targets.get("scenario") or {}
    if scenario.get("purpose") != FIXTURE_PURPOSE:
        issues.append(f"scenario.purpose must be {FIXTURE_PURPOSE}")
    if scenario.get("clinical_dose_verified") is not False:
        issues.append("scenario.clinical_dose_verified must be false for computational fixtures")
    target_dose = scenario.get("dose") or {}
    value = _positive_number(target_dose.get("value"))
    if target_dose.get("unit") != "mg" or value is None:
        issues.append("scenario.dose must be a finite positive mg amount")
    regimen = spec.get("regimen") or {}
    arms = regimen.get("arms") or {}
    if not arms:
        issues.append("regimen.arms must declare the computational dose")
    for arm_id, arm in arms.items():
        dose = _positive_number(arm.get("dose_mg"))
        if value is None or dose is None or not math.isclose(dose, value, rel_tol=1e-9, abs_tol=1e-12):
            issues.append(f"regimen.arms.{arm_id}.dose_mg disagrees with scenario.dose")
    return issues


def assess_fixture(pk: dict[str, Any], spec: dict[str, Any], targets: dict[str, Any]) -> dict[str, Any]:
    """Project numerical screening and the actual computational regimen without a clinical verdict."""
    parsed, derived = pk.get("pk_parsed") or {}, pk.get("derived") or {}
    reported = _positive_number(parsed.get("half_life_h"))
    cl = _positive_number(derived.get("CL_abs_L_per_h_at_70kg"))
    volume = _positive_number(derived.get("V_abs_L_at_70kg"))
    implied = math.log(2) * volume / cl if cl is not None and volume is not None else None
    implied = _positive_number(implied)
    ratio = _positive_number(implied / reported) if implied is not None and reported is not None else None
    candidate = None
    if ratio is not None:
        log_distance = abs(math.log(ratio))
        boundary = math.log(HALF_LIFE_THRESHOLD_FOLD)
        candidate = log_distance > boundary and not math.isclose(log_distance, boundary, rel_tol=1e-12, abs_tol=1e-12)
    provenance = pk.get("value_provenance") or {}
    circular = any(
        bool(DEPENDENCY_FIELDS.intersection(((provenance.get(field) or {}).get("selection") or {}).get("depends_on") or []))
        for field in DEPENDENCY_FIELDS
    )
    scenario = targets.get("scenario") or {}
    return {
        "half_life_check": {
            "evaluated": ratio is not None,
            "reported_h": reported,
            "implied_h": implied,
            "ratio": ratio,
            "threshold_fold": HALF_LIFE_THRESHOLD_FOLD,
            "hold_candidate": candidate,
            "circular": circular,
        },
        "dose_context": {
            "purpose": scenario.get("purpose"),
            "clinical_dose_verified": scenario.get("clinical_dose_verified"),
            "arms": copy.deepcopy((spec.get("regimen") or {}).get("arms") or {}),
        },
    }
