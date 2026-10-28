"""Carry clinical-assessment and computational-dose meaning across fixture exports."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml

try:
    from simulation_assessment import assess_fixture
except ModuleNotFoundError:
    from tools.simulation_assessment import assess_fixture

CONTEXT_FIELDS = ["CLINICAL_ASSESSMENT", "CLINICAL_USE", "HOLD_REASONS", "DOSE_PURPOSE", "CLINICAL_DOSE_VERIFIED", "HOLD_CANDIDATE"]


def _load(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Fixture context source must be a mapping: {path}")
    return value


def validate_context(context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(context, dict):
        raise ValueError("Fixture context must be a mapping")
    value = copy.deepcopy(context)
    if value.get("schema_version") != "1":
        raise ValueError("Fixture context schema_version must be 1")
    validity = value.get("simulation_validity") or {}
    if not isinstance(validity, dict):
        raise ValueError("Fixture context simulation_validity must be a mapping")
    if value.get("clinical_use") != "not_approved":
        raise ValueError("Fixture context CLINICAL_USE must be not_approved")
    if validity.get("status") not in {"not_assessed", "clinical_hold"}:
        raise ValueError("Fixture context has unsupported clinical assessment")
    reasons = validity.get("reasons")
    if not isinstance(reasons, list) or any(not isinstance(reason, str) or not reason.strip() for reason in reasons):
        raise ValueError("Fixture context hold reasons must be strings")
    if validity["status"] == "clinical_hold" and not reasons:
        raise ValueError("Fixture context must explain clinical_hold")
    if value.get("dose_purpose") != "computational_stress_test" or value.get("clinical_dose_verified") is not False:
        raise ValueError("Fixture context cannot claim verified clinical dosing")
    check = value.get("half_life_check")
    if not isinstance(check, dict):
        raise ValueError("Fixture context half_life_check must be a mapping")
    candidate = check.get("hold_candidate")
    if candidate is not None and not isinstance(candidate, bool):
        raise ValueError("Fixture context hold_candidate must be boolean or null")
    return value


def resolve_fixture_context(spec_path: Path | str | None = None, *, pk_path: Path | str | None = None, targets_path: Path | str | None = None) -> dict[str, Any]:
    spec_path = Path(spec_path) if spec_path is not None else None
    pk_path = Path(pk_path) if pk_path is not None else (spec_path.parent / "pk.yml" if spec_path else None)
    targets_path = Path(targets_path) if targets_path is not None else (spec_path.parent / "targets.yml" if spec_path else None)
    pk, targets, spec = _load(pk_path), _load(targets_path), _load(spec_path)
    validity = copy.deepcopy(pk.get("simulation_validity") or {"status": "not_assessed", "reasons": []})
    scenario = targets.get("scenario") or {}
    context = {
        "schema_version": "1", "clinical_use": "not_approved",
        "simulation_validity": validity,
        "dose_purpose": scenario.get("purpose", "computational_stress_test"),
        "clinical_dose_verified": scenario.get("clinical_dose_verified", False),
        "half_life_check": assess_fixture(pk, spec, targets)["half_life_check"],
        "context_source": {"spec_path": str(spec_path) if spec_path else None,
                           "pk_path": str(pk_path) if pk_path and pk_path.exists() else None,
                           "targets_path": str(targets_path) if targets_path and targets_path.exists() else None},
    }
    return validate_context(context)


def context_columns(context: dict[str, Any]) -> dict[str, str]:
    context = validate_context(context)
    candidate = context["half_life_check"].get("hold_candidate")
    return {
        "CLINICAL_ASSESSMENT": context["simulation_validity"]["status"],
        "CLINICAL_USE": context["clinical_use"],
        "HOLD_REASONS": json.dumps(context["simulation_validity"]["reasons"], ensure_ascii=False, separators=(",", ":")),
        "DOSE_PURPOSE": context["dose_purpose"], "CLINICAL_DOSE_VERIFIED": "false",
        "HOLD_CANDIDATE": "not_evaluable" if candidate is None else str(candidate).lower(),
    }


def attach_context(rows: list[dict[str, Any]], context: dict[str, Any], *, require_existing: bool = False) -> None:
    columns = context_columns(context)
    for row in rows:
        existing = [field for field in CONTEXT_FIELDS if field in row]
        if (existing or require_existing) and len(existing) != len(CONTEXT_FIELDS):
            raise ValueError("Fixture context columns are incomplete")
        for field in existing:
            if str(row[field]) != columns[field]:
                raise ValueError(f"Fixture context conflict in {field}")
        row.update(columns)


def inherit_fixture_context(sdtm_path: Path, ex_rows: list[dict[str, str]]) -> dict[str, Any]:
    manifest = _load(sdtm_path / "MANIFEST.yml")
    declared = manifest.get("fixture_context")
    if declared is not None:
        context = validate_context(declared)
        attach_context(ex_rows, context, require_existing=True)
        return context
    fields = [field for field in CONTEXT_FIELDS if ex_rows and field in ex_rows[0]]
    if fields:
        if len(fields) != len(CONTEXT_FIELDS):
            raise ValueError("Fixture context columns are incomplete")
        row = ex_rows[0]
        context = resolve_fixture_context()
        try:
            reasons = json.loads(row["HOLD_REASONS"])
        except (ValueError, TypeError) as exc:
            raise ValueError("Fixture context HOLD_REASONS is not valid JSON") from exc
        context["simulation_validity"] = {"status": row["CLINICAL_ASSESSMENT"], "reasons": reasons}
        context["clinical_use"] = row["CLINICAL_USE"]
        context["dose_purpose"] = row["DOSE_PURPOSE"]
        if row["CLINICAL_DOSE_VERIFIED"] != "false":
            raise ValueError("Fixture context cannot claim verified clinical dosing")
        flag = row["HOLD_CANDIDATE"]
        if flag not in {"true", "false", "not_evaluable"}:
            raise ValueError("Fixture context HOLD_CANDIDATE is invalid")
        context["half_life_check"]["hold_candidate"] = {"true": True, "false": False, "not_evaluable": None}[flag]
        context = validate_context(context)
        attach_context(ex_rows, context, require_existing=True)
        return context
    context = resolve_fixture_context()
    attach_context(ex_rows, context)
    return context
