#!/usr/bin/env python3
"""Build the bilingual documentation site's data bundle from canonical drug YAML."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import yaml

try:
    from pharmacology_review import review_library
except ModuleNotFoundError:  # pragma: no cover - supports package imports in tests
    from tools.pharmacology_review import review_library


KNOWN_LIMITATION_CODES = {
    "fixture_derived_parameter",
    "bioavailability_fixture_derived",
    "one_compartment_structural_mismatch",
}
TRUSTED_PHARMACOLOGY_HOSTS = {
    "dailymed.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "www.accessdata.fda.gov",
    "accessdata.fda.gov",
}


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def clean(value: Any) -> Any:
    """Return JSON-safe values without changing scientific values."""
    if isinstance(value, dict):
        return {str(key): clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def first_spec(drug_dir: Path) -> tuple[Path | None, dict[str, Any]]:
    paths = sorted(drug_dir.glob("spec_pk1_*.yml"))
    if not paths:
        return None, {}
    return paths[0], load_yaml(paths[0])


def source_metadata(url: str | None) -> dict[str, Any]:
    """Classify a source URL without treating the URL itself as value evidence."""
    if not url:
        return {"kind": "unclassified", "identifier": None}
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if "pubmed.ncbi.nlm.nih.gov" in host:
        match = re.search(r"/([0-9]+)/?(?:$|[?#])", parsed.path)
        return {"kind": "PubMed", "identifier": match.group(1) if match else None}
    if "dailymed.nlm.nih.gov" in host:
        values = parse_qs(parsed.query).get("setid", [])
        match = re.search(r"setid=([^&]+)", url, flags=re.IGNORECASE)
        return {"kind": "DailyMed", "identifier": values[0] if values else (match.group(1) if match else None)}
    if "sciencedirect.com" in host:
        return {"kind": "ScienceDirect", "identifier": None}
    return {"kind": host or "unclassified", "identifier": None}


def is_trusted_pharmacology_source_url(url: str | None) -> bool:
    if not url:
        return False
    return urlparse(url).netloc.lower() in TRUSTED_PHARMACOLOGY_HOSTS


def parameter_label(source_field: str) -> str:
    if "bioavailability" in source_field.lower():
        return "bioavailability"
    labels = {
        "pk_parsed.clearance": "clearance",
        "pk_parsed.volume": "volume",
        "pk_parsed.half_life_h": "half_life",
        "pk_parsed.bioavailability_frac": "bioavailability",
        "pk_raw.clearance": "clearance",
        "pk_raw.volume_of_distribution": "volume",
        "pk_raw.half_life": "half_life",
        "pk_raw.bioavailability": "bioavailability",
    }
    return labels.get(source_field, source_field.rsplit(".", 1)[-1])


def build_evidence_claims(
    slug: str,
    pk: dict[str, Any],
    provenance: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build an honest evidence view from canonical data and review notes.

    A reviewer note is deliberately stored as a summary, never as an exact quote.
    Claims without a value-level source remain visible as unresolved work.
    """
    claims: list[dict[str, Any]] = []
    for key, item in provenance.items():
        if not isinstance(item, dict):
            continue
        source_field = str(item.get("source_field") or key)
        source_id = item.get("source_id")
        review_status = item.get("source_review_status") or "needs_source_review"
        exact_quote = item.get("exact_quote")
        source_locator = item.get("source_locator")
        fixture_derived = (item.get("conversion") or {}).get("method") == "derived_formula"
        value_verified = bool(
            source_id
            and review_status == "checked"
            and exact_quote
            and source_locator
            and not fixture_derived
        )
        missing = []
        if not source_id:
            missing.append("source_id")
        if not source_locator:
            missing.append("source_locator")
        if not exact_quote:
            missing.append("exact_quote")
        claims.append(
            {
                "claim_id": f"{slug}-{key}",
                "claim_type": "pk_parameter",
                "parameter": parameter_label(source_field),
                "source_field": source_field,
                "source_id": source_id,
                "raw_value": item.get("raw_value"),
                "normalized_value": item.get("normalized_value"),
                "normalized_unit": item.get("normalized_unit"),
                "evidence_status": "checked_summary" if review_status == "checked" else review_status,
                "evidence_level": "value_verified" if value_verified else ("summary_only" if review_status == "checked" else "unresolved"),
                "fixture_derived": fixture_derived,
                "evidence_summary": item.get("reviewer_note"),
                "exact_quote": exact_quote,
                "source_locator": source_locator,
                "missing": missing,
            }
        )

    represented_fields = {
        str(item.get("source_field"))
        for item in provenance.values()
        if isinstance(item, dict) and item.get("source_field")
    }
    raw_fields = {
        "pk_raw.clearance": "clearance",
        "pk_raw.volume_of_distribution": "volume",
        "pk_raw.half_life": "half_life",
        "pk_raw.bioavailability": "bioavailability",
    }
    raw = pk.get("pk_raw") or {}
    parsed = pk.get("pk_parsed") or {}
    route = str(pk.get("route_inferred") or "").lower()
    provenance_covers = {
        "clearance": "CL_abs_L_per_h_at_70kg" in provenance,
        "volume": "V_abs_L_at_70kg" in provenance,
        "half_life": "t_half_h" in provenance,
        "half_life_h": "t_half_h" in provenance,
        "bioavailability": "bioavailability_frac" in provenance,
        "bioavailability_frac": "bioavailability_frac" in provenance,
    }
    for source_field, parameter in raw_fields.items():
        raw_key = source_field.split(".", 1)[1]
        if raw_key == "bioavailability" and (route.startswith("iv") or str(raw.get(raw_key)).strip().upper().startswith("N/A")):
            continue
        if raw_key == "volume_of_distribution" and provenance_covers.get("volume", False):
            continue
        if raw_key == "bioavailability" and "bioavailability_frac" in parsed:
            continue
        if raw_key not in raw or provenance_covers.get(raw_key, False) or raw_key in provenance or source_field in represented_fields:
            continue
        claims.append(
            {
                "claim_id": f"{slug}-{raw_key}-unmapped",
                "claim_type": "pk_parameter",
                "parameter": parameter,
                "source_field": source_field,
                "source_id": None,
                "raw_value": raw.get(raw_key),
                "normalized_value": None,
                "normalized_unit": None,
                "evidence_status": "needs_source_mapping",
                "evidence_level": "unresolved",
                "evidence_summary": "Canonical raw value exists, but no value-level source mapping has been registered.",
                "exact_quote": None,
                "source_locator": None,
                "missing": ["source_id", "source_locator", "exact_quote"],
            }
        )

    parsed_fields = {
        "pk_parsed.clearance": "clearance",
        "pk_parsed.volume": "volume",
        "pk_parsed.half_life_h": "half_life",
        "pk_parsed.bioavailability_frac": "bioavailability",
    }
    for source_field, parameter in parsed_fields.items():
        parsed_key = source_field.split(".", 1)[1]
        value = parsed.get(parsed_key)
        if parsed_key == "bioavailability_frac" and route.startswith("iv"):
            continue
        if parsed_key == "bioavailability_frac" and str(pk.get("pk_parsed", {}).get("clearance_basis") or "").lower() == "apparent" and parsed.get(parsed_key) == 1.0:
            claims.append(
                {
                    "claim_id": f"{slug}-{parsed_key}-fixture-assumption",
                    "claim_type": "fixture_assumption",
                    "parameter": "bioavailability",
                    "source_field": source_field,
                    "source_id": None,
                    "raw_value": value,
                    "normalized_value": parsed.get(parsed_key),
                    "normalized_unit": "fraction",
                    "evidence_status": "fixture_check",
                    "evidence_level": "fixture_check",
                    "fixture_derived": True,
                    "evidence_summary": "F=1 is a model convention for an apparent CL/F, V/F fixture; it is not an observed absolute bioavailability claim.",
                    "exact_quote": None,
                    "source_locator": None,
                    "missing": [],
                }
            )
            continue
        if parsed_key == "bioavailability_frac" and parsed_key in parsed and str(parsed.get("clearance_basis") or "apparent").lower() != "systemic":
            claims.append(
                {
                    "claim_id": f"{slug}-{parsed_key}-fixture-context",
                    "claim_type": "fixture_assumption",
                    "parameter": "bioavailability",
                    "source_field": source_field,
                    "source_id": None,
                    "raw_value": value,
                    "normalized_value": value,
                    "normalized_unit": "fraction",
                    "evidence_status": "fixture_check",
                    "evidence_level": "fixture_check",
                    "fixture_derived": True,
                    "evidence_summary": "The parsed F value is contextual only because CL/V are apparent CL/F and V/F; the simulation convention uses F1=1 and does not claim an observed absolute bioavailability.",
                    "exact_quote": None,
                    "source_locator": None,
                    "missing": [],
                }
            )
            continue
        if parsed_key not in parsed or provenance_covers.get(parsed_key, False) or parsed_key in provenance or source_field in represented_fields:
            continue
        normalized_value = value.get("value") if isinstance(value, dict) else value
        normalized_unit = value.get("unit") if isinstance(value, dict) else None
        claims.append(
            {
                "claim_id": f"{slug}-{parsed_key}-unmapped",
                "claim_type": "pk_parameter",
                "parameter": parameter,
                "source_field": source_field,
                "source_id": None,
                "raw_value": value,
                "normalized_value": normalized_value,
                "normalized_unit": normalized_unit,
                "evidence_status": "needs_source_mapping",
                "evidence_level": "unresolved",
                "fixture_derived": False,
                "evidence_summary": "Parsed parameter exists, but no value-level source mapping has been registered.",
                "exact_quote": None,
                "source_locator": None,
                "missing": ["source_id", "source_locator", "exact_quote"],
            }
        )
    return claims


