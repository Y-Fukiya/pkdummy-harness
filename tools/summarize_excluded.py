#!/usr/bin/env python3
"""
Summarize EXCLUDED.csv (produced by tools/harvest_and_generate.py) and recommend parser improvements.

Usage:
  python tools/summarize_excluded.py --excluded EXCLUDED.csv
  python tools/summarize_excluded.py --excluded EXCLUDED.csv --out-md reports/excluded_summary.md
  python tools/summarize_excluded.py --excluded EXCLUDED.csv --out-md reports/excluded_summary.md --out-csv reports/excluded_next_steps.csv

Outputs:
- counts by reason code / missing fields / route
- global recommended remediation buckets
- per-drug next-step suggestions inferred from `reason` + `reason_json`
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


def split_reason_codes(s: str) -> List[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    return [c.strip() for c in s.split(";") if c.strip()]


def split_missing(s: str) -> List[str]:
    if not isinstance(s, str) or not s.strip():
        return []
    # EXCLUDED.csv uses comma-join, but be forgiving.
    out: List[str] = []
    for tok in s.replace(";", ",").split(","):
        tok = tok.strip()
        if tok:
            out.append(tok)
    return out


def safe_json_loads(s: Any) -> Dict[str, Any]:
    if not isinstance(s, str) or not s.strip():
        return {}
    try:
        x = json.loads(s)
        return x if isinstance(x, dict) else {}
    except Exception:
        return {"__parse_error__": True, "__raw__": s[:5000]}


RECOMMENDATIONS = [
    # (predicate codes set, title, actions)
    ({"HAS_PKROW_TEXT", "MISSING_CLEARANCE"}, "表由来のCL抽出が弱い", [
        "DailyMed表のヘッダ推定を強化（列名に単位がある/単位列が別のケース）",
        "PKROWの直接パース対象キーワードを拡張（CL, CL/F, apparent clearance 等）",
    ]),
    ({"HAS_PKROW_TEXT", "MISSING_VOLUME"}, "表由来のV抽出が弱い", [
        "Vd/Vss/Vc/Vp/central volume/peripheral volume の同義語を拡張",
        "表の列結合（値列＋単位列）を改善",
    ]),
    ({"CLEARANCE_KEYWORDS_BUT_NO_CANDIDATES"}, "CLの正規表現/単位正規化が不足", [
        "mL/min/1.73m², L/hr/70kg, L/min/m² などの単位を追加",
        "“total clearance”, “systemic clearance”, “apparent oral clearance” の文脈を拾う",
    ]),
    ({"VOLUME_KEYWORDS_BUT_NO_CANDIDATES"}, "Vの正規表現/単位正規化が不足", [
        "‘total body water’/‘apparent volume’ など曖昧表現の救済（数値がある場合だけ採用）",
        "L/m², L/1.73m², mL/kg などを追加",
    ]),
    ({"PUBMED_ABSTRACT_ONLY"}, "PubMed抄録しか取れず値が出ない", [
        "PMCIDがある論文に寄せる（elinkでPMC優先）",
        "jobs.ymlでPMIDを固定する/retmaxを増やす/別ソース（PDF/label）を指定する",
    ]),
    ({"ROUTE_INHALATION"}, "吸入/局所製剤でCL/Vがラベルに無い", [
        "‘systemic exposure is low’ 等の場合はテンプレ前提を変更（吸収率/局所モデル）",
        "別途 ‘systemic PK’ の論文ソースを取る（PopPK/ClinPharm review）",
    ]),
]


def recommend_global(reason_counts: Counter) -> List[Tuple[str, List[str]]]:
    recs: List[Tuple[str, List[str]]] = []
    present = {k for k, v in reason_counts.items() if v > 0}
    for codes, title, actions in RECOMMENDATIONS:
        if codes & present:
            recs.append((title, actions))
    return recs


def _pk_has(pk: Dict[str, Any], key: str) -> bool:
    v = pk.get(key)
    if v is None:
        return False
    if isinstance(v, dict) and v.get("value") is None:
        return False
    return True


def suggest_job_overrides(reason_json: Dict[str, Any]) -> List[str]:
    """Return YAML snippet lines the user can paste into jobs.yml."""
    srcs = reason_json.get("sources") or []
    out: List[str] = []
    if isinstance(srcs, list):
        for s in srcs:
            if not isinstance(s, dict):
                continue
            if s.get("type") == "dailymed" and s.get("setid"):
                out.append(f"dailymed: {{setid: {s['setid']}}}")
            if s.get("type") == "pubmed" and isinstance(s.get("chosen"), dict) and s["chosen"].get("pmid"):
                out.append(f"pubmed: {{pmid: {s['chosen']['pmid']}}}")
    # Dedup while preserving order
    seen = set()
    dedup: List[str] = []
    for x in out:
        if x not in seen:
            dedup.append(x)
            seen.add(x)
    return dedup


def infer_next_steps(reason_codes: List[str], missing: List[str], reason_json: Dict[str, Any]) -> List[str]:
    """Per-drug next steps inferred from reason codes + reason_json."""
    steps: List[str] = []
    pk = reason_json.get("pk") or {}
    diag = reason_json.get("diagnostics") or []

    if reason_json.get("__parse_error__"):
        steps.append("reason_jsonが壊れているため、harvestの出力を確認（JSONが途中で途切れていないか）")

    # Source-level hints
    src_overrides = suggest_job_overrides(reason_json)
    if src_overrides:
        steps.append("再現性のため jobs.yml に固定値を入れる: " + " / ".join(src_overrides))

    # If PKROW exists, table path is the highest ROI
    if "HAS_PKROW_TEXT" in reason_codes:
        if "clearance" in missing:
            steps.append("DailyMed表（PKROW）からCLを拾えるように：ヘッダ/単位列推定を強化")
        if "volume" in missing:
            steps.append("DailyMed表（PKROW）からVを拾えるように：Vの同義語（Vss/Vc/Vp）と列結合を強化")

    # PubMed-only or abstract-only
    if "PUBMED_ABSTRACT_ONLY" in reason_codes:
        steps.append("PMC全文が取れるPMID/PMCIDに寄せる（elinkでPMC優先、またはPMID固定で当たり論文を指定）")

    # Missing CL/V with possible derivation routes
    has_hl = _pk_has(pk, "half_life_h")
    has_cl = _pk_has(pk, "clearance")
    has_v = _pk_has(pk, "volume")

    if "clearance" in missing or "MISSING_CLEARANCE" in reason_codes:
        if has_hl and has_v:
            steps.append("救済ルール適用候補：t1/2 と V から CL = ln(2)*V/t1/2 を導出")
        else:
            steps.append("CLの同義語/単位を追加（CL/F, CLr, systemic/total clearance、mL/min/1.73m² 等）")

    if "volume" in missing or "MISSING_VOLUME" in reason_codes:
        if has_hl and has_cl:
            steps.append("救済ルール適用候補：t1/2 と CL から V = CL*t1/2/ln(2) を導出")
        else:
            steps.append("Vの同義語/単位を追加（Vss, Vc, Vd, apparent volume、mL/kg, L/m² 等）")

    # Basis mismatch hints
    cl_basis = pk.get("clearance_basis")
    v_basis = pk.get("volume_basis")
    if cl_basis and v_basis and cl_basis != v_basis:
        steps.append(f"basis不一致：CL({cl_basis})とV({v_basis})の優先順位をjobs.ymlで指定（prefer_basis/systemic/apparent）")

    # Inhalation/topical routes often lack systemic params in label
    if "ROUTE_INHALATION" in reason_codes:
        steps.append("吸入/局所はラベルPKにCL/Vが無いことが多い：PopPK論文 or FDA/PMDAのClinPharmレビューを優先")

    if "GENERATION_FAILED" in reason_codes:
        steps.append("生成失敗：reports/harvest_report.jsonの該当jobを確認し、pk.ymlの必須キー欠落や単位の不整合を修正")

    # Diagnostics-driven hints (best-effort)
    unit_hits: List[str] = []
    try:
        for entry in diag if isinstance(diag, list) else []:
            details = entry.get("details") if isinstance(entry, dict) else None
            if isinstance(details, dict):
                u = details.get("units_seen") or details.get("unit_candidates")
                if isinstance(u, list):
                    unit_hits.extend([str(x) for x in u if x])
    except Exception:
        pass
    unit_hits = list(dict.fromkeys(unit_hits))[:8]
    if unit_hits:
        steps.append("未対応の単位候補が見えています: " + ", ".join(unit_hits) + "（正規化ルール追加の候補）")

    # F missing is usually non-blocking; still, suggest.
    if "bioavailability_frac" in missing or "MISSING_F" in reason_codes:
        steps.append("Fは必須にしない運用ならOK（デフォルトF1=1で見かけCL/Vとして回す）。必要なら%表記パースを追加")

    # Dedup + limit
    dedup: List[str] = []
    seen = set()
    for s in steps:
        if s not in seen:
            dedup.append(s)
            seen.add(s)
    return dedup[:10]


def to_markdown_table(rows: List[Dict[str, str]]) -> List[str]:
    if not rows:
        return ["(none)"]
    headers = list(rows[0].keys())
    lines: List[str] = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        lines.append("| " + " | ".join(r.get(h, "") for h in headers) + " |")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--excluded", type=str, default="EXCLUDED.csv")
    ap.add_argument("--out-md", type=str, default="")
    ap.add_argument("--out-csv", type=str, default="")
    args = ap.parse_args()

    df = pd.read_csv(args.excluded)
    if df.empty:
        msg = "EXCLUDED.csv is empty: nothing to summarize."
        print(msg)
        if args.out_md:
            Path(args.out_md).write_text("# Excluded summary\n\n" + msg + "\n", encoding="utf-8")
            print(f"Wrote {args.out_md}")
        return 0

    reason_counts = Counter()
    missing_counts = Counter()
    route_counts = Counter()

    per_drug_rows: List[Dict[str, Any]] = []

    for _, r in df.iterrows():
        route = str(r.get("route_inferred", "unknown"))
        route_counts[route] += 1

        missing = split_missing(str(r.get("missing", "")))
        for m in missing:
            missing_counts[m] += 1

        reason_codes = split_reason_codes(str(r.get("reason", "")))
        for c in reason_codes:
            reason_counts[c] += 1

        rj = safe_json_loads(r.get("reason_json"))
        steps = infer_next_steps(reason_codes, missing, rj)
        per_drug_rows.append({
            "drug": str(r.get("drug", "")),
            "slug": str(r.get("slug", "")),
            "route": route,
            "missing": ",".join(missing),
            "reason_codes": ";".join(reason_codes),
            "next_steps": " / ".join(steps),
        })

    lines: List[str] = []
    lines.append("# Excluded summary\n")
    lines.append("## Route (inferred)\n")
    for k, v in route_counts.most_common():
        lines.append(f"- {k}: {v}")

    lines.append("\n## Missing fields\n")
    for k, v in missing_counts.most_common():
        lines.append(f"- {k}: {v}")

    lines.append("\n## Reason codes (top)\n")
    for k, v in reason_counts.most_common(30):
        lines.append(f"- {k}: {v}")

    lines.append("\n## Recommended next parser improvements\n")
    recs = recommend_global(reason_counts)
    if recs:
        for title, actions in recs:
            lines.append(f"### {title}")
            for a in actions:
                lines.append(f"- {a}")
            lines.append("")
    else:
        lines.append("- (No strong global signal; use per-drug next steps below.)\n")

    lines.append("\n## Per-drug next steps\n")
    md_rows: List[Dict[str, str]] = []
    for x in per_drug_rows:
        md_rows.append({
            "drug": x["drug"],
            "route": x["route"],
            "missing": x["missing"],
            "reason_codes": x["reason_codes"],
            "next_steps": x["next_steps"],
        })
    lines.extend(to_markdown_table(md_rows))

    out = "\n".join(lines)
    print(out)

    if args.out_md:
        Path(args.out_md).write_text(out, encoding="utf-8")
        print(f"\nWrote {args.out_md}")

    if args.out_csv:
        out_df = pd.DataFrame(per_drug_rows)
        Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
        out_df.to_csv(args.out_csv, index=False)
        print(f"Wrote {args.out_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
