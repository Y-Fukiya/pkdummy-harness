#!/usr/bin/env python3
"""Harvest CL/V from DailyMed and/or PubMed/PMC, then generate v0.3-style templates.

Typical usage:

  # 1) Create a jobs file (see docs/HARVEST.md for format)
  uv run --with requests --with lxml --with pyyaml python tools/harvest_and_generate.py \
      --jobs jobs.yml --repo .

It writes/updates:
  - drugs/<slug>/pk.yml
  - drugs/<slug>/spec_*.yml
  - drugs/<slug>/targets.yml

and can optionally rebuild INDEX.csv (use tools/rebuild_index.py).
"""

from __future__ import annotations

# Allow running as a script:
#   python tools/harvest_and_generate.py ...
# by ensuring the repo root (parent of this file) is on sys.path.
import os
import sys
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import argparse
import json
import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from tools.dailymed import search_spls, pick_best_setid, fetch_spl_xml, extract_relevant_text_from_spl_xml
from tools.ncbi_eutils import esearch, elink_pubmed_to_pmc, efetch_pmc_fulltext_xml, efetch_pubmed_abstract, strip_xml_to_text
from tools.pk_extract import extract_pk_from_text, extract_pk_from_pkrow
from tools.template_gen import generate_drug_folder, slugify

