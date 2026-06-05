#!/usr/bin/env python3
"""Check that INDEX.csv is reproducible from drugs/*/pk.yml.

This is the offline, deterministic regeneration check. It reconstructs the
expected INDEX.csv content in memory using the same schema as
`tools/rebuild_index.py` and compares it with the checked-in file. It does not
run live DailyMed/PubMed harvesting.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import io
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml


FIELDNAMES = [
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


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_index_text(root: Path) -> str:
    drugs_dir = root / "drugs"
    rows: List[Dict[str, Any]] = []
    for drug_dir in sorted(drugs_dir.glob("*/")):
        slug = drug_dir.name
        pk = load_yaml(drug_dir / "pk.yml")
        parsed = pk.get("pk_parsed", {}) or {}
        derived = pk.get("derived", {}) or {}
        route = pk.get("route_inferred")

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

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="library root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    original_index = root / "INDEX.csv"
    if not original_index.exists():
        print(f"ERROR: INDEX.csv not found under {root}", file=sys.stderr)
        return 2

    current = original_index.read_text(encoding="utf-8")
    expected = build_index_text(root)

    if current != expected:
        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile=str(original_index),
            tofile="regenerated INDEX.csv",
        )
        print("INDEX.csv drift detected after regeneration:", file=sys.stderr)
        print("".join(diff), file=sys.stderr)
        return 1

    print("Regeneration check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
