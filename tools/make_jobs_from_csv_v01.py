#!/usr/bin/env python3
"""
Create jobs.yml for the "excluded 22" (v0.1-style strict selection) directly from all_pk_parameters_combined.csv.

Why this exists:
- The original v0.1 selection required (CL, V, t1/2) to be parseable.
- Oral drugs additionally required a numeric bioavailability (F).
- BSA-normalized clearance like "mL/min/1.73 m2" was treated as not usable (without BSA conversion),
  which is why e.g. aciclovir was excluded in v0.1.

This script reproduces that "15 selected / 22 excluded" split from the CSV, and writes jobs.yml
for ONLY the excluded drugs, so you can harvest (DailyMed/PubMed) and try to fill the missing params.

Usage:
  python tools/make_jobs_from_csv_v01.py --in all_pk_parameters_combined.csv --out jobs_excluded22.yml

Notes:
- It infers route as:
    Bioavailability contains "IV only" -> iv
    else -> oral
- It uses Source URL to pin:
    DailyMed: setid=... if present
    PubMed: pmid=... if present
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml

_RX_NUM = re.compile(r'(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?')

def _norm(s: Any) -> str:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    st = str(s)
    st = st.replace("–", "-").replace("−", "-")
    st = re.sub(r"\s+", " ", st).strip()
    return st

def _num_mid(s: str) -> Optional[float]:
    m = _RX_NUM.search(s)
    if not m:
        return None
    a = float(m.group(1))
    if m.group(2):
        b = float(m.group(2))
        return (a + b) / 2.0
    return a

def parse_half_life_h(raw: Any) -> Optional[float]:
    s = _norm(raw).lower()
    if not s:
        return None
    v = _num_mid(s)
    if v is None:
        return None
    if "day" in s:
        return v * 24.0
    if "min" in s:
        return v / 60.0
    # default to hours if "h" or "hour" appears; otherwise assume hours
    return v

def infer_route(raw_bio: Any) -> str:
    s = _norm(raw_bio).lower()
    if "iv only" in s:
        return "iv"
    return "oral"

def parse_bioavailability_frac(raw_bio: Any) -> Optional[float]:
    s = _norm(raw_bio).lower()
    if not s or "iv only" in s or s in {"n/a", "na"}:
        return None
    # percent range
    m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*%", s)
    if m:
        a = float(m.group(1))
        b = float(m.group(2))
        return ((a + b) / 2.0) / 100.0
    # percent single
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if m:
        return float(m.group(1)) / 100.0
    # fraction
    m = re.search(r"\b0\.\d+\b", s)
    if m:
        return float(m.group(0))
    return None

def parse_clearance_unit(raw_cl: Any) -> Tuple[Optional[float], Optional[str]]:
    s = _norm(raw_cl).lower()
    if not s or s in {"n/a", "na"}:
        return None, None
    v = _num_mid(s)
    if v is None:
        return None, None
    # v0.1 behavior: treat BSA-normalized units as NOT usable (needs conversion)
    if re.search(r"ml\s*/\s*min\s*/\s*1\.?73\s*m2", s) or "ml/min/1.73" in s:
        return v, "mL/min/1.73m2"
    if re.search(r"(l|liter)s?\s*/\s*h\s*/\s*kg", s) or "l/h/kg" in s:
        return v, "L/h/kg"
    if re.search(r"ml\s*/\s*min\s*/\s*kg", s) or "ml/min/kg" in s or re.search(r"ml\s*/\s*kg\s*/\s*min", s):
        return v, "mL/min/kg"
    if re.search(r"(l|liter)s?\s*/\s*h", s) or "l/h" in s:
        return v, "L/h"
    if re.search(r"ml\s*/\s*min", s):
        return v, "mL/min"
    if re.search(r"ml\s*/\s*h", s):
        return v, "mL/h"
    if re.search(r"l\s*/\s*min", s):
        return v, "L/min"
    return v, "unknown"

def cl_usable_v01(raw_cl: Any) -> bool:
    v, u = parse_clearance_unit(raw_cl)
    if v is None or u is None:
        return False
    # v0.1: BSA-normalized CL not usable without conversion
    if u == "mL/min/1.73m2":
        return False
    return u in {"L/h/kg","mL/min/kg","L/h","mL/min","mL/h","L/min"}

def parse_volume_unit(raw_v: Any) -> Tuple[Optional[float], Optional[str]]:
    s = _norm(raw_v).lower()
    if not s or s in {"n/a", "na"}:
        return None, None
    v = _num_mid(s)
    if v is None:
        return None, None
    if re.search(r"(l|liter)s?\s*/\s*kg", s) or "l/kg" in s:
        return v, "L/kg"
    if re.search(r"ml\s*/\s*kg", s) or "ml/kg" in s:
        return v, "mL/kg"
    if re.search(r"(l|liter)s?\b", s) and not re.search(r"/\s*kg", s):
        return v, "L"
    if re.search(r"ml\b", s) and not re.search(r"/\s*kg", s):
        return v, "mL"
    return v, "unknown"

def v_usable_v01(raw_v: Any) -> bool:
    v, u = parse_volume_unit(raw_v)
    if v is None or u is None:
        return False
    return u in {"L/kg","mL/kg","L","mL"}

def extract_dailymed_setid(url: str) -> Optional[str]:
    m = re.search(r"setid=([0-9a-fA-F-]{36})", url)
    return m.group(1) if m else None

def extract_pubmed_pmid(url: str) -> Optional[str]:
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url)
    return m.group(1) if m else None

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="all_pk_parameters_combined.csv")
    ap.add_argument("--out", default="jobs_excluded22.yml")
    ap.add_argument("--default-dose-mg", type=float, default=100.0)
    ap.add_argument("--weight-ref-kg", type=float, default=70.0)
    ap.add_argument("--pubmed", action="store_true", help="Force-enable PubMed search even if no PMID is pinned.")
    args = ap.parse_args()

    df = pd.read_csv(args.inp)

    required_cols = {"Drug Name","Half-life","Clearance","Volume of Distribution","Bioavailability","Source URL"}
    missing = required_cols - set(df.columns)
    if missing:
        raise SystemExit(f"CSV missing required columns: {sorted(missing)}")

    excluded: List[Dict[str, Any]] = []
    for _, r in df.iterrows():
        name = str(r["Drug Name"])
        route = infer_route(r["Bioavailability"])
        t_ok = parse_half_life_h(r["Half-life"]) is not None
        cl_ok = cl_usable_v01(r["Clearance"])
        v_ok = v_usable_v01(r["Volume of Distribution"])
        f_ok = True
        if route == "oral":
            f_ok = parse_bioavailability_frac(r["Bioavailability"]) is not None

        selected_v01 = (t_ok and cl_ok and v_ok and f_ok)
        if selected_v01:
            continue

        job: Dict[str, Any] = {
            "name": name,
            "route": route,
            "dose_mg": float(args.default_dose_mg),
            "weight_ref_kg_for_abs": float(args.weight_ref_kg),
            "param_basis": "auto",
            "dailymed": True,
            "pubmed": False,
        }

        src = _norm(r["Source URL"])
        if src:
            sid = extract_dailymed_setid(src)
            pmid = extract_pubmed_pmid(src)
            if sid:
                job["dailymed"] = {"setid": sid}
            if pmid:
                job["pubmed"] = {"pmid": str(pmid)}
            elif args.pubmed:
                job["pubmed"] = True

        excluded.append(job)

    out_path = Path(args.out)
    out_path.write_text(yaml.safe_dump({"jobs": excluded}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Wrote {out_path} with {len(excluded)} jobs (excluded22 v0.1-style)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
