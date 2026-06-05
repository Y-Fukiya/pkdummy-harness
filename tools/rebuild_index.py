#!/usr/bin/env python3
"""Rebuild INDEX.csv from drugs/*/pk.yml

Usage:
  python tools/rebuild_index.py /path/to/library

This overwrites INDEX.csv.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Dict

import yaml


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def normalize_route(route: Any) -> str:
    r = str(route or "").strip().lower()
    if r in {"po", "oral", "p.o.", "per os"} or r.startswith("oral"):
        return "po"
    if r in {"iv", "i.v.", "intravenous"} or r.startswith("iv") or r.startswith("intraven"):
        return "iv"
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    drugs_dir = root / "drugs"
    out = root / "INDEX.csv"

    rows = []
    for drug_dir in sorted(drugs_dir.glob("*/")):
        slug = drug_dir.name
        pk = load_yaml(drug_dir / "pk.yml")
        parsed = pk.get("pk_parsed", {}) or {}
        derived = pk.get("derived", {}) or {}
        route = normalize_route(pk.get("route_inferred"))

        spec_file = f"drugs/{slug}/" + ("spec_pk1_oral.yml" if route == "po" else "spec_pk1_iv.yml")
        rows.append({
            "drug": pk.get("name"),
            "slug": slug,
            "route": route,
            "half_life_h": parsed.get("half_life_h"),
            "CL_abs_L_h_at_70kg": derived.get("CL_abs_L_per_h_at_70kg"),
            "V_abs_L_at_70kg": derived.get("V_abs_L_at_70kg"),
            "F": parsed.get("bioavailability_frac"),
            "spec_file": spec_file,
            "pk_file": f"drugs/{slug}/pk.yml",
            "sources_n": len(pk.get("sources", [])),
            "targets_file": f"drugs/{slug}/targets.yml",
        })

    fieldnames = [
        "drug",
        "slug",
        "route",
        "half_life_h",
        "CL_abs_L_h_at_70kg",
        "V_abs_L_at_70kg",
        "F",
        "spec_file",
        "pk_file",
        "sources_n",
        "targets_file",
    ]

    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
