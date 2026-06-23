#!/usr/bin/env python3
"""Regenerate the `derived` block of every pk.yml from pk_parsed, deterministically.

Implements the two maintainer decisions documented in
docs/DERIVED_DRIFT_DECISIONS.md (or the review follow-up):

  Decision 1 (ke convention): canonical ke is CL/V. `derive_quantities` already
  computes ke = CL_abs / V_abs, and validate_library now checks against CL/V, so
  regenerating from pk_parsed yields a library consistent with both the validator
  and the simulator.

  Decision 2 (basis persistence): persist pk_parsed.clearance_basis / volume_basis
  so the derived block is reproducible from pk.yml alone and the basis is explicit.
  Missing values are backfilled with the documented route-auto default
  (oral -> apparent, iv -> systemic). This does NOT mark the basis as human
  verified; validate_library still warns on oral drugs whose source clearance uses
  a systemic-style unit until a maintainer sets clearance_basis_source: confirmed.

Usage:
  python tools/regen_derived.py .            # dry run: print unified diff, write nothing
  python tools/regen_derived.py . --write    # rewrite drugs/*/pk.yml in place
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.template_gen import derive_quantities


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _dump_yaml(obj: Any) -> str:
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True)


def _route_default_basis(route_inferred: Any) -> str:
    r = str(route_inferred or "").strip().lower()
    return "apparent" if r.startswith("po") or r.startswith("oral") else "systemic"


def regenerate_pk_text(pk_path: Path) -> str:
    """Return the regenerated YAML text for one pk.yml (no file write)."""
    pk = _load_yaml(pk_path)
    parsed = pk.get("pk_parsed", {}) or {}

    # Decision 2: persist basis (backfill route-auto default where absent).
    default_basis = _route_default_basis(pk.get("route_inferred"))
    if parsed.get("clearance_basis") in (None, ""):
        parsed["clearance_basis"] = default_basis
    if parsed.get("volume_basis") in (None, ""):
        parsed["volume_basis"] = parsed.get("clearance_basis") or default_basis

    # Decision 1: ke = CL/V is produced by derive_quantities; recompute derived.
    wt = parsed.get("weight_ref_kg_for_abs") or 70.0
    try:
        wt = float(wt)
    except (TypeError, ValueError):
        wt = 70.0
    pk["pk_parsed"] = parsed
    pk["derived"] = derive_quantities(parsed, wt_kg=wt)
    return _dump_yaml(pk)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".", help="library root (contains drugs/)")
    ap.add_argument("--write", action="store_true", help="rewrite pk.yml files in place")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    drugs_dir = root / "drugs"
    changed = 0
    for pk_path in sorted(p / "pk.yml" for p in drugs_dir.glob("*/") if (p / "pk.yml").exists()):
        old = pk_path.read_text(encoding="utf-8")
        new = regenerate_pk_text(pk_path)
        if old == new:
            continue
        changed += 1
        if args.write:
            pk_path.write_text(new, encoding="utf-8")
        else:
            rel = pk_path.relative_to(root)
            diff = difflib.unified_diff(
                old.splitlines(keepends=True), new.splitlines(keepends=True),
                fromfile=f"a/{rel}", tofile=f"b/{rel}",
            )
            sys.stdout.writelines(diff)

    verb = "rewrote" if args.write else "would change"
    print(f"\nregen_derived: {verb} {changed} pk.yml file(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
