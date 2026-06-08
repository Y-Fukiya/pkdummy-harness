#!/usr/bin/env python3
"""Validate OSP PK template library integrity.

Checks:
- Each drug folder has pk.yml, targets.yml, and the correct spec file
- Derived values in pk.yml are internally consistent
- CL/V implied half-life is flagged when it conflicts with the 1-compartment target
- spec theta matches pk.yml (CL/V chosen from derived abs values)
- targets AUC matches Dose/CL rule in targets.yml note
- INDEX.csv is consistent with pk.yml + file paths

Usage:
  python tools/validate_library.py /path/to/osp_pk_templates_v0_2
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def approx(a: float, b: float, tol: float = 1e-8) -> bool:
    return abs(a - b) <= tol


def fail(msg: str, issues: List[str]) -> None:
    issues.append(msg)


def warn(msg: str, warnings: List[str]) -> None:
    warnings.append(msg)


def normalize_route(route: Any) -> str:
    r = str(route or "").strip().lower()
    if r in {"po", "oral", "p.o.", "per os"} or r.startswith("oral"):
        return "po"
    if r in {"iv", "i.v.", "intravenous"} or r.startswith("iv") or r.startswith("intraven"):
        return "iv"
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".", help="library root (folder containing pk_library.yml)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    drugs_dir = root / "drugs"
    index_csv = root / "INDEX.csv"

    if not (root / "pk_library.yml").exists():
        print(f"ERROR: pk_library.yml not found under {root}", file=sys.stderr)
        return 2

    issues: List[str] = []
    warnings: List[str] = []

    # Load INDEX.csv if present
    index_rows: Dict[str, Dict[str, str]] = {}
    if index_csv.exists():
        with index_csv.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                slug = (r.get("slug") or "").strip()
                if slug:
                    index_rows[slug] = r

    # Validate each drug folder
    for drug_dir in sorted(drugs_dir.glob("*/")):
        slug = drug_dir.name
        pk_path = drug_dir / "pk.yml"
        targets_path = drug_dir / "targets.yml"

        if not pk_path.exists():
            fail(f"{slug}: missing pk.yml", issues)
            continue
        if not targets_path.exists():
            fail(f"{slug}: missing targets.yml", issues)
            continue

        pk = load_yaml(pk_path)
        parsed = pk.get("pk_parsed", {}) or {}
        derived = pk.get("derived", {}) or {}
        route = normalize_route(pk.get("route_inferred"))

        # Spec file existence
        spec_name = "spec_pk1_oral.yml" if route == "po" else "spec_pk1_iv.yml"
        spec_path = drug_dir / spec_name
        if not spec_path.exists():
            fail(f"{slug}: missing {spec_name}", issues)
            continue

        # Derived checks
        t_half = parsed.get("half_life_h")
        ke = derived.get("ke_1_per_h")
        if isinstance(t_half, (int, float)) and isinstance(ke, (int, float)):
            exp_ke = math.log(2) / float(t_half)
            if not approx(float(ke), exp_ke, tol=1e-6):
                fail(f"{slug}: ke mismatch (got {ke}, expected {exp_ke})", issues)

        CL_abs = derived.get("CL_abs_L_per_h_at_70kg")
        V_abs = derived.get("V_abs_L_at_70kg")
        CL_sys = derived.get("CL_systemic_L_per_h_at_70kg")
        V_sys = derived.get("V_systemic_L_at_70kg")
        F = parsed.get("bioavailability_frac")

        if (
            isinstance(t_half, (int, float))
            and isinstance(CL_abs, (int, float))
            and isinstance(V_abs, (int, float))
            and float(t_half) > 0
            and float(CL_abs) > 0
            and float(V_abs) > 0
        ):
            implied_t_half = math.log(2.0) * float(V_abs) / float(CL_abs)
            rel_error = abs(implied_t_half - float(t_half)) / abs(float(t_half))
            if rel_error > 0.25:
                warn(
                    f"{slug}: t_half_h {t_half} h conflicts with CL/V implied "
                    f"{implied_t_half:.6g} h (rel_error={rel_error:.3g}; threshold=0.25). "
                    "This target may be unattainable by the 1-compartment fixture without "
                    "choosing a different independent parameter pair.",
                    warnings,
                )

        if route == "po" and isinstance(F, (int, float)):
            if isinstance(CL_abs, (int, float)) and isinstance(CL_sys, (int, float)):
                exp = float(CL_abs) * float(F)
                if not approx(float(CL_sys), exp, tol=1e-6):
                    fail(f"{slug}: CL_systemic mismatch (got {CL_sys}, expected {exp})", issues)
            if isinstance(V_abs, (int, float)) and isinstance(V_sys, (int, float)):
                exp = float(V_abs) * float(F)
                if not approx(float(V_sys), exp, tol=1e-6):
                    fail(f"{slug}: V_systemic mismatch (got {V_sys}, expected {exp})", issues)
        if route == "iv":
            if isinstance(CL_abs, (int, float)) and isinstance(CL_sys, (int, float)):
                if not approx(float(CL_sys), float(CL_abs), tol=1e-9):
                    fail(f"{slug}: IV CL_systemic should equal CL_abs", issues)
            if isinstance(V_abs, (int, float)) and isinstance(V_sys, (int, float)):
                if not approx(float(V_sys), float(V_abs), tol=1e-9):
                    fail(f"{slug}: IV V_systemic should equal V_abs", issues)

        # Spec theta matches (we expect CL/V to be abs values used in template)
        spec = load_yaml(spec_path)
        theta = (((spec.get("model") or {}).get("theta")) or {})
        if isinstance(CL_abs, (int, float)):
            cl = theta.get("CL")
            if isinstance(cl, (int, float)) and not approx(float(cl), float(CL_abs), tol=1e-6):
                fail(f"{slug}: spec theta.CL != derived.CL_abs (got {cl}, expected {CL_abs})", issues)
        if isinstance(V_abs, (int, float)):
            v = theta.get("V")
            if isinstance(v, (int, float)) and not approx(float(v), float(V_abs), tol=1e-6):
                fail(f"{slug}: spec theta.V != derived.V_abs (got {v}, expected {V_abs})", issues)

        # Targets AUC consistency (Dose/CL rule) if targets has auc.value
        targets = load_yaml(targets_path)
        auc = (((targets.get("targets") or {}).get("auc")) or {})
        try:
            auc_value = float(auc.get("value"))
        except Exception:
            auc_value = None
        if auc_value is not None and isinstance(CL_abs, (int, float)):
            # Dose is in targets.scenario.dose.value (mg), and spec uses mult=1000 for ng/mL.
            # In this template family we use: AUC (ng*h/mL) = Dose(mg)*1e6 / CL(L/h)
            # because mg -> ng is 1e6, and L -> mL is 1e3, so 1e6/1e3 = 1e3.
            # Therefore: AUC = Dose(mg) * 1000 / CL(L/h)
            # NOTE: This matches how v0.1 targets were generated.
            dose = (((targets.get("scenario") or {}).get("dose")) or {}).get("value")
            if isinstance(dose, (int, float)):
                exp_auc = float(dose) * 1000.0 / float(CL_abs)
                if not approx(float(auc_value), exp_auc, tol=1e-6):
                    fail(f"{slug}: targets auc mismatch (got {auc_value}, expected {exp_auc})", issues)

        # INDEX.csv consistency (if exists)
        if index_rows:
            r = index_rows.get(slug)
            if not r:
                fail(f"{slug}: missing in INDEX.csv", issues)
            else:
                # Check key fields
                if route and normalize_route(r.get("route")) != route:
                    fail(f"{slug}: INDEX route mismatch (got {r.get('route')}, expected {route})", issues)
                # Files
                for key, rel in [("pk_file", f"drugs/{slug}/pk.yml"),
                                 ("targets_file", f"drugs/{slug}/targets.yml")]:
                    if (r.get(key) or "").strip() != rel:
                        fail(f"{slug}: INDEX {key} mismatch (got {r.get(key)}, expected {rel})", issues)

    # Print summary
    if issues:
        print("Library validation: FAILED")
        for m in issues:
            print("-", m)
        if warnings:
            print("1-compartment attainability warnings:")
            for m in warnings:
                print("-", m)
        return 1
    print("Library validation: OK")
    if warnings:
        print("1-compartment attainability warnings:")
        for m in warnings:
            print("-", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