def load_pubmed_metadata(root: Path) -> dict[str, dict[str, Any]]:
    path = root / "site" / "app" / "pubmed.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    records = value.get("records") if isinstance(value, dict) else {}
    return records if isinstance(records, dict) else {}


def load_pharmacology_data(root: Path) -> dict[str, Any]:
    path = root / "docs" / "pharmacology.yml"
    if not path.exists():
        return {}
    value = load_yaml(path)
    if not isinstance(value, dict):
        return {"defaults": {}, "drugs": {}}
    drugs = value.get("drugs")
    defaults = value.get("claim_defaults")
    return {
        "defaults": defaults if isinstance(defaults, dict) else {},
        "drugs": drugs if isinstance(drugs, dict) else {},
    }


def build_pharmacology(
    slug: str,
    raw_entry: dict[str, Any] | None,
    sources: list[dict[str, Any]],
    defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a separate, fail-closed pharmacology evidence layer.

    Pharmacology claims are intentionally not inferred from PK prose. A claim
    only becomes reviewed after a human records both a short exact quote and a
    precise source locator. The current repository registers source candidates
    for all drugs so the site can show what is pending without presenting a URL
    or a general summary as confirmed evidence.
    """
    if not isinstance(raw_entry, dict):
        return {"status": "not_curated", "review_stage": "not_started", "claim_count": 0, "claims": []}

    defaults = defaults if isinstance(defaults, dict) else {}

    source_by_id = {
        str(source.get("id")): source
        for source in sources
        if source.get("id")
    }
    claims: list[dict[str, Any]] = []
    for raw_claim in raw_entry.get("claims") or []:
        if not isinstance(raw_claim, dict):
            continue
        source_id = raw_claim.get("source_id")
        exact_quote = raw_claim.get("exact_quote")
        source_locator = raw_claim.get("source_locator")
        source = source_by_id.get(str(source_id)) if source_id else None
        direct_source = raw_claim.get("source")
        if (
            isinstance(direct_source, dict)
            and direct_source.get("source_role") == "pharmacology"
            and is_trusted_pharmacology_source_url(direct_source.get("url"))
        ):
            direct_id = direct_source.get("id") or source_id or f"pharmacology_{len(claims) + 1}"
            source = {
                "id": direct_id,
                "display_id": direct_source.get("display_id") or direct_id,
                "url": direct_source.get("url"),
                "index": direct_source.get("index", 0),
                **source_metadata(direct_source.get("url")),
            }
        resolved_source_id = source_id or (source.get("id") if source else None)
        claim_status = raw_claim.get("claim_status") or raw_entry.get("claim_status") or defaults.get("claim_status") or "unconfirmed"
        source_fit_status = raw_claim.get("source_fit_status") or raw_entry.get("source_fit_status") or defaults.get("source_fit_status") or "unreviewed"
        context = {
            field: raw_claim.get(field)
            or raw_entry.get(field)
            or defaults.get(field)
            or "unconfirmed"
            for field in (
                "jurisdiction",
                "population_context",
                "route_or_formulation",
                "study_context",
            )
        }
        requested_level = raw_claim.get("evidence_level") or "source_candidate"
        review_ready = (
            requested_level == "reviewed"
            and raw_entry.get("status") == "curated"
            and claim_status == "reviewed"
            and source_fit_status == "reviewed"
            and bool(source and is_trusted_pharmacology_source_url(source.get("url")))
            and (raw_claim.get("evidence_status") or "source_candidate") == "reviewed"
            and bool(exact_quote)
            and bool(source_locator)
            and all(value != "unconfirmed" for value in context.values())
        )
        missing = list(raw_claim.get("missing") or [])
        if not source and "source_id" not in missing:
            missing.append("source_id")
        if not exact_quote and "exact_quote" not in missing:
            missing.append("exact_quote")
        if not source_locator and "source_locator" not in missing:
            missing.append("source_locator")
        if source_fit_status != "reviewed" and "source_fit_status" not in missing:
            missing.append("source_fit_status")
        if claim_status != "reviewed" and "claim_status" not in missing:
            missing.append("claim_status")
        for field, value in context.items():
            if value == "unconfirmed" and field not in missing:
                missing.append(field)
        evidence_level = "reviewed" if review_ready else "source_candidate"
        evidence_status = "reviewed" if review_ready else "source_candidate"
        claims.append(
            {
                "claim_id": raw_claim.get("claim_id") or f"{slug}-pharmacology-{len(claims) + 1}",
                "claim_type": raw_claim.get("claim_type") or "mechanism",
                "statement": raw_claim.get("statement") or {},
                "source_id": resolved_source_id,
                "source_key": f"{slug}:{resolved_source_id}" if resolved_source_id else None,
                "source": source,
                "claim_status": claim_status,
                "source_fit_status": source_fit_status,
                **context,
                "evidence_status": evidence_status,
                "evidence_level": evidence_level,
                "evidence_summary": raw_claim.get("evidence_summary") or {},
                "exact_quote": exact_quote,
                "source_locator": source_locator,
                "missing": missing,
            }
        )
    all_reviewed = bool(claims) and all(item["evidence_level"] == "reviewed" for item in claims)
    status = raw_entry.get("status") or ("partial" if claims else "not_curated")
    if status == "curated" and not all_reviewed:
        status = "partial"
    return {
        "status": "curated" if status == "curated" and all_reviewed else status,
        "review_stage": "reviewed" if all_reviewed else (raw_entry.get("review_stage") or "source_mapped"),
        "claim_count": len(claims),
        "source_candidate_count": sum(item["evidence_level"] == "source_candidate" for item in claims),
        "reviewed_count": sum(item["evidence_level"] == "reviewed" for item in claims),
        "exact_quote_count": sum(bool(item.get("exact_quote")) for item in claims),
        "source_locator_count": sum(bool(item.get("source_locator")) for item in claims),
        "claims": claims,
    }


def build_drug(
    pk_path: Path,
    strict_review: dict[str, Any] | None = None,
    pharmacology_data: dict[str, Any] | None = None,
    pharmacology_defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    drug_dir = pk_path.parent
    pk = load_yaml(pk_path)
    targets_path = drug_dir / "targets.yml"
    targets = load_yaml(targets_path) if targets_path.exists() else {}
    spec_path, spec = first_spec(drug_dir)
    pubmed_metadata = load_pubmed_metadata(pk_path.parents[2])
    sources: list[dict[str, Any]] = []
    for index, source in enumerate(pk.get("sources") or [], start=1):
        if not isinstance(source, dict):
            continue
        source_id = source.get("id")
        metadata = source_metadata(source.get("url"))
        source_record = {
                "id": source_id,
                "display_id": source_id or f"source_{index}",
                "url": source.get("url"),
                "index": index,
                **metadata,
            }
        if metadata["kind"] == "PubMed" and metadata["identifier"] in pubmed_metadata:
            source_record["bibliography"] = pubmed_metadata[metadata["identifier"]]
        sources.append(source_record)

    parsed = pk.get("pk_parsed") or {}
    derived = pk.get("derived") or {}
    provenance = pk.get("value_provenance") or {}
    target_map = targets.get("targets") or {}
    model = spec.get("model") or {}
    route = pk.get("route_inferred") or spec.get("regimen", {}).get("route")
    review_states = [
        item.get("source_review_status")
        for item in provenance.values()
        if isinstance(item, dict)
    ]
    needs_review = sum(state not in {"checked", "not_applicable"} for state in review_states)
    half_life_target = target_map.get("t_half") if isinstance(target_map, dict) else {}
    structural_mismatch = (
        half_life_target.get("structural_mismatch")
        if isinstance(half_life_target, dict)
        else {}
    )
    evidence_claims = build_evidence_claims(drug_dir.name, pk, provenance)
    auc_target = target_map.get("auc") if isinstance(target_map, dict) else None
    if isinstance(auc_target, dict):
        target_source_id = auc_target.get("source_id")
        target_checked = bool(target_source_id and auc_target.get("independent_literature_target") is True)
        fixture_check = auc_target.get("independent_literature_target") is not True
        evidence_claims.append(
            {
                "claim_id": f"{drug_dir.name}-targets-auc",
                "claim_type": "auc_target",
                "parameter": "AUC0-inf target",
                "source_field": "targets.auc",
                "source_id": target_source_id,
                "raw_value": auc_target.get("raw_value", auc_target.get("value")),
                "normalized_value": auc_target.get("value"),
                "normalized_unit": auc_target.get("unit"),
                "evidence_status": "checked_summary" if target_checked else ("fixture_check" if fixture_check else "needs_source_mapping"),
                "evidence_level": "summary_only" if target_checked else ("fixture_check" if fixture_check else "unresolved"),
                "fixture_derived": fixture_check,
                "evidence_summary": (
                    "Independent literature AUC target with declared raw-unit conversion."
                    if target_checked
                    else "AUC target is derived or lacks a value-level source mapping."
                ),
                "exact_quote": None,
                "source_locator": None,
                "missing": [] if fixture_check else [
                    field
                    for field, value in (
                        ("source_id", target_source_id),
                        ("source_locator", None),
                        ("exact_quote", None),
                    )
                    if value in (None, "")
                ],
            }
        )
    evidence_summary = {
        "claim_count": len(evidence_claims),
        "checked_summary_count": sum(item["evidence_level"] == "summary_only" for item in evidence_claims),
        "fixture_check_count": sum(item["evidence_level"] == "fixture_check" for item in evidence_claims),
        "unresolved_count": sum(item["evidence_level"] == "unresolved" for item in evidence_claims),
        "value_verified_count": sum(item["evidence_level"] == "value_verified" for item in evidence_claims),
        "exact_quote_count": sum(bool(item.get("exact_quote")) for item in evidence_claims),
        "source_locator_count": sum(bool(item.get("source_locator")) for item in evidence_claims),
    }
    # A fixture-derived claim can be validly classified as non-value-level
    # evidence, but missing quote/locator metadata is still a visible context
    # note. Do not let the fixture classification hide the repository's open
    # citation-readiness gap.
    evidence_summary["citation_gap_count"] = sum(
        item["evidence_level"] == "summary_only"
        and (not item.get("exact_quote") or not item.get("source_locator"))
        for item in evidence_claims
    ) + evidence_summary["unresolved_count"]

    strict_review = strict_review or {}
    strict_issues = strict_review.get("issues") or []
    open_review_count = sum(
        issue.get("severity") in {"BLOCKER", "ERROR"}
        or (issue.get("severity") == "REVIEW" and issue.get("code") not in KNOWN_LIMITATION_CODES)
        for issue in strict_issues
        if isinstance(issue, dict)
    )
    known_limitation_count = sum(
        issue.get("severity") == "REVIEW" and issue.get("code") in KNOWN_LIMITATION_CODES
        for issue in strict_issues
        if isinstance(issue, dict)
    )

    pharmacology = build_pharmacology(drug_dir.name, pharmacology_data, sources, pharmacology_defaults)
    return clean(
        {
            "slug": drug_dir.name,
            "simulation_validity": pk.get("simulation_validity") or {},
            "id": pk.get("id"),
            "name": pk.get("name") or drug_dir.name,
            "route": route,
            "sources": sources,
            "raw": pk.get("pk_raw") or {},
            "parsed": parsed,
            "derived": derived,
            "provenance": provenance,
            "targets": targets,
            "spec": {
                "file": spec_path.name if spec_path else None,
                "study": spec.get("study") or {},
                "population": spec.get("population") or {},
                "regimen": spec.get("regimen") or {},
                "sampling": spec.get("sampling") or {},
                "model": model,
                "iiv": spec.get("iiv") or {},
                "residual": spec.get("residual") or {},
            },
            "review": {
                "provenance_field_count": len(provenance),
                "needs_review_count": needs_review,
                "evidence_claim_count": evidence_summary["claim_count"],
                "evidence_unresolved_count": evidence_summary["unresolved_count"],
                "evidence_citation_gap_count": evidence_summary["citation_gap_count"],
                "strict_status": strict_review.get("status"),
                "open_review_count": open_review_count,
                "known_limitation_count": known_limitation_count,
                "structural_mismatch_acknowledged": bool(
                    isinstance(structural_mismatch, dict)
                    and structural_mismatch.get("acknowledged") is True
                ),
            },
            "pharmacology": pharmacology,
            "evidence": {
                "schema_version": "0.1",
                "summary": evidence_summary,
                "claims": evidence_claims,
            },
        }
    )


def build_bundle(root: Path) -> dict[str, Any]:
    try:
        from check_parameter_contract import check_source_contract
    except ModuleNotFoundError:
        from tools.check_parameter_contract import check_source_contract
    issues = check_source_contract(root)
    if issues:
        raise ValueError("Parameter contract failed:\n" + "\n".join(issues))
    strict_report = review_library(root)
    strict_by_slug = {item["slug"]: item for item in strict_report["drugs"]}
    pharmacology_payload = load_pharmacology_data(root)
    pharmacology_data = pharmacology_payload.get("drugs", {})
    pharmacology_defaults = pharmacology_payload.get("defaults", {})
    drugs = [
        build_drug(
            path,
            strict_by_slug.get(path.parent.name),
            pharmacology_data.get(path.parent.name),
            pharmacology_defaults,
        )
        for path in sorted((root / "drugs").glob("*/pk.yml"))
    ]
    return {
        "schema_version": "1.0",
        "source": "drugs/*/pk.yml + targets.yml + spec_pk1_*.yml + docs/pharmacology.yml",
        "drug_count": len(drugs),
        "drugs": drugs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path("site/app/drugs.json"))
    parser.add_argument("--check", action="store_true", help="Compare the existing bundle without writing it.")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.out if args.out.is_absolute() else root / args.out
    bundle = build_bundle(root)
    if args.check:
        if not output.is_file() or json.loads(output.read_text(encoding="utf-8")) != bundle:
            print(f"Atlas data drift: {output}; regenerate from canonical inputs")
            return 1
        print(f"Atlas data check: OK ({len(bundle['drugs'])} drugs)")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {output} ({len(bundle['drugs'])} drugs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