def load_jobs(path: Path) -> List[Dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "jobs" in data:
        data = data["jobs"]
    if not isinstance(data, list):
        raise ValueError("jobs.yml must be a list, or {jobs: [...]} structure.")
    return data

def harvest_from_dailymed(drug_name: str, *, route: str = "oral", prefer_basis: str = "auto", setid: Optional[str] = None) -> Dict[str, Any]:
    if not setid:
        hits = search_spls(drug_name, pagesize=25, page=1)
        best = pick_best_setid(drug_name, hits)
        if not best:
            return {"ok": False, "source": "dailymed", "error": f"No SPL hits for {drug_name}"}
        setid = best.setid
        picked_meta = {"title": best.title, "published_date": best.published_date, "spl_version": best.spl_version}
    else:
        picked_meta = {}

    xml_bytes = fetch_spl_xml(setid)
    # Pass 1: PK sections only
    text_pk = extract_relevant_text_from_spl_xml(xml_bytes, only_pk_sections=True)
    pk_pk = extract_pk_from_text(text_pk, route=route, prefer_basis=prefer_basis)

    # Pass 2: if still missing CL/V, broaden to all sections (sometimes CL/V is elsewhere)
    if not pk_pk.get("clearance") or not pk_pk.get("volume"):
        text_all = extract_relevant_text_from_spl_xml(xml_bytes, only_pk_sections=False)
        pk_all = extract_pk_from_text(text_all, route=route, prefer_basis=prefer_basis)
        # Merge, preferring pass-1 values and using pass-2 to fill gaps
        pk = {
            "clearance": pk_pk.get("clearance") or pk_all.get("clearance"),
            "volume": pk_pk.get("volume") or pk_all.get("volume"),
            "clearance_basis": pk_pk.get("clearance_basis") or pk_all.get("clearance_basis"),
            "volume_basis": pk_pk.get("volume_basis") or pk_all.get("volume_basis"),
            "half_life_h": pk_pk.get("half_life_h") or pk_all.get("half_life_h"),
            "bioavailability_frac": pk_pk.get("bioavailability_frac") or pk_all.get("bioavailability_frac"),
            "evidence": (pk_pk.get("evidence") or []) + (pk_all.get("evidence") or []),
            "notes": (pk_pk.get("notes") or []) + (pk_all.get("notes") or []),
            "diagnostics": {
                "pass_pk_sections": pk_pk.get("diagnostics", {}),
                "pass_all_sections": pk_all.get("diagnostics", {}),
            },
        }
        text = text_pk + "\n\n## EXTRA_SECTIONS\n" + text_all
    else:
        text = text_pk
        pk = dict(pk_pk)
        pk["diagnostics"] = {"pass_pk_sections": pk_pk.get("diagnostics", {})}
    return {
        "ok": True,
        "source": "dailymed",
        "setid": setid,
        "picked": picked_meta,
        "text": text,
        "pk": pk,
    }

def harvest_from_pubmed(drug_name: str, *, route: str = "oral", prefer_basis: str = "auto", pmid: Optional[str] = None, query: Optional[str] = None, retmax: int = 5) -> Dict[str, Any]:
    # If pmid not provided, search
    if not pmid:
        term = query or f"{drug_name}[Title/Abstract] AND (pharmacokinetics OR clearance OR volume of distribution)"
        pmids = esearch("pubmed", term, retmax=retmax)
    else:
        pmids = [pmid]

    if not pmids:
        return {"ok": False, "source": "pubmed", "error": "No PMIDs found"}

    # Prefer articles with PMCID (open full text in PMC)
    pmcids = elink_pubmed_to_pmc(pmids)
    chosen = None
    text = ""
    if pmcids:
        chosen = {"pmcid": pmcids[0], "via": "pmc_fulltext"}
        xml = efetch_pmc_fulltext_xml(pmcids[0])
        text = strip_xml_to_text(xml)
    else:
        chosen = {"pmid": pmids[0], "via": "pubmed_abstract"}
        text = efetch_pubmed_abstract(pmids[0])

    pk = extract_pk_from_text(text, route=route, prefer_basis=prefer_basis)
    pk = dict(pk)
    pk["diagnostics"] = {
        "via": chosen.get("via"),
        "pmids": pmids[:10],
        "pmcids": pmcids[:10],
        "extract": pk.get("diagnostics", {}),
    }
    return {"ok": True, "source": "pubmed", "chosen": chosen, "text": text, "pk": pk, "pmids": pmids[:10], "pmcids": pmcids[:10]}

def merge_pk(a: Dict[str, Any], b: Dict[str, Any], *, source: Optional[str] = None) -> Dict[str, Any]:
    """Merge extracted pk dicts, preferring a then b.

    In v0.8, we also accumulate `diagnostics` entries so missing-parameter
    reasons can be written to EXCLUDED.csv in a machine-readable form.
    """
    out = {}
    for k in ["clearance", "volume", "half_life_h", "bioavailability_frac", "clearance_basis", "volume_basis"]:
        out[k] = a.get(k) or b.get(k)
    # evidence/notes
    out["evidence"] = (a.get("evidence") or []) + (b.get("evidence") or [])
    out["notes"] = (a.get("notes") or []) + (b.get("notes") or [])
    # diagnostics (list of per-source dicts)
    out["diagnostics"] = list(a.get("diagnostics") or [])
    bd = b.get("diagnostics")
    if bd is not None:
        out["diagnostics"].append({"source": source or b.get("source") or "unknown", "details": bd})
    return out


def _route_category(route: str) -> str:
    r = (route or "").strip().lower()
    if any(k in r for k in ["inhal", "resp", "pulmon", "nasal"]):
        return "inhalation"
    if any(k in r for k in ["topical", "dermal", "transderm", "ophthalm", "otic"]):
        return "topical"
    if r.startswith("iv") or "intraven" in r:
        return "iv"
    if r.startswith("po") or r.startswith("oral"):
        return "oral"
    return "other"


def _pk_abs_from_units(pk: Dict[str, Any], wt_kg: float) -> Dict[str, Optional[float]]:
    """Convert CL/V to absolute units when possible.

    Returns: {"cl_L_per_h": float|None, "v_L": float|None}
    """
    cl = pk.get("clearance")
    v = pk.get("volume")
    cl_abs: Optional[float] = None
    v_abs: Optional[float] = None
    if isinstance(cl, dict) and "value" in cl:
        try:
            if cl.get("unit") == "L/h/kg":
                cl_abs = float(cl["value"]) * float(wt_kg)
            else:
                cl_abs = float(cl["value"])
        except Exception:
            cl_abs = None
    if isinstance(v, dict) and "value" in v:
        try:
            if v.get("unit") == "L/kg":
                v_abs = float(v["value"]) * float(wt_kg)
            else:
                v_abs = float(v["value"])
        except Exception:
            v_abs = None
    return {"cl_L_per_h": cl_abs, "v_L": v_abs}


def apply_rescue_strategies(
    pk: Dict[str, Any],
    *,
    combined_text: str,
    route: str,
    prefer_basis: str,
    wt_kg: float,
    reason_codes: List[str],
) -> Dict[str, Any]:
    """Try reason-driven rescue steps and record which ones were applied."""
    pk = dict(pk)
    pk.setdefault("notes", [])
    pk.setdefault("evidence", [])

    # 1) Table rescue: parse synthesized PKROW segments.
    if (not pk.get("clearance") or not pk.get("volume")) and ("PKROW:" in (combined_text or "")):
        try:
            pkrow = extract_pk_from_pkrow(combined_text, route=route, prefer_basis=prefer_basis)
            # Fill only gaps
            before = (bool(pk.get("clearance")), bool(pk.get("volume")))
            pk["clearance"] = pk.get("clearance") or pkrow.get("clearance")
            pk["volume"] = pk.get("volume") or pkrow.get("volume")
            pk["clearance_basis"] = pk.get("clearance_basis") or pkrow.get("clearance_basis")
            pk["volume_basis"] = pk.get("volume_basis") or pkrow.get("volume_basis")
            pk["half_life_h"] = pk.get("half_life_h") or pkrow.get("half_life_h")
            pk["bioavailability_frac"] = pk.get("bioavailability_frac") or pkrow.get("bioavailability_frac")
            pk["evidence"].extend(pkrow.get("evidence") or [])
            pk["notes"].extend(pkrow.get("notes") or [])
            after = (bool(pk.get("clearance")), bool(pk.get("volume")))
            if after != before:
                reason_codes.append("RESCUED_PKROW")
        except Exception as e:
            pk["notes"].append(f"PKROW rescue failed: {e}")

    # 2) Derivation rescue: if one of CL/V exists and half-life exists.
    hl = pk.get("half_life_h")
    if hl is not None:
        try:
            hl_h = float(hl)
        except Exception:
            hl_h = None
    else:
        hl_h = None

    if hl_h and hl_h > 0:
        abs_ = _pk_abs_from_units(pk, wt_kg)
        cl_abs = abs_["cl_L_per_h"]
        v_abs = abs_["v_L"]
        import math
        ke = math.log(2.0) / hl_h
        if pk.get("clearance") and not pk.get("volume") and cl_abs is not None and ke > 0:
            v = cl_abs / ke
            if v > 0:
                pk["volume"] = {"value": float(v), "unit": "L"}
                pk.setdefault("volume_basis", pk.get("clearance_basis") or ("apparent" if route.lower().startswith("o") else "systemic"))
                pk["notes"].append("Derived V from CL and t1/2 assuming ke=ln(2)/t1/2 (adult ref).")
                pk["evidence"].append({"param": "volume", "value_raw": f"Derived: V=CL/(ln2/t1/2) using t1/2={hl_h} h", "context": "rescue"})
                reason_codes.append("RESCUED_DERIVE_V")
        if pk.get("volume") and not pk.get("clearance") and v_abs is not None and ke > 0:
            cl = ke * v_abs
            if cl > 0:
                pk["clearance"] = {"value": float(cl), "unit": "L/h"}
                pk.setdefault("clearance_basis", pk.get("volume_basis") or ("apparent" if route.lower().startswith("o") else "systemic"))
                pk["notes"].append("Derived CL from V and t1/2 assuming ke=ln(2)/t1/2 (adult ref).")
                pk["evidence"].append({"param": "clearance", "value_raw": f"Derived: CL=(ln2/t1/2)*V using t1/2={hl_h} h", "context": "rescue"})
                reason_codes.append("RESCUED_DERIVE_CL")

    return pk


def derive_reason_codes(
    *,
    name: str,
    route: str,
    pk: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> List[str]:
    """Create machine-readable reason codes for missing CL/V."""
    codes: List[str] = []
    missing = []
    if not pk.get("clearance"):
        missing.append("clearance")
        codes.append("MISSING_CLEARANCE")
    if not pk.get("volume"):
        missing.append("volume")
        codes.append("MISSING_VOLUME")

    # Route-based hint
    if _route_category(route) == "inhalation":
        codes.append("ROUTE_INHALATION")

    # Source-level hints
    for src in sources:
        if src.get("type") == "dailymed" and src.get("error"):
            codes.append("DAILYMED_ERROR")
        if src.get("type") == "dailymed" and not src.get("setid") and src.get("picked") is None and src.get("error") is None:
            # very rare, but keep for completeness
            codes.append("NO_DAILYMED_HIT")
        if src.get("type") == "pubmed" and src.get("error"):
            codes.append("PUBMED_ERROR")
        if src.get("type") == "pubmed" and isinstance(src.get("chosen"), dict):
            via = src["chosen"].get("via")
            if via == "pubmed_abstract":
                codes.append("PUBMED_ABSTRACT_ONLY")
            if via == "pmc_fulltext":
                codes.append("PUBMED_PMC_FULLTEXT")

    # Diagnostics-driven hints (from pk["diagnostics"] list)
    for d in (pk.get("diagnostics") or []):
        det = (d or {}).get("details") or {}
        # DailyMed pass diagnostics
        if isinstance(det, dict) and "pass_pk_sections" in det:
            p1 = det.get("pass_pk_sections") or {}
            ck = p1.get("clearance_kw_hits")
            cc = p1.get("clearance_candidates")
            vk = p1.get("volume_kw_hits")
            vc = p1.get("volume_candidates")
            if ck and (cc == 0) and "MISSING_CLEARANCE" in codes:
                codes.append("CLEARANCE_KEYWORDS_BUT_NO_CANDIDATES")
            if vk and (vc == 0) and "MISSING_VOLUME" in codes:
                codes.append("VOLUME_KEYWORDS_BUT_NO_CANDIDATES")
            if p1.get("has_pkrow") and ("MISSING_CLEARANCE" in codes or "MISSING_VOLUME" in codes):
                codes.append("HAS_PKROW_TEXT")
        # PubMed extract diagnostics
        if isinstance(det, dict) and det.get("extract"):
            pe = det.get("extract")
            ck = pe.get("clearance_kw_hits")
            cc = pe.get("clearance_candidates")
            vk = pe.get("volume_kw_hits")
            vc = pe.get("volume_candidates")
            if ck and (cc == 0) and "MISSING_CLEARANCE" in codes:
                codes.append("PUBMED_CLEARANCE_KW_NO_CAND")
            if vk and (vc == 0) and "MISSING_VOLUME" in codes:
                codes.append("PUBMED_VOLUME_KW_NO_CAND")

    # De-duplicate while preserving order
    seen = set()
    deduped = []
    for c in codes:
        if c not in seen:
            deduped.append(c)
            seen.add(c)
    return deduped

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=str, required=True, help="YAML file describing drugs and sources")
    ap.add_argument("--repo", type=str, default=".", help="Repo root (contains drugs/ and INDEX.csv)")
    ap.add_argument("--default-dose-mg", type=float, default=100.0, help="Dose used in generated templates if not specified per job")
    ap.add_argument("--no-pubmed", action="store_true", help="Skip PubMed/PMC harvesting")
    ap.add_argument("--report", type=str, default="reports/harvest_report.json", help="Write JSON report here (relative to repo)")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    jobs = load_jobs(Path(args.jobs))

    report = {
        "jobs": [],
        "summary": {"ok": 0, "failed": 0, "missing_params": 0, "reason_counts": {}},
    }

    excluded_rows: List[Dict[str, Any]] = []

    for job in jobs:
        name = job.get("name") or job.get("drug") or job.get("drug_name")
        if not name:
            raise ValueError(f"Job missing name: {job}")
        route = job.get("route") or job.get("route_inferred") or "oral"
        # Parameter basis preference:
        #   - auto (default): oral -> apparent (CL/F, V/F), iv -> systemic
        #   - apparent: prioritize CL/F, V/F when both exist
        #   - systemic: prioritize CL, V
        #   - any: no preference
        prefer_basis = str(job.get("param_basis") or job.get("prefer_basis") or "auto")
        dose_mg = float(job.get("dose_mg") or args.default_dose_mg)
        wt_kg = float(job.get("weight_ref_kg_for_abs") or job.get("wt_kg") or 70.0)

        sources_meta = []
        pk_text_parts = []
        pk_merged = {
            "clearance": None,
            "volume": None,
            "clearance_basis": None,
            "volume_basis": None,
            "half_life_h": None,
            "bioavailability_frac": None,
            "evidence": [],
            "notes": [],
            "diagnostics": [],
        }

        # DailyMed
        if job.get("dailymed", True):
            dm_setid = None
            if isinstance(job.get("dailymed"), dict):
                dm_setid = job["dailymed"].get("setid")
            try:
                dm = harvest_from_dailymed(name, route=route, prefer_basis=prefer_basis, setid=dm_setid)
                if not dm.get("ok"):
                    sources_meta.append({"type": "dailymed", "error": dm.get("error") or "unknown_error"})
                else:
                    sources_meta.append({"type": "dailymed", "setid": dm.get("setid"), "picked": dm.get("picked")})
                    if dm.get("text"):
                        pk_text_parts.append("[DailyMed]\n" + dm["text"][:20000])
                    if dm.get("pk"):
                        pk_merged = merge_pk(pk_merged, dm["pk"], source="dailymed")
            except Exception as e:
                sources_meta.append({"type": "dailymed", "error": str(e)})

        # PubMed/PMC
        if not args.no_pubmed and job.get("pubmed", True):
            pmid = None
            query = None
            if isinstance(job.get("pubmed"), dict):
                pmid = job["pubmed"].get("pmid")
                query = job["pubmed"].get("query")
            try:
                pm = harvest_from_pubmed(name, route=route, prefer_basis=prefer_basis, pmid=pmid, query=query, retmax=int(job.get("pubmed_retmax") or 5))
                if not pm.get("ok"):
                    sources_meta.append({"type": "pubmed", "error": pm.get("error") or "unknown_error"})
                else:
                    sources_meta.append({"type": "pubmed", "chosen": pm.get("chosen"), "pmids": pm.get("pmids"), "pmcids": pm.get("pmcids")})
                    if pm.get("text"):
                        pk_text_parts.append("[PubMed/PMC]\n" + pm["text"][:20000])
                    if pm.get("pk"):
                        pk_merged = merge_pk(pk_merged, pm["pk"], source="pubmed")
            except Exception as e:
                sources_meta.append({"type": "pubmed", "error": str(e)})

        # Combine harvested text for rescue passes and diagnostics
        combined_text = "\n\n".join(pk_text_parts)

        # Reason-driven rescue strategies
        rescue_codes: List[str] = []
        pk_merged = apply_rescue_strategies(
            pk_merged,
            combined_text=combined_text,
            route=route,
            prefer_basis=prefer_basis,
            wt_kg=wt_kg,
            reason_codes=rescue_codes,
        )

        reason_codes = derive_reason_codes(name=name, route=route, pk=pk_merged, sources=sources_meta)
        for rc in rescue_codes:
            if rc not in reason_codes:
                reason_codes.append(rc)

        # If still missing CL or V, keep job in report but don't generate spec
        missing = []
        if not pk_merged.get("clearance"):
            missing.append("clearance")
        if not pk_merged.get("volume"):
            missing.append("volume")

        job_result = {
            "name": name,
            "route": route,
            "dose_mg": dose_mg,
            "weight_ref_kg_for_abs": wt_kg,
            "sources": sources_meta,
            "pk": {k: pk_merged.get(k) for k in ["clearance","volume","clearance_basis","volume_basis","half_life_h","bioavailability_frac"]},
            "missing": missing,
            "reason_codes": reason_codes,
            "notes": pk_merged.get("notes", []),
            "evidence": pk_merged.get("evidence", [])[:6],
        }

        if missing:
            report["summary"]["missing_params"] += 1
            report["jobs"].append({**job_result, "status": "missing_params"})
            # Write to excluded rows
            excluded_rows.append({
                "drug": name,
                "slug": slugify(name),
                "route_inferred": route,
                "status": "missing_params",
                "missing": ",".join(missing),
                "reason": ";".join(reason_codes),
                "reason_json": json.dumps({
                    "reason_codes": reason_codes,
                    "missing": missing,
                    "sources": sources_meta,
                    "pk": job_result["pk"],
                    "diagnostics": pk_merged.get("diagnostics", []),
                }, ensure_ascii=False),
                "remediation_hint": "consider_pubmed_pmc_or_manual" if "PUBMED_PMC_FULLTEXT" not in reason_codes else "manual_review",
            })
            # Update reason counts
            for rc in reason_codes:
                report["summary"]["reason_counts"][rc] = report["summary"]["reason_counts"].get(rc, 0) + 1
            continue

        # generate
        try:
            pk_text = combined_text
            out_dir = generate_drug_folder(
                out_root=repo,
                name=name,
                route="oral" if route.lower().startswith("o") else "iv",
                dose_mg=dose_mg,
                pk_text=pk_text,
                sources=sources_meta,
                pk_parsed={
                    "clearance": pk_merged["clearance"],
                    "volume": pk_merged["volume"],
                    "clearance_basis": pk_merged.get("clearance_basis"),
                    "volume_basis": pk_merged.get("volume_basis"),
                    "half_life_h": pk_merged.get("half_life_h"),
                    "half_life_h_range": [pk_merged.get("half_life_h"), pk_merged.get("half_life_h")] if pk_merged.get("half_life_h") else None,
                    "bioavailability_frac": pk_merged.get("bioavailability_frac"),
                    "weight_ref_kg_for_abs": wt_kg,
                },
                wt_kg=wt_kg,
            )
            report["summary"]["ok"] += 1
            report["jobs"].append({**job_result, "status": "ok", "output": str(out_dir.relative_to(repo))})
        except Exception as e:
            report["summary"]["failed"] += 1
            report["jobs"].append({**job_result, "status": "failed", "error": str(e)})
            excluded_rows.append({
                "drug": name,
                "slug": slugify(name),
                "route_inferred": route,
                "status": "failed",
                "missing": ",".join(missing),
                "reason": ";".join(reason_codes + ["GENERATION_FAILED"]),
                "reason_json": json.dumps({
                    "reason_codes": reason_codes,
                    "error": str(e),
                    "sources": sources_meta,
                    "pk": job_result["pk"],
                    "diagnostics": pk_merged.get("diagnostics", []),
                }, ensure_ascii=False),
                "remediation_hint": "check_generated_pk_and_units",
            })
            for rc in (reason_codes + ["GENERATION_FAILED"]):
                report["summary"]["reason_counts"][rc] = report["summary"]["reason_counts"].get(rc, 0) + 1

    report_path = (repo / args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write EXCLUDED.csv (machine readable reasons)
    excluded_path = repo / "EXCLUDED.csv"
    if excluded_rows:
        excluded_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "drug",
            "slug",
            "route_inferred",
            "status",
            "missing",
            "reason",
            "reason_json",
            "remediation_hint",
        ]
        with excluded_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in excluded_rows:
                w.writerow({k: r.get(k, "") for k in fieldnames})

    print(f"[harvest] ok={report['summary']['ok']} missing={report['summary']['missing_params']} failed={report['summary']['failed']}")
    print(f"[harvest] report: {report_path}")
    if excluded_rows:
        print(f"[harvest] excluded: {excluded_path} ({len(excluded_rows)} rows)")
    if report["summary"]["failed"] or report["summary"]["missing_params"]:
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
