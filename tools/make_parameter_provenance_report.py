#!/usr/bin/env python3
"""Export a reviewable inventory of PK fixture parameter provenance.

The canonical inputs remain ``drugs/<slug>/pk.yml``, ``targets.yml`` and
``spec_pk1_*.yml``.  This tool only reads those files and writes a long CSV,
source catalog, Markdown guide and a small YAML manifest.  It deliberately
does not infer an exact paper-to-parameter mapping from a URL alone: when a
value-level mapping is absent, the report says so explicitly.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml


REPORT_VERSION = "1.0"
CSV_FIELDS = [
    "record_type",
    "drug",
    "drug_id",
    "route",
    "spec_file",
    "parameter",
    "source_field",
    "fixture_value",
    "fixture_unit",
    "reference_value",
    "reference_unit",
    "value_basis",
    "role",
    "basis",
    "source_id",
    "source_url",
    "source_record_index",
    "source_review_status",
    "source_mapping_status",
    "source_verification_status",
    "source_review_blocker",
    "source_verification_note",
    "reviewer_status",
    "reviewer_note",
    "fixture_limitation_status",
    "raw_value",
    "raw_unit",
    "normalized_value",
    "normalized_unit",
    "pk_raw_excerpt",
    "conversion_method",
    "conversion_formula",
    "assumptions",
    "reference_status",
    "notes",
]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _same_number(left: Any, right: Any) -> bool:
    left_number = _number(left)
    right_number = _number(right)
    if left_number is None or right_number is None:
        return False
    tolerance = max(1e-10, abs(right_number) * 1e-8)
    return abs(left_number - right_number) <= tolerance


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return " ".join(str(value).split())


def _pk_raw_excerpt(value: Any, limit: int = 2000) -> str:
    """Return a bounded, single-line rendering of the canonical pk_raw block."""
    text = _text(value)
    return text if len(text) <= limit else f"{text[: limit - 3]}..."


def _path_value(mapping: dict[str, Any], dotted_path: str) -> Any:
    current: Any = mapping
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _source_catalog(sources: Any) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    if not isinstance(sources, list):
        return catalog
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            continue
        source_id = source.get("id")
        catalog.append(
            {
                "source_id": _text(source_id),
                "source_key": _text(source_id) or f"source[{index}]",
                "source_url": _text(source.get("url")),
                "source_record_index": index,
            }
        )
    return catalog


def _source_by_id(catalog: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(item["source_id"]): item
        for item in catalog
        if str(item.get("source_id") or "")
    }


def _spec_path(drug_dir: Path) -> Path | None:
    candidates = sorted(drug_dir.glob("spec_pk1_*.yml"))
    return candidates[0] if candidates else None


def _provenance_entry(pk: dict[str, Any], key: str) -> dict[str, Any]:
    value = (pk.get("value_provenance") or {}).get(key)
    return value if isinstance(value, dict) else {}


def _provenance_fields(
    pk: dict[str, Any],
    key: str,
    source_map: dict[str, dict[str, Any]],
) -> dict[str, str]:
    entry = _provenance_entry(pk, key)
    source_id = _text(entry.get("source_id"))
    source = source_map.get(source_id, {})
    source_verification = entry.get("source_verification")
    source_verification = source_verification if isinstance(source_verification, dict) else {}
    if source_id and source_id not in source_map:
        source_mapping_status = "source_id_unresolved"
    elif source_id and _text(entry.get("source_review_status")) == "checked":
        source_mapping_status = "checked"
    elif source_id:
        source_mapping_status = "source_id_present_needs_review"
    else:
        source_mapping_status = "needs_source_mapping"
    return {
        "source_field": _text(entry.get("source_field")),
        "value_basis": _text(entry.get("value_basis")),
        "role": _text(entry.get("role")),
        "basis": _text(entry.get("basis")),
        "source_id": source_id,
        "source_url": _text(source.get("source_url")),
        "source_record_index": _text(source.get("source_record_index")),
        "source_review_status": _text(entry.get("source_review_status")),
        "source_mapping_status": source_mapping_status,
        "source_review_blocker": _text(source_verification.get("blocker")),
        "source_verification_note": _text(source_verification.get("reviewer_note")),
        "reviewer_status": _text(entry.get("reviewer_status")),
        "reviewer_note": _text(entry.get("reviewer_note")),
        "fixture_limitation_status": _text(entry.get("fixture_limitation_status")),
        "raw_value": _text(entry.get("raw_value")),
        "raw_unit": _text(entry.get("raw_unit")),
        "normalized_value": _text(entry.get("normalized_value")),
        "normalized_unit": _text(entry.get("normalized_unit")),
        "conversion_method": _text(_path_value(entry, "conversion.method")),
        "conversion_formula": _text(_path_value(entry, "conversion.formula")),
        "assumptions": _text(_path_value(entry, "conversion.assumptions")),
        "source_verification_status": _text(source_verification.get("status")),
    }


def _row(**values: Any) -> dict[str, str]:
    result = {field: "" for field in CSV_FIELDS}
    for field, value in values.items():
        if field in result:
            result[field] = _text(value)
    return result


def _pk_rows(
    *,
    slug: str,
    pk: dict[str, Any],
    spec_path: Path | None,
    source_map: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    parsed = pk.get("pk_parsed") or {}
    derived = pk.get("derived") or {}
    route = _text(pk.get("route_inferred"))
    shared = {
        "drug": slug,
        "drug_id": pk.get("id"),
        "route": route,
        "spec_file": spec_path.name if spec_path else "",
        "record_type": "pk_parameter",
        "pk_raw_excerpt": _pk_raw_excerpt(pk.get("pk_raw")),
    }
    definitions = [
        ("pk_parsed.half_life_h", "t_half_h", parsed.get("half_life_h"), "h", "t_half_h"),
        (
            "pk_parsed.clearance",
            "clearance",
            _path_value(pk, "pk_parsed.clearance.value"),
            _path_value(pk, "pk_parsed.clearance.unit"),
            "CL_abs_L_per_h_at_70kg",
        ),
        (
            "pk_parsed.volume",
            "volume",
            _path_value(pk, "pk_parsed.volume.value"),
            _path_value(pk, "pk_parsed.volume.unit"),
            "V_abs_L_at_70kg",
        ),
        (
            "pk_parsed.bioavailability_frac",
            "bioavailability",
            parsed.get("bioavailability_frac"),
            "fraction",
            "pk_parsed.bioavailability_frac",
        ),
        (
            "derived.CL_abs_L_per_h_at_70kg",
            "CL_abs_L_per_h_at_70kg",
            derived.get("CL_abs_L_per_h_at_70kg"),
            "L/h",
            "CL_abs_L_per_h_at_70kg",
        ),
        (
            "derived.V_abs_L_at_70kg",
            "V_abs_L_at_70kg",
            derived.get("V_abs_L_at_70kg"),
            "L",
            "V_abs_L_at_70kg",
        ),
        (
            "derived.CL_systemic_L_per_h_at_70kg",
            "CL_systemic_L_per_h_at_70kg",
            derived.get("CL_systemic_L_per_h_at_70kg"),
            "L/h",
            "",
        ),
        (
            "derived.V_systemic_L_at_70kg",
            "V_systemic_L_at_70kg",
            derived.get("V_systemic_L_at_70kg"),
            "L",
            "",
        ),
        ("derived.ke_1_per_h", "ke_1_per_h", derived.get("ke_1_per_h"), "1/h", ""),
    ]
    rows: list[dict[str, str]] = []
    for source_field, parameter, value, unit, provenance_key in definitions:
        if value is None:
            continue
        provenance_entry = _provenance_entry(pk, provenance_key) if provenance_key else {}
        metadata = _provenance_fields(pk, provenance_key, source_map) if provenance_entry else {}
        mapping_status = "not_applicable"
        if provenance_entry:
            mapping_status = metadata.get("source_mapping_status")
            if mapping_status == "checked":
                reference_status = "value_level_metadata"
            elif mapping_status == "source_id_present_needs_review":
                reference_status = "value_level_metadata_needs_source_review"
            elif mapping_status == "source_id_unresolved":
                reference_status = "value_level_metadata_source_id_unresolved"
            else:
                reference_status = "value_level_metadata_needs_source_mapping"
        elif pk.get("sources"):
            mapping_status = "source_url_present_not_parameter_mapped"
            reference_status = "source_url_present_not_parameter_mapped"
        else:
            mapping_status = "not_recorded"
            reference_status = "no_source_url_in_pk_yml"
        if source_field.startswith("derived."):
            metadata.setdefault("value_basis", "derived_from_reported")
            metadata.setdefault("role", "derived_output")
            if not metadata.get("conversion_formula"):
                metadata["conversion_formula"] = {
                    "derived.CL_abs_L_per_h_at_70kg": "pk_parsed.clearance.value after unit/body-weight normalization",
                    "derived.V_abs_L_at_70kg": "pk_parsed.volume.value after unit/body-weight normalization",
                    "derived.CL_systemic_L_per_h_at_70kg": "derived.CL_apparent_L_per_h_at_70kg * pk_parsed.bioavailability_frac",
                    "derived.V_systemic_L_at_70kg": "derived.V_apparent_L_at_70kg * pk_parsed.bioavailability_frac",
                    "derived.ke_1_per_h": "derived.CL_abs_L_per_h_at_70kg / derived.V_abs_L_at_70kg",
                }.get(source_field, "")
            if reference_status == "source_url_present_not_parameter_mapped":
                reference_status = "derived_from_pk_yml_source_fields"
        notes = []
        if parameter in {"CL_abs_L_per_h_at_70kg", "V_abs_L_at_70kg"}:
            notes.append("Canonical independent CL/V values used by the 1-compartment fixture; inspect basis and conversion before external use.")
        if parameter in {"CL_systemic_L_per_h_at_70kg", "V_systemic_L_at_70kg"}:
            notes.append("Derived systemic value; do not treat as directly reported unless the source mapping says so.")
        if parameter == "bioavailability":
            notes.append("Used to distinguish apparent CL/F or V/F from systemic CL/V; model F1 may intentionally differ.")
        mapped_source_field = metadata.pop("source_field", "") or source_field
        metadata.setdefault("source_mapping_status", mapping_status)
        reference_value = value if metadata["source_mapping_status"] == "checked" else ""
        reference_unit = unit if reference_value != "" else ""
        rows.append(
            _row(
                **shared,
                parameter=parameter,
                source_field=mapped_source_field,
                fixture_value=value,
                fixture_unit=unit,
                reference_value=reference_value,
                reference_unit=reference_unit,
                reference_status=reference_status,
                notes=" ".join(notes),
                **metadata,
            )
        )
    return rows


def _model_rows(
    *,
    slug: str,
    pk: dict[str, Any],
    spec: dict[str, Any],
    spec_path: Path,
    source_map: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    theta = _path_value(spec, "model.theta") or {}
    if not isinstance(theta, dict):
        theta = {}
    parsed = pk.get("pk_parsed") or {}
    derived = pk.get("derived") or {}
    route = _text(_path_value(spec, "regimen.route") or pk.get("route_inferred"))
    shared = {
        "record_type": "model_parameter",
        "drug": slug,
        "drug_id": pk.get("id"),
        "route": route,
        "spec_file": spec_path.name,
        "pk_raw_excerpt": _pk_raw_excerpt(pk.get("pk_raw")),
    }
    rows: list[dict[str, str]] = []
    for parameter, value in theta.items():
        reference_value: Any = None
        reference_field = ""
        reference_unit = ""
        status = "fixture_policy_no_external_source"
        notes = "Model specification value; no direct source mapping is claimed by this report."
        metadata: dict[str, str] = {}
        mapping_status = "not_applicable"
        if parameter == "CL":
            reference_value = derived.get("CL_abs_L_per_h_at_70kg")
            reference_field = "derived.CL_abs_L_per_h_at_70kg"
            reference_unit = "L/h"
            provenance = _provenance_entry(pk, "CL_abs_L_per_h_at_70kg")
            metadata = _provenance_fields(pk, "CL_abs_L_per_h_at_70kg", source_map) if provenance else {}
            if _same_number(value, reference_value):
                mapping_status = metadata.get("source_mapping_status", "needs_source_mapping")
                status = {
                    "checked": "mapped_to_pk_derived",
                    "source_id_present_needs_review": "mapped_to_pk_derived_needs_source_review",
                    "source_id_unresolved": "mapped_to_pk_derived_source_id_unresolved",
                }.get(mapping_status, "mapped_to_pk_derived_needs_source_mapping")
            else:
                mapping_status = "not_recorded"
                status = "fixture_override_needs_review"
            notes = "Compare with pk.yml derived CL and confirm apparent/systemic basis."
        elif parameter == "V":
            reference_value = derived.get("V_abs_L_at_70kg")
            reference_field = "derived.V_abs_L_at_70kg"
            reference_unit = "L"
            provenance = _provenance_entry(pk, "V_abs_L_at_70kg")
            metadata = _provenance_fields(pk, "V_abs_L_at_70kg", source_map) if provenance else {}
            if _same_number(value, reference_value):
                mapping_status = metadata.get("source_mapping_status", "needs_source_mapping")
                status = {
                    "checked": "mapped_to_pk_derived",
                    "source_id_present_needs_review": "mapped_to_pk_derived_needs_source_review",
                    "source_id_unresolved": "mapped_to_pk_derived_source_id_unresolved",
                }.get(mapping_status, "mapped_to_pk_derived_needs_source_mapping")
            else:
                mapping_status = "not_recorded"
                status = "fixture_override_needs_review"
            notes = "Compare with pk.yml derived V and confirm apparent/systemic basis."
        elif parameter == "F1":
            reference_value = parsed.get("bioavailability_frac")
            reference_field = "pk_parsed.bioavailability_frac"
            reference_unit = "fraction"
            if route in {"oral", "po", "sl", "sublingual"}:
                basis = str(parsed.get("clearance_basis") or "").lower()
                status = f"fixture_policy_{basis}_parameters"
                notes = (
                    "Systemic CL/V uses the selected bioavailability as F1; inspect its source and selection policy."
                    if basis == "systemic"
                    else "Apparent CL/F and V/F use F1=1; this is a parameterization policy, not a claim of complete bioavailability."
                )
            else:
                status = "fixture_policy_no_external_source"
                notes = "F1 is a model parameterization policy, not an independent source claim."
        elif parameter in {"KA", "ALAG1"}:
            status = "fixture_policy_no_external_source"
            notes = "Absorption parameter supplied by the demo spec; add a drug-specific source mapping before treating it as literature-supported."
        if mapping_status != "checked":
            reference_value = None
            reference_unit = ""
        for key in ("source_field", "value_basis", "role", "basis"):
            metadata.pop(key, None)
        metadata.setdefault("source_mapping_status", mapping_status)
        rows.append(
            _row(
                **shared,
                parameter=f"model.theta.{parameter}",
                source_field=reference_field,
                fixture_value=value,
                fixture_unit="fraction" if parameter == "F1" else "",
                reference_value=reference_value,
                reference_unit=reference_unit,
                value_basis="fixture_policy" if parameter in {"KA", "ALAG1", "F1"} else "derived_from_reported",
                role="simulation_parameter",
                reference_status=status,
                notes=notes,
                **metadata,
            )
        )
    return rows


def _variability_rows(*, slug: str, pk: dict[str, Any], spec: dict[str, Any], spec_path: Path) -> list[dict[str, str]]:
    route = _text(_path_value(spec, "regimen.route") or pk.get("route_inferred"))
    shared = {
        "record_type": "model_variability",
        "drug": slug,
        "drug_id": pk.get("id"),
        "route": route,
        "spec_file": spec_path.name,
        "value_basis": "fixture_policy",
        "role": "simulation_parameter",
        "reference_status": "fixture_policy_no_external_source",
        "source_mapping_status": "not_applicable",
        "notes": "IIV/residual-error value from the demo spec; not a direct literature estimate unless separately mapped.",
    }
    rows: list[dict[str, str]] = []
    eta = _path_value(spec, "iiv.eta") or {}
    if isinstance(eta, dict):
        for parameter, value in eta.items():
            rows.append(_row(**shared, parameter=f"iiv.eta.{parameter}", fixture_value=value, fixture_unit="omega^2"))
    residual = spec.get("residual") or {}
    if isinstance(residual, dict):
        for parameter in ("prop", "add"):
            if parameter in residual:
                rows.append(_row(**shared, parameter=f"residual.{parameter}", fixture_value=residual[parameter], fixture_unit="fraction" if parameter == "prop" else "concentration"))
    return rows


def _target_rows(*, slug: str, pk: dict[str, Any], targets: dict[str, Any], spec_path: Path | None) -> list[dict[str, str]]:
    route = _text(pk.get("route_inferred"))
    target_map = _path_value(targets, "targets") or {}
    if not isinstance(target_map, dict):
        return []
    rows: list[dict[str, str]] = []
    for name, target in target_map.items():
        if not isinstance(target, dict) or "value" not in target:
            continue
        basis = _text(target.get("basis") or target.get("target_basis"))
        source_field = _text(target.get("source_value"))
        reference_status = "derived_target" if basis == "dose_over_cl" else "target_without_source_mapping"
        notes = _text(target.get("summary"))
        if basis == "dose_over_cl":
            notes = f"Computed target; source_value={source_field or 'not recorded'}. Not an independent literature AUC."
        rows.append(
            _row(
                record_type="target",
                drug=slug,
                drug_id=pk.get("id"),
                route=route,
                spec_file=spec_path.name if spec_path else "",
                parameter=f"targets.{name}",
                source_field=source_field,
                fixture_value=target.get("value"),
                fixture_unit=target.get("unit"),
                reference_value="",
                reference_unit="",
                value_basis=basis or "unknown_needs_review",
                role=target.get("role"),
                basis=basis,
                reference_status=reference_status,
                source_mapping_status="not_applicable",
                notes=notes,
            )
        )
    return rows


def _build_rows(root: Path, selected_drugs: set[str] | None = None) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    parameter_rows: list[dict[str, str]] = []
    source_rows: list[dict[str, str]] = []
    summary_rows: list[dict[str, str]] = []
    for pk_path in sorted((root / "drugs").glob("*/pk.yml")):
        slug = pk_path.parent.name
        if selected_drugs and slug not in selected_drugs:
            continue
        pk = load_yaml(pk_path)
        targets_path = pk_path.parent / "targets.yml"
        targets = load_yaml(targets_path) if targets_path.exists() else {}
        spec_path = _spec_path(pk_path.parent)
        spec = load_yaml(spec_path) if spec_path else {}
        catalog = _source_catalog(pk.get("sources"))
        source_map = _source_by_id(catalog)
        for source in catalog:
            source_rows.append(
                {
                    "drug": slug,
                    "drug_id": _text(pk.get("id")),
                    "source_id": _text(source.get("source_id")),
                    "source_key": _text(source.get("source_key")),
                    "source_url": _text(source.get("source_url")),
                    "source_record_index": _text(source.get("source_record_index")),
                }
            )
        drug_rows = _pk_rows(slug=slug, pk=pk, spec_path=spec_path, source_map=source_map)
        if spec_path:
            drug_rows.extend(_model_rows(slug=slug, pk=pk, spec=spec, spec_path=spec_path, source_map=source_map))
            drug_rows.extend(_variability_rows(slug=slug, pk=pk, spec=spec, spec_path=spec_path))
        drug_rows.extend(_target_rows(slug=slug, pk=pk, targets=targets, spec_path=spec_path))
        parameter_rows.extend(drug_rows)
        mapped = sum(1 for row in drug_rows if row["source_mapping_status"] == "checked")
        summary_rows.append(
            _row(
                record_type="drug_summary",
                drug=slug,
                drug_id=pk.get("id"),
                route=pk.get("route_inferred"),
                spec_file=spec_path.name if spec_path else "",
                fixture_value=len(drug_rows),
                fixture_unit="parameter rows",
                reference_value=mapped,
                reference_unit="checked source-mapping rows",
                reference_status="source_urls_present" if catalog else "no_source_urls",
                notes=f"source_count={len(catalog)}; value_level_metadata_fields={len(pk.get('value_provenance') or {}) if isinstance(pk.get('value_provenance'), dict) else 0}",
            )
        )
    parameter_rows.sort(key=lambda row: (row["drug"], row["record_type"], row["parameter"]))
    source_rows.sort(key=lambda row: (row["drug"], int(row["source_record_index"] or 0)))
    summary_rows.sort(key=lambda row: row["drug"])
    return parameter_rows, source_rows, summary_rows


def _write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _markdown_escape(value: Any) -> str:
    return _text(value).replace("|", "\\|")


def _write_markdown(path: Path, parameter_rows: list[dict[str, str]], source_rows: list[dict[str, str]], summary_rows: list[dict[str, str]]) -> None:
    lines = [
        "# PK fixture parameter provenance inventory",
        "",
        "この一覧は `drugs/*/pk.yml`、`targets.yml`、`spec_pk1_*.yml` を読み取り、値の由来を確認するための監査用出力です。ソースURLが存在することだけでは、URL内のどの記載が特定の値に対応するかを証明しません。`reference_status` を必ず確認してください。",
        "",
        "## 読み方",
        "",
        "- `value_level_metadata`: `pk.yml.value_provenance` に解決済みsource_idがあり、source_review_status=checked。",
        "- `value_level_metadata_needs_source_mapping`: value_provenanceはあるが、値単位のsource_idが未記録。",
        "- `value_level_metadata_needs_source_review`: source_idはあるが、値単位のreviewが未完了。",
        "- `source_mapping_status=checked`: その行のsource_idと値単位reviewが確認済み。これ以外は直接の科学的根拠として扱わない。",
        "- `mapped_to_pk_derived`: specのCL/Vが `pk.yml.derived` と一致する。",
        "- `derived_from_pk_yml_source_fields`: pk.yml内のparsed値から導出された値で、独立した直接報告値ではない。",
        "- `source_url_present_not_parameter_mapped`: URLはあるが、特定パラメータとの直接対応は未記録。",
        "- `fixture_policy_*`: デモ用specの仮定。外部文献値として扱わない。",
        "",
        "CSVの全行は `PARAMETER_PROVENANCE.csv`、URLの全件は `SOURCES.csv` にあります。`raw_*`/`normalized_*`/`pk_raw_excerpt`/`conversion_*` と検証状態を併読してください。URL本文の直接引用や査読をこの一覧だけで代替しないでください。数値の変更はこの出力では行わず、canonicalなYAMLを更新してから再生成してください。",
        "",
        "## 薬剤別サマリー",
        "",
        "| Drug | Route | Spec | Source URLs | Parameter rows | Checked source-mapping rows | Status |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(
            f"| `{_markdown_escape(row['drug'])}` | {_markdown_escape(row['route'])} | `{_markdown_escape(row['spec_file'])}` | "
            f"{len([source for source in source_rows if source['drug'] == row['drug']])} | {row['fixture_value']} | {row['reference_value']} | {_markdown_escape(row['reference_status'])} |"
        )
    lines.extend(["", "## 値単位の確認一覧", ""])
    important = [
        row
        for row in parameter_rows
        if row["record_type"] in {"pk_parameter", "model_parameter", "target"}
    ]
    lines.extend([
        "| Drug | Record | Parameter | Fixture value | Reference value | Basis | Source | Review status |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ])
    for row in important:
        source = row["source_id"] or (row["source_url"][:60] if row["source_url"] else "-")
        review = row["source_review_status"] or row["reference_status"]
        lines.append(
            f"| `{_markdown_escape(row['drug'])}` | {_markdown_escape(row['record_type'])} | `{_markdown_escape(row['parameter'])}` | "
            f"{_markdown_escape(row['fixture_value'])} {_markdown_escape(row['fixture_unit'])} | {_markdown_escape(row['reference_value'])} {_markdown_escape(row['reference_unit'])} | "
            f"{_markdown_escape(row['value_basis']) or '-'} | {_markdown_escape(source)} | {_markdown_escape(review)} |"
        )
    lines.extend(["", "## ソースURL", "", "| Drug | Source key | URL |", "| --- | --- | --- |"])
    for row in source_rows:
        url = row["source_url"] or "(URLなし)"
        lines.append(f"| `{_markdown_escape(row['drug'])}` | `{_markdown_escape(row['source_key'])}` | {_markdown_escape(url)} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _timestamp() -> str | None:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        try:
            return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat().replace("+00:00", "Z")
        except ValueError:
            pass
    return None


def build_report(root: Path, out_dir: Path, selected_drugs: set[str] | None = None) -> dict[str, Any]:
    parameter_rows, source_rows, summary_rows = _build_rows(root, selected_drugs)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(out_dir / "PARAMETER_PROVENANCE.csv", parameter_rows, CSV_FIELDS)
    _write_csv(
        out_dir / "SOURCES.csv",
        source_rows,
        ["drug", "drug_id", "source_id", "source_key", "source_url", "source_record_index"],
    )
    _write_markdown(out_dir / "PARAMETER_PROVENANCE.md", parameter_rows, source_rows, summary_rows)
    status_counts: dict[str, int] = {}
    for row in parameter_rows:
        status = row["reference_status"] or "blank"
        status_counts[status] = status_counts.get(status, 0) + 1
    manifest = {
        "report_version": REPORT_VERSION,
        "generated_by": "tools/make_parameter_provenance_report.py",
        "generated_at_utc": _timestamp(),
        "scope": {
            "root": str(root),
            "drugs_dir": str(root / "drugs"),
            "selected_drugs": sorted(selected_drugs) if selected_drugs else "all",
            "canonical_inputs": ["drugs/*/pk.yml", "drugs/*/targets.yml", "drugs/*/spec_pk1_*.yml"],
        },
        "summary": {
            "drug_count": len(summary_rows),
            "source_count": len(source_rows),
            "parameter_row_count": len(parameter_rows),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "outputs": ["PARAMETER_PROVENANCE.csv", "SOURCES.csv", "PARAMETER_PROVENANCE.md", "PARAMETER_PROVENANCE.yml"],
        "interpretation": [
            "A source URL alone is not proof of an exact parameter-to-source match.",
            "Only rows with source_mapping_status=checked have a value-level source mapping; blank reference_value means no checked source value is claimed.",
            "Derived values retain their formula/basis and should not be read as directly reported values.",
            "fixture_policy rows are demo assumptions and require a separate source review before external use.",
        ],
    }
    (out_dir / "PARAMETER_PROVENANCE.yml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root (default: .).")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/parameter_provenance"), help="Output directory.")
    parser.add_argument("--drug", action="append", dest="drugs", help="Limit to one or more drug slugs (repeatable).")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    selected = set(args.drugs or []) or None
    out_dir = args.out_dir if args.out_dir.is_absolute() else root / args.out_dir
    manifest = build_report(root, out_dir, selected)
    print(yaml.safe_dump(manifest["summary"], allow_unicode=True, sort_keys=False).rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
