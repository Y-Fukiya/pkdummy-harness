#!/usr/bin/env python3
"""Diagnose drift between committed pk.yml `derived` blocks and the current generator.

Why this exists
---------------
`tools/template_gen.derive_quantities` is supposed to be the single source of the
`derived` block in every `drugs/<slug>/pk.yml`. In practice the committed library
and the current generator have diverged. Crucially they disagree on *conventions*,
not just values, so a blind bulk regeneration would silently change semantics and
can even break `tools/validate_library.py` invariants.

This tool classifies the drift per field and per convention so the maintainer can
make the (unavoidable) design decisions before regenerating. It does NOT modify any
file.

Known convention forks it surfaces:
  * ke_1_per_h: committed uses ke = ln2 / t_half; derive_quantities uses
    ke = CL_abs / V_abs; validate_library *enforces* ke == ln2 / t_half. These
    coincide only when t_half == ln2 * V / CL, which is exactly the case the
    1-compartment attainability warning says is often false.
  * basis keys: committed lacks CL_apparent/V_apparent; the generator adds them.
  * CL_systemic/V_systemic: committed bakes a route-auto basis assumption;
    the generator leaves them None because pk_parsed.clearance_basis is not
    persisted, so the original basis cannot be reproduced from pk.yml alone.

Usage:
  python tools/check_derived_drift.py .                 # human report, exit 0
  python tools/check_derived_drift.py . --out-md report.md
  python tools/check_derived_drift.py . --strict        # exit 1 if any drift
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.template_gen import derive_quantities

_NUMERIC_FIELDS = [
    "ke_1_per_h",
    "CL_abs_L_per_h_at_70kg",
    "V_abs_L_at_70kg",
    "CL_apparent_L_per_h_at_70kg",
    "V_apparent_L_at_70kg",
    "CL_systemic_L_per_h_at_70kg",
    "V_systemic_L_at_70kg",
]


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _num(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _approx(a: Optional[float], b: Optional[float], rel: float = 1e-6) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if b == 0:
        return abs(a - b) <= rel
    return abs(a - b) / abs(b) <= rel


def _ke_convention(committed_ke: Optional[float], t_half: Optional[float],
                   cl_abs: Optional[float], v_abs: Optional[float]) -> str:
    if committed_ke is None:
        return "none"
    by_thalf = math.log(2.0) / t_half if t_half else None
    by_clv = (cl_abs / v_abs) if (cl_abs and v_abs) else None
    hit_thalf = _approx(committed_ke, by_thalf)
    hit_clv = _approx(committed_ke, by_clv)
    if hit_thalf and not hit_clv:
        return "ln2/t_half"
    if hit_clv and not hit_thalf:
        return "CL/V"
    if hit_thalf and hit_clv:
        return "both_coincide"
    return "neither"


def analyze_drug(pk_path: Path) -> Dict[str, Any]:
    pk = _load_yaml(pk_path)
    parsed = pk.get("pk_parsed", {}) or {}
    committed = pk.get("derived", {}) or {}
    wt = _num(parsed.get("weight_ref_kg_for_abs")) or 70.0
    generated = derive_quantities(parsed, wt_kg=wt)

    field_diffs: List[Tuple[str, Optional[float], Optional[float]]] = []
    for field in _NUMERIC_FIELDS:
        c = _num(committed.get(field))
        g = _num(generated.get(field))
        if not _approx(c, g):
            field_diffs.append((field, c, g))

    committed_keys = set(committed.keys()) - {"notes"}
    generated_keys = set(generated.keys()) - {"notes"}

    return {
        "slug": pk_path.parent.name,
        "ke_convention_committed": _ke_convention(
            _num(committed.get("ke_1_per_h")),
            _num(parsed.get("half_life_h")),
            _num(committed.get("CL_abs_L_per_h_at_70kg")),
            _num(committed.get("V_abs_L_at_70kg")),
        ),
        "field_diffs": field_diffs,
        "keys_only_in_generator": sorted(generated_keys - committed_keys),
        "keys_only_in_committed": sorted(committed_keys - generated_keys),
        "basis_persisted": parsed.get("clearance_basis") is not None,
        "has_drift": bool(field_diffs) or bool(generated_keys ^ committed_keys),
    }


def analyze_library(root: Path) -> List[Dict[str, Any]]:
    drugs_dir = root / "drugs"
    out: List[Dict[str, Any]] = []
    for drug_dir in sorted(p for p in drugs_dir.glob("*/") if (p / "pk.yml").exists()):
        out.append(analyze_drug(drug_dir / "pk.yml"))
    return out


def render_report(results: List[Dict[str, Any]]) -> str:
    n = len(results)
    drifted = [r for r in results if r["has_drift"]]
    ke_conv: Dict[str, int] = {}
    for r in results:
        ke_conv[r["ke_convention_committed"]] = ke_conv.get(r["ke_convention_committed"], 0) + 1
    basis_persisted = sum(1 for r in results if r["basis_persisted"])

    lines = [
        "# derived-block drift report",
        "",
        f"- Drugs scanned: {n}",
        f"- Drugs with drift vs current derive_quantities: {len(drifted)}",
        f"- pk_parsed.clearance_basis persisted: {basis_persisted}/{n}",
        "",
        "## ke convention used by committed pk.yml",
        "",
        "| Convention | Drugs |",
        "| --- | ---: |",
    ]
    for k in sorted(ke_conv):
        lines.append(f"| {k} | {ke_conv[k]} |")
    lines += [
        "",
        "`ln2/t_half` is what validate_library.py enforces; `CL/V` is what the current",
        "derive_quantities produces. Where committed uses `ln2/t_half`, regenerating with",
        "the current generator would change ke and FAIL validate_library's ke check.",
        "",
        "## Per-drug drift",
        "",
        "| Drug | ke conv | basis saved | drifted fields | keys+gen | keys+committed |",
        "| --- | --- | :-: | --- | --- | --- |",
    ]
    for r in sorted(results, key=lambda x: x["slug"]):
        fields = ", ".join(f for f, _, _ in r["field_diffs"]) or "-"
        kg = ", ".join(r["keys_only_in_generator"]) or "-"
        kc = ", ".join(r["keys_only_in_committed"]) or "-"
        lines.append(
            f"| {r['slug']} | {r['ke_convention_committed']} | "
            f"{'Y' if r['basis_persisted'] else 'N'} | {fields} | {kg} | {kc} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".", help="library root (contains drugs/)")
    ap.add_argument("--out-md", type=Path, default=None, help="optional markdown report path")
    ap.add_argument("--strict", action="store_true", help="exit 1 if any drift is found")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    results = analyze_library(root)
    report = render_report(results)
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(report, encoding="utf-8")
    print(report)

    drifted = sum(1 for r in results if r["has_drift"])
    if args.strict and drifted:
        print(f"\nderived drift: {drifted} drug(s) drifted (strict mode).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
