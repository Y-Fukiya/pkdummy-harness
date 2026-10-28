#!/usr/bin/env python3
"""Run a fail-closed pharmacology/PK review of the drug fixture library.

This is an automated reviewer, not a claim of human clinical sign-off.  It
checks parameterization logic, route mapping, target circularity, unit/BSA
metadata, and value-level provenance.  Missing primary evidence is reported as
an open blocker; it is never converted into a guessed value.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
from typing import Any

import yaml


REQUIRED_FIELDS = (
    "CL_abs_L_per_h_at_70kg",
    "V_abs_L_at_70kg",
    "t_half_h",
)
PRIMARY_HOSTS = (
    "dailymed.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
)
SYSTEMIC_ORAL_BASIS = "systemic"
_BSA_UNIT = re.compile(r"(?:/|per\s+)(?:1\.?\s*73|1\.73)\s*m", re.IGNORECASE)
_HALF_LIFE_RANGE = re.compile(
    r"(?P<low>\d+(?:\.\d+)?)\s*(?:to|-)\s*(?P<high>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def normalize_route(value: Any) -> str:
    route = str(value or "").strip().lower()
    if route in {"po", "oral", "p.o.", "per os"} or route.startswith("oral"):
        return "po"
    if route in {"sl", "s.l.", "sublingual"} or route.startswith("subling"):
        return "sl"
    if route in {"iv", "i.v.", "intravenous", "iv_bolus", "iv_infusion"} or route.startswith("iv"):
        return "iv"
    return route


def _float(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def source_kind(url: str) -> str:
    lowered = url.lower()
    if any(host in lowered for host in PRIMARY_HOSTS):
        return "primary_or_regulatory"
    if "fda.gov" in lowered or "ema.europa.eu" in lowered:
        return "regulatory"
    if any(host in lowered for host in ("wikipedia.org", "drugbank", "pubchem", "researchgate")):
        return "secondary_or_aggregator"
    return "unclassified"


def _issue(code: str, severity: str, message: str, *, field: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"code": code, "severity": severity, "message": message}
    if field:
        result["field"] = field
    return result


def _reported_half_life_range_h(raw_value: Any) -> tuple[float, float] | None:
    """Read the first explicit raw half-life range without guessing contexts."""
    text = str(raw_value or "")
    match = _HALF_LIFE_RANGE.search(text)
    if not match:
        return None
    context = text[match.start():match.end() + 16].lower()
    factor = 1.0
    if "minute" in context or re.search(r"\bmin\b", context):
        factor = 1.0 / 60.0
    elif "day" in context:
        factor = 24.0
    return float(match.group("low")) * factor, float(match.group("high")) * factor


def review_drug(root: Path, drug_dir: Path) -> dict[str, Any]:
    slug = drug_dir.name
    pk = load_yaml(drug_dir / "pk.yml")
    targets = load_yaml(drug_dir / "targets.yml")
    spec_paths = sorted(drug_dir.glob("spec_pk1_*.yml"))
    spec = load_yaml(spec_paths[0]) if len(spec_paths) == 1 else {}
    parsed = pk.get("pk_parsed") or {}
    derived = pk.get("derived") or {}
    theta = ((spec.get("model") or {}).get("theta")) or {}
    issues: list[dict[str, Any]] = []

    reported_range = _reported_half_life_range_h((pk.get("pk_raw") or {}).get("half_life"))
    parsed_range = parsed.get("half_life_h_range")
    if reported_range is not None:
        if not isinstance(parsed_range, list) or len(parsed_range) != 2:
            issues.append(_issue(
                "half_life_range_missing",
                "BLOCKER",
                "raw half-life contains an explicit range but pk_parsed.half_life_h_range is missing",
                field="pk_parsed.half_life_h_range",
            ))
        else:
            low, high = (_float(parsed_range[0]), _float(parsed_range[1]))
            if (
                low is None
                or high is None
                or not math.isclose(low, reported_range[0], rel_tol=0, abs_tol=1e-9)
                or not math.isclose(high, reported_range[1], rel_tol=0, abs_tol=1e-9)
            ):
                issues.append(_issue(
                    "half_life_range_context_mismatch",
                    "BLOCKER",
                    f"parsed half-life range={parsed_range!r} does not match first raw reported range={reported_range!r} h",
                    field="pk_parsed.half_life_h_range",
                ))

    route = normalize_route(pk.get("route_inferred"))
    spec_route = normalize_route((spec.get("regimen") or {}).get("route"))
    if route != spec_route:
        issues.append(_issue("route_model_mismatch", "ERROR", f"pk route={route!r} but spec route={spec_route!r}"))

    if route == "sl":
        raw_route = str(parsed.get("route_observed") or "").lower()
        template = str((spec.get("model") or {}).get("template") or "").lower()
        if raw_route != "sublingual":
            issues.append(_issue("route_observation_missing", "BLOCKER", "sl route has no explicit observed sublingual route"))
        if "oral" not in template and "extravascular" not in template:
            issues.append(_issue("route_model_unsupported", "ERROR", "sublingual route is not connected to an extravascular model"))

    basis = str(parsed.get("clearance_basis") or "apparent").strip().lower()
    f = _float(parsed.get("bioavailability_frac"))
    f1 = _float(theta.get("F1"))
    if route in {"po", "sl"} and f is not None and f1 is not None:
        expected_f1 = f if basis == SYSTEMIC_ORAL_BASIS else 1.0
        if not math.isclose(f1, expected_f1, rel_tol=0, abs_tol=1e-9):
            issues.append(_issue("f1_basis_mismatch", "ERROR", f"basis={basis}, F1={f1}, expected={expected_f1}"))

    auc = ((targets.get("targets") or {}).get("auc")) or {}
    auc_basis = str(auc.get("basis") or "").strip().lower()
    dose = _float((((targets.get("scenario") or {}).get("dose")) or {}).get("value"))
    cl = _float(derived.get("CL_abs_L_per_h_at_70kg"))
    if dose is not None and cl and cl > 0 and _float(auc.get("value")) is not None:
        if auc_basis == "f_dose_over_cl" and route in {"po", "sl"} and f is not None:
            expected_auc = dose * 1000.0 * f / cl
        elif auc_basis == "dose_over_cl":
            expected_auc = dose * 1000.0 / cl
        else:
            expected_auc = None
        if expected_auc is not None and not math.isclose(float(auc["value"]), expected_auc, rel_tol=0, abs_tol=1e-6):
            issues.append(_issue("auc_parameterization_mismatch", "ERROR", f"basis={auc_basis}, target={auc['value']}, expected={expected_auc}"))

    basis_source = str(parsed.get("clearance_basis_source") or "").strip().lower()
    if route in {"po", "sl"} and basis == SYSTEMIC_ORAL_BASIS and basis_source in {"", "unit_inferred"}:
        issues.append(_issue("clearance_basis_not_verified", "BLOCKER", "systemic oral CL basis is inferred from the unit and lacks an explicit primary-source review", field="pk_parsed.clearance_basis"))

    sources = pk.get("sources") or []
    source_map: dict[str, dict[str, Any]] = {}
    for source in sources:
        source_id = str(source.get("id") or "").strip()
        url = str(source.get("url") or "").strip()
        if not source_id:
            issues.append(_issue("source_register_id_missing", "BLOCKER", f"source URL has no stable id: {url}"))
        else:
            source_map[source_id] = source
    provenance = pk.get("value_provenance") or {}
    for field in REQUIRED_FIELDS:
        entry = provenance.get(field)
        if not isinstance(entry, dict):
            issues.append(_issue("value_provenance_missing", "BLOCKER", "value-level provenance entry is missing", field=field))
            continue
        source_id = entry.get("source_id")
        if not source_id:
            issues.append(_issue("value_source_unmapped", "BLOCKER", "value is not mapped to an exact source", field=field))
        elif str(source_id) not in source_map:
            issues.append(_issue("value_source_unknown", "ERROR", f"source_id={source_id!r} does not resolve", field=field))
        if str(entry.get("source_review_status") or "").lower() != "checked":
            issues.append(_issue("value_source_not_checked", "BLOCKER", f"source_review_status={entry.get('source_review_status')!r}", field=field))
        derived_parameter = (entry.get("conversion") or {}).get("method") == "derived_formula"
        if entry.get("source_id") and str(entry.get("source_review_status") or "").lower() == "checked":
            if not derived_parameter and (not entry.get("source_locator") or not entry.get("exact_quote")):
                issues.append(
                    _issue(
                        "citation_locator_or_quote_missing",
                        "REVIEW",
                        "checked summary lacks a section/table/page locator or short exact quote; it is not value-level citation-complete",
                        field=field,
                    )
                )
        if entry.get("value_basis") in {"derived_from_reported", "derived_from_half_life", "fixture_derived"} and derived_parameter:
            issues.append(_issue("fixture_derived_parameter", "REVIEW", "parameter is derived rather than directly reported; retain as fixture-only", field=field))

    # For a systemic oral model, F is not optional metadata: it is in the AUC
    # equation.  Keep the same fail-closed source/locator/quote discipline used
    # for CL/V/t1/2, while distinguishing a reported F from a midpoint/bound
    # selected as a deterministic fixture value.
    if route == "po" and basis == SYSTEMIC_ORAL_BASIS and f is not None:
        f_entry = provenance.get("bioavailability_frac")
        f_field = "bioavailability_frac"
        if not isinstance(f_entry, dict):
            issues.append(_issue("bioavailability_provenance_missing", "BLOCKER", "systemic oral AUC uses F but value-level F provenance is missing", field=f_field))
        else:
            f_source_id = f_entry.get("source_id")
            if not f_source_id:
                issues.append(_issue("bioavailability_source_unmapped", "BLOCKER", "systemic oral F is not mapped to an exact source", field=f_field))
            elif str(f_source_id) not in source_map:
                issues.append(_issue("bioavailability_source_unknown", "ERROR", f"source_id={f_source_id!r} does not resolve", field=f_field))
            if str(f_entry.get("source_review_status") or "").lower() != "checked":
                issues.append(_issue("bioavailability_source_not_checked", "BLOCKER", f"source_review_status={f_entry.get('source_review_status')!r}", field=f_field))
            if f_entry.get("source_id") and str(f_entry.get("source_review_status") or "").lower() == "checked":
                if not f_entry.get("source_locator") or not f_entry.get("exact_quote"):
                    issues.append(_issue("bioavailability_locator_or_quote_missing", "REVIEW", "checked F summary lacks a locator or short exact quote", field=f_field))
            if (f_entry.get("conversion") or {}).get("method") == "derived_formula":
                issues.append(_issue("bioavailability_fixture_derived", "REVIEW", "F is a range midpoint/bound or other deterministic selection; retain the selection rule and context", field=f_field))

    raw_cl = str((pk.get("pk_raw") or {}).get("clearance") or "")
    if _BSA_UNIT.search(raw_cl) and not (parsed.get("normalization_reference") or (pk.get("derived") or {}).get("normalization_reference")):
        issues.append(_issue("bsa_reference_not_recorded", "BLOCKER", "clearance uses a 1.73 m2-normalized unit without an explicit BSA reference policy", field="pk_raw.clearance"))

    # A source register may intentionally retain secondary URLs as discovery
    # aids. They are a review finding only when a canonical value actually
    # points to one; unused discovery URLs must not make an otherwise
    # value-level-complete drug look unresolved.
    used_source_ids = {
        str(entry.get("source_id"))
        for entry in provenance.values()
        if isinstance(entry, dict) and entry.get("source_id")
    }
    secondary_sources_used = [
        str(source.get("url"))
        for source in sources
        if str(source.get("id") or "") in used_source_ids
        and source_kind(str(source.get("url") or "")) == "secondary_or_aggregator"
    ]
    if secondary_sources_used:
        issues.append(_issue("secondary_source_used_for_value", "REVIEW", f"canonical values use secondary sources ({len(secondary_sources_used)}); replace or explicitly justify them"))

    t_half = _float(parsed.get("half_life_h"))
    v = _float(derived.get("V_abs_L_at_70kg"))
    if cl and v and t_half and cl > 0 and v > 0:
        implied = math.log(2.0) * v / cl
        rel = abs(implied - t_half) / t_half
        if rel > 0.25:
            issues.append(_issue("one_compartment_structural_mismatch", "REVIEW", f"CL/V imply t1/2={implied:.6g} h vs extracted {t_half:.6g} h"))

    errors = sum(issue["severity"] == "ERROR" for issue in issues)
    blockers = sum(issue["severity"] == "BLOCKER" for issue in issues)
    status = "ERROR" if errors else "REVIEW_REQUIRED" if blockers else "PASS"
    return {"slug": slug, "route": route, "status": status, "issues": issues, "errors": errors, "blockers": blockers}


def review_library(root: Path) -> dict[str, Any]:
    results = [review_drug(root, path) for path in sorted((root / "drugs").glob("*/")) if (path / "pk.yml").exists()]
    counts = {
        "drugs": len(results),
        "pass": sum(result["status"] == "PASS" for result in results),
        "review_required": sum(result["status"] == "REVIEW_REQUIRED" for result in results),
        "error": sum(result["status"] == "ERROR" for result in results),
        "blockers": sum(result["blockers"] for result in results),
        "errors": sum(result["errors"] for result in results),
    }
    return {"status": "PASS" if counts["errors"] == 0 and counts["blockers"] == 0 else "NOT_READY", "counts": counts, "drugs": results}


def render_markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    known_limitations = {
        "fixture_derived_parameter",
        "bioavailability_fixture_derived",
        "one_compartment_structural_mismatch",
    }
    open_review_findings = sum(
        1
        for result in report["drugs"]
        for issue in result["issues"]
        if issue["severity"] == "REVIEW" and issue["code"] not in known_limitations
    )
    known_limitation_count = sum(
        1
        for result in report["drugs"]
        for issue in result["issues"]
        if issue["severity"] == "REVIEW" and issue["code"] in known_limitations
    )
    lines = [
        "# Pharmacology / PK Strict Review",
        "",
        "> Automated fail-closed review from a pharmacology/PK reviewer perspective. This is not human clinical sign-off.",
        "",
        f"**Contract verdict: {report['status']}** — {counts['drugs']} drugs; PASS {counts['pass']}; REVIEW_REQUIRED {counts['review_required']}; ERROR {counts['error']}; blockers {counts['blockers']}; errors {counts['errors']}; open review findings {open_review_findings}; known fixture/model limitations {known_limitation_count}.",
        "",
        f"**Publication readiness: {'CONDITIONAL' if open_review_findings or known_limitation_count else 'READY FOR HUMAN REVIEW'}** — known limitations are disclosed rather than promoted to direct clinical evidence. This is not human clinical sign-off.",
        "",
        "A drug is not publication-ready when a route/model error exists, when a value lacks an exact checked source mapping, or when a checked summary lacks a locator/quote. Unresolved evidence is recorded as a blocker rather than silently filled.",
        "",
        "## Drug-level findings",
        "",
        "| Drug | Route | Status | Errors | Blockers | Findings |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for result in report["drugs"]:
        findings = "; ".join(
            f"KNOWN LIMITATION: {issue['code']}"
            if issue["code"] in known_limitations
            else f"OPEN: {issue['code']}"
            for issue in result["issues"]
        )
        lines.append(f"| {result['slug']} | {result['route']} | {result['status']} | {result['errors']} | {result['blockers']} | {findings or 'none'} |")
    lines.extend([
        "",
        "## Review policy",
        "",
        "- Oral apparent parameters (CL/F, V/F): F1=1 and AUC consistency target is Dose/CL_apparent.",
        "- Oral or sublingual systemic parameters: F1=F and AUC consistency target is F×Dose/CL_systemic.",
        "- A sublingual route is represented only by an explicitly labelled first-order extravascular fixture approximation; it is not interchangeable with GI oral absorption.",
        "- Derived V or CL values remain fixture-derived unless their formula, raw value, unit, and source are recorded.",
        "- PubMed/DailyMed are eligible primary/regulatory source classes; aggregators may remain as discovery aids but cannot close a value-level evidence gap. A secondary URL is an open finding only when a canonical value actually uses it.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default="docs/PHARMACOLOGY_REVIEW.md")
    parser.add_argument("--strict", action="store_true", help="return non-zero while any blocker/error remains")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = review_library(root)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_markdown(report), encoding="utf-8")
    print(f"Pharmacology review: {report['status']} ({report['counts']})")
    return 1 if args.strict and report["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
