#!/usr/bin/env python3
"""Create a jobs.yml from EXCLUDED.csv.

EXCLUDED.csv columns (v0.3/v0.4): drug, reason, ...

Example:
  python tools/make_jobs_from_excluded.py --excluded EXCLUDED.csv --out jobs_excluded.yml --route oral
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import yaml

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--excluded", type=str, default="EXCLUDED.csv")
    ap.add_argument("--out", type=str, default="jobs_excluded.yml")
    ap.add_argument("--route", type=str, default="oral", choices=["oral","iv"])
    ap.add_argument("--dose-mg", type=float, default=100.0)
    ap.add_argument("--weight-ref-kg", type=float, default=70.0)
    ap.add_argument("--pubmed", action="store_true", help="Also enable pubmed for each job")
    args = ap.parse_args()

    df = pd.read_csv(args.excluded)
    if "drug" not in df.columns:
        raise SystemExit("EXCLUDED.csv must contain a 'drug' column.")
    jobs: List[Dict[str, Any]] = []
    for d in df["drug"].dropna().unique().tolist():
        jobs.append({
            "name": str(d),
            "route": args.route,
            "dose_mg": float(args.dose_mg),
            "weight_ref_kg_for_abs": float(args.weight_ref_kg),
            "dailymed": True,
            "pubmed": bool(args.pubmed),
        })

    Path(args.out).write_text(yaml.safe_dump({"jobs": jobs}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(f"Wrote {args.out} with {len(jobs)} jobs")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
