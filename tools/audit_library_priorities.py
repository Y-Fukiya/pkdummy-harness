#!/usr/bin/env python3
"""Read-only internal-first audit for PK fixture library priorities.

This tool ranks drug x spec rows by fixture risk. It never updates pk.yml,
targets.yml, or spec files, and it never queries live external services.
Optional OSP/PK-DB columns are populated only from local snapshot CSVs.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml


ATTAINABILITY_WARN_REL = 0.25

FIELDNAMES = [
    "drug",
    "slug",
    "route",
    "spec_file",
    "has_pk_yml",
    "sources_n",
    "has_raw_text",
    "has_parsed",
    "has_derived",
    "attainability_status",
    "t_half_cl_v_rel_error",
    "target_independence_status",
    "target_circularity_notes",
    "known_stress_fixture",
    "unit_or_basis_risk",
    "overall_internal_priority",
    "priority_reason",
    "osp_model_match",
    "osp_evaluation_report",
    "pkdb_exact_hit_count",
    "pkdb_role",
    "recommended_next_action",
]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _norm_text(value: Any) -> str:
    return str(value or "").strip()


def _norm_key(value: Any) -> str:
    text = _norm_text(value).lower()
    text = re.sub(r"\([^)]*\)", "", text)
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _slug_key(value: Any) -> str:
    text = _norm_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _rel_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


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


def _bool_text(value: bool) -> str:
    return "yes" if value else "no"


def _notes_text(*blocks: Any) -> str:
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, list):
            parts.extend(str(item) for item in block)
        elif block:
            parts.append(str(block))
    return "\n".join(parts).lower()


def _route_from_spec(spec: dict[str, Any], pk: dict[str, Any]) -> str:
    route = (((spec.get("regimen") or {}).get("route")) or pk.get("route_inferred") or "")
    route_norm = str(route).strip().lower()
    if route_norm in {"oral", "po", "p.o.", "per os"}:
        return "po"
    if route_norm in {"iv", "i.v.", "intravenous", "iv_bolus", "iv_infusion"}:
        return "iv"
    if route_norm in {"sc", "subcutaneous"}:
        return "sc"
    if route_norm in {"im", "intramuscular"}:
        return "im"
    return route_norm or "unknown"


def _has_raw_text(pk_raw: dict[str, Any]) -> bool:
    if not pk_raw:
        return False
    return any(_norm_text(value) for value in pk_raw.values())


def _has_parsed(parsed: dict[str, Any]) -> bool:
    return (
        _to_float(parsed.get("half_life_h")) is not None
        and isinstance(parsed.get("clearance"), dict)
        and isinstance(parsed.get("volume"), dict)
    )


def _has_derived(derived: dict[str, Any]) -> bool:
    return (
        _to_float(derived.get("CL_abs_L_per_h_at_70kg")) is not None
        and _to_float(derived.get("V_abs_L_at_70kg")) is not None
    )


def _attainability(pk: dict[str, Any]) -> tuple[str, str]:
    parsed = pk.get("pk_parsed") or {}
    derived = pk.get("derived") or {}
    t_half = _to_float(parsed.get("half_life_h"))
    cl_abs = _to_float(derived.get("CL_abs_L_per_h_at_70kg"))
    v_abs = _to_float(derived.get("V_abs_L_at_70kg"))
    if not t_half or not cl_abs or not v_abs:
        return "NA", ""
    implied = math.log(2.0) * v_abs / cl_abs
    rel_error = abs(implied - t_half) / abs(t_half)
    status = "WARN" if rel_error > ATTAINABILITY_WARN_REL else "OK"
    return status, f"{rel_error:.6g}"


def _target_independence(targets: dict[str, Any], notes_text: str) -> tuple[str, str]:
    target_map = targets.get("targets") or {}
    circular: list[str] = []
    if "auc" in target_map and ("dose/cl" in notes_text or "computed as dose/cl" in notes_text):
        circular.append("auc_from_dose_over_cl")
    if "t_half" in target_map and "not used to recalibrate" in notes_text:
        circular.append("t_half_retained_as_check")
    if circular:
        return "HAS_GENERATIVE_DERIVED_TARGETS", ";".join(circular)
    if target_map:
        return "NO_EXPLICIT_CIRCULARITY_NOTE", ""
    return "NO_TARGETS", ""


def _unit_or_basis_risks(pk: dict[str, Any], spec: dict[str, Any], route: str) -> str:
    risks: list[str] = []
    raw = pk.get("pk_raw") or {}
    parsed = pk.get("pk_parsed") or {}
    derived = pk.get("derived") or {}
    notes = _notes_text(derived.get("notes"), (spec.get("model") or {}).get("notes"))
    raw_text = " ".join(str(value).lower() for value in raw.values())

    if route == "po":
        if _to_float(parsed.get("bioavailability_frac")) is None:
            risks.append("oral_missing_F")
        if "cl/f" in raw_text or "v/f" in raw_text:
            risks.append("apparent_CL_or_V_basis")
    if "1.73" in raw_text:
        risks.append("BSA_normalized_source")
    if "/kg" in raw_text or "per kg" in raw_text:
        risks.append("weight_normalized_source")
    if "derived_from" in str(parsed).lower() or "assuming ke" in str(parsed).lower() or "derived from" in notes:
        risks.append("parameter_derived_from_identity")
    return ";".join(dict.fromkeys(risks))


def _known_stress(spec: dict[str, Any], targets: dict[str, Any]) -> bool:
    notes = _notes_text((spec.get("model") or {}).get("notes"), targets.get("notes"))
    return "stress-test" in notes or "stress test" in notes or "known 1-compartment attainability issue" in notes


def _load_snapshot(path: Path | None, *, name_columns: tuple[str, ...]) -> dict[str, list[dict[str, str]]]:
    if path is None or not path.exists():
        return {}
    out: dict[str, list[dict[str, str]]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            keys = {_slug_key(row.get("slug"))}
            for column in name_columns:
                keys.add(_norm_key(row.get(column)))
                keys.add(_slug_key(row.get(column)))
            for key in {key for key in keys if key}:
                out.setdefault(key, []).append(row)
    return out


def _snapshot_matches(index: dict[str, list[dict[str, str]]], *, slug: str, drug: str) -> list[dict[str, str]]:
    keys = {_slug_key(slug), _norm_key(slug), _slug_key(drug), _norm_key(drug)}
    matches: list[dict[str, str]] = []
    seen: set[int] = set()
    for key in keys:
        for row in index.get(key, []):
            marker = id(row)
            if marker not in seen:
                seen.add(marker)
                matches.append(row)
    return matches


def _has_osp_report(rows: list[dict[str, str]]) -> bool:
    report_columns = ("evaluation_report", "evaluation_report_url", "report", "report_url", "qualification_report")
    for row in rows:
        if any(_norm_text(row.get(column)) for column in report_columns):
            return True
    return False


def _priority(
    *,
    known_stress: bool,
    attainability_status: str,
    has_derived: bool,
    has_parsed: bool,
    unit_or_basis_risk: str,
    sources_n: int,
    has_raw_text: bool,
    osp_model_match: bool,
    pkdb_exact_hit_count: int,
) -> tuple[str, str, str]:
    if known_stress:
        return (
            "STRESS_FIXTURE",
            "Known stress fixture; do not auto-fix solely because audit risk is high.",
            "Keep as boundary/stress case; review only if intended-use label is wrong.",
        )
    if attainability_status == "WARN" or not has_derived:
        return (
            "P0_CORRECTNESS",
            "1-compartment identity or missing derived CL/V may make generated profiles structurally incorrect.",
            "Review independent parameter pair and spec/targets consistency before provenance enrichment.",
        )
    if not has_parsed or unit_or_basis_risk:
        return (
            "P1_STRUCTURAL",
            "Route, unit, CL/F vs CL, or derived-identity basis needs structural review.",
            "Check units/basis; use OSP structural prior if available; do not update pk.yml automatically.",
        )
    if sources_n == 0 or not has_raw_text:
        return (
            "P2_PROVENANCE",
            "Current fixture is internally usable but weakly documented.",
            "Add source/raw/parsed/derived evidence through manual review if this drug is important.",
        )
    if osp_model_match or pkdb_exact_hit_count > 0:
        return (
            "P3_REFERENCE",
            "Internal fixture is acceptable; external references may improve explanation or sampling templates.",
            "Use external references only for notes, structure review, or sampling/profile-shape guidance.",
        )
    return ("OK", "No major internal audit concern.", "No action required.")


def audit_library(
    root: Path,
    *,
    osp_snapshot: Path | None = None,
    pkdb_snapshot: Path | None = None,
) -> list[dict[str, str]]:
    drugs_dir = root / "drugs"
    osp_index = _load_snapshot(osp_snapshot, name_columns=("drug", "name", "substance", "model"))
    pkdb_index = _load_snapshot(pkdb_snapshot, name_columns=("drug", "name", "substance", "substance_name"))

    rows: list[dict[str, str]] = []
    for drug_dir in sorted(path for path in drugs_dir.iterdir() if path.is_dir()):
        slug = drug_dir.name
        pk_path = drug_dir / "pk.yml"
        targets_path = drug_dir / "targets.yml"
        if not pk_path.exists():
            continue
        pk = load_yaml(pk_path)
        targets = load_yaml(targets_path) if targets_path.exists() else {}
        spec_paths = sorted(drug_dir.glob("spec_pk1_*.yml"))
        if not spec_paths:
            spec_paths = [Path("")]
        drug_name = _norm_text(pk.get("name")) or slug
        parsed = pk.get("pk_parsed") or {}
        derived = pk.get("derived") or {}
        raw = pk.get("pk_raw") or {}
        sources_n = len(pk.get("sources") or [])
        has_raw_text = _has_raw_text(raw)
        has_parsed = _has_parsed(parsed)
        has_derived = _has_derived(derived)
        attainability_status, rel_error = _attainability(pk)
        target_status, circularity_notes = _target_independence(targets, _notes_text(targets.get("notes")))

        osp_matches = _snapshot_matches(osp_index, slug=slug, drug=drug_name)
        pkdb_matches = _snapshot_matches(pkdb_index, slug=slug, drug=drug_name)

        for spec_path in spec_paths:
            spec = load_yaml(spec_path) if spec_path and spec_path.exists() else {}
            route = _route_from_spec(spec, pk)
            stress = _known_stress(spec, targets)
            unit_risk = _unit_or_basis_risks(pk, spec, route)
            priority, reason, action = _priority(
                known_stress=stress,
                attainability_status=attainability_status,
                has_derived=has_derived,
                has_parsed=has_parsed,
                unit_or_basis_risk=unit_risk,
                sources_n=sources_n,
                has_raw_text=has_raw_text,
                osp_model_match=bool(osp_matches),
                pkdb_exact_hit_count=len(pkdb_matches),
            )
            rows.append(
                {
                    "drug": drug_name,
                    "slug": slug,
                    "route": route,
                    "spec_file": _rel_path(spec_path, root) if spec_path else "",
                    "has_pk_yml": "yes",
                    "sources_n": str(sources_n),
                    "has_raw_text": _bool_text(has_raw_text),
                    "has_parsed": _bool_text(has_parsed),
                    "has_derived": _bool_text(has_derived),
                    "attainability_status": attainability_status,
                    "t_half_cl_v_rel_error": rel_error,
                    "target_independence_status": target_status,
                    "target_circularity_notes": circularity_notes,
                    "known_stress_fixture": _bool_text(stress),
                    "unit_or_basis_risk": unit_risk,
                    "overall_internal_priority": priority,
                    "priority_reason": reason,
                    "osp_model_match": _bool_text(bool(osp_matches)),
                    "osp_evaluation_report": _bool_text(_has_osp_report(osp_matches)),
                    "pkdb_exact_hit_count": str(len(pkdb_matches)),
                    "pkdb_role": "sampling/profile reference only" if pkdb_matches else "none",
                    "recommended_next_action": action,
                }
            )
    return rows


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(path: Path, rows: list[dict[str, str]], *, root: Path, osp_snapshot: Path | None, pkdb_snapshot: Path | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(row["overall_internal_priority"] for row in rows)
    lines = [
        "# PK Fixture Library Priority Audit",
        "",
        "This read-only audit ranks drug x route/spec rows by internal fixture risk.",
        "It does not update `pk.yml`, `targets.yml`, or spec files and does not query the network.",
        "",
        "## Inputs",
        "",
        f"- repo root: `{root}`",
        f"- OSP snapshot: `{osp_snapshot}`" if osp_snapshot else "- OSP snapshot: not provided",
        f"- PK-DB snapshot: `{pkdb_snapshot}`" if pkdb_snapshot else "- PK-DB snapshot: not provided",
        "",
        "## Priority Tiers",
        "",
        "| Tier | Meaning |",
        "| --- | --- |",
        "| `P0_CORRECTNESS` | 1-compartment identity or missing derived CL/V may make generated profiles structurally incorrect. |",
        "| `P1_STRUCTURAL` | Route, unit, CL/F vs CL, or derived-identity basis needs structural review. |",
        "| `P2_PROVENANCE` | Internally usable fixture, but source/raw/parsed/derived support is weak. |",
        "| `P3_REFERENCE` | Internal fixture is acceptable; external references may improve notes or sampling/profile templates. |",
        "| `STRESS_FIXTURE` | Intentionally retained boundary case; not an automatic fix target. |",
        "| `OK` | No major internal audit concern. |",
        "",
        "## Summary",
        "",
        "| Priority | Rows |",
        "| --- | ---: |",
    ]
    for key in ["P0_CORRECTNESS", "P1_STRUCTURAL", "P2_PROVENANCE", "P3_REFERENCE", "STRESS_FIXTURE", "OK"]:
        lines.append(f"| `{key}` | {counts.get(key, 0)} |")
    lines.extend(["", "## Highest Priority Rows", ""])
    interesting = [row for row in rows if row["overall_internal_priority"] not in {"OK", "P3_REFERENCE"}]
    if interesting:
        lines.append("| Priority | Drug | Route | Attainability | Rel error | Unit/basis risk | Recommended action |")
        lines.append("| --- | --- | --- | --- | ---: | --- | --- |")
        order = {"P0_CORRECTNESS": 0, "P1_STRUCTURAL": 1, "P2_PROVENANCE": 2, "STRESS_FIXTURE": 3}
        for row in sorted(interesting, key=lambda r: (order.get(r["overall_internal_priority"], 9), r["slug"], r["route"])):
            lines.append(
                "| `{priority}` | {drug} | {route} | {attain} | {rel} | {risk} | {action} |".format(
                    priority=row["overall_internal_priority"],
                    drug=row["drug"],
                    route=row["route"],
                    attain=row["attainability_status"],
                    rel=row["t_half_cl_v_rel_error"] or "",
                    risk=row["unit_or_basis_risk"] or "",
                    action=row["recommended_next_action"],
                )
            )
    else:
        lines.append("No P0/P1/P2/STRESS rows found.")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only internal-first priority audit for the PK fixture library.")
    parser.add_argument("root", nargs="?", default=".", help="Repository root.")
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/library_audit"))
    parser.add_argument("--osp-snapshot", type=Path, default=Path("external_sources/snapshots/osp_model_index.csv"))
    parser.add_argument("--pkdb-snapshot", type=Path, default=Path("external_sources/snapshots/pkdb_substance_index.csv"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    root = Path(args.root).resolve()
    osp_snapshot = args.osp_snapshot if args.osp_snapshot and args.osp_snapshot.exists() else None
    pkdb_snapshot = args.pkdb_snapshot if args.pkdb_snapshot and args.pkdb_snapshot.exists() else None
    rows = audit_library(root, osp_snapshot=osp_snapshot, pkdb_snapshot=pkdb_snapshot)
    out_dir = args.out_dir
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    csv_path = out_dir / "library_priority_audit.csv"
    md_path = out_dir / "library_priority_audit.md"
    _write_csv(csv_path, rows)
    _write_markdown(md_path, rows, root=root, osp_snapshot=osp_snapshot, pkdb_snapshot=pkdb_snapshot)
    print("Library priority audit: OK")
    print(f"rows: {len(rows)}")
    print(f"csv: {csv_path}")
    print(f"markdown: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
