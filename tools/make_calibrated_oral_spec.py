#!/usr/bin/env python3
"""Generate F-corrected oral profiles for systemic-basis drugs (a separate profile).

Background
----------
For the oral drugs whose basis was corrected to `systemic` (see
docs/BASIS_WORKLIST_RESOLUTION.md), the DEFAULT spec parameterises theta.CL with
the systemic clearance but sets F1 = 1.0, so the simulated exposure is
Dose/CL_systemic -- i.e. it implicitly treats the systemic CL as an apparent
CL/F. That is fine as an internal fixture, but it is inconsistent with the
declared systemic basis.

This tool emits a SEPARATE profile in which the only change is theta.F1 = the
label bioavailability (CL stays the systemic value), so the simulated exposure is
F * Dose / CL_systemic -- consistent with "systemic CL + bioavailability". For a
systemic-basis drug CL_abs == CL_systemic, so no other theta changes are needed.

This is still a TEMPLATE/fixture, not a clinically validated PK model. Profiles
are written under `profiles/` (outside `drugs/`) so they never collide with the
`spec_pk1_*.yml` "exactly one spec per drug" rule used by run_demo_set/run_workflow.

Usage:
  python tools/make_calibrated_oral_spec.py .            # dry-run diff vs committed
  python tools/make_calibrated_oral_spec.py . --write    # (re)write profiles/*.yml
  python tools/make_calibrated_oral_spec.py . --check     # strict drift check (exit 1)
  python tools/make_calibrated_oral_spec.py . --drug aciclovir   # print one to stdout
"""

from __future__ import annotations

import argparse
import copy
import difflib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

PROFILE_DIRNAME = "profiles"


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _dump_yaml(obj: Any) -> str:
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True)


def _normalize_route(route: Any) -> str:
    r = str(route or "").strip().lower()
    return "po" if r.startswith("po") or r.startswith("oral") else r


def calibrated_oral_spec(default_spec: Dict[str, Any], pk: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return an F-corrected copy of an oral spec, or None if not applicable.

    Applicable only to oral, systemic-basis drugs with a known bioavailability.
    The sole parameter change is theta.F1 -> bioavailability_frac.
    """
    parsed = pk.get("pk_parsed", {}) or {}
    if _normalize_route(pk.get("route_inferred")) != "po":
        return None
    if str(parsed.get("clearance_basis") or "").strip().lower() != "systemic":
        return None
    f = parsed.get("bioavailability_frac")
    if not isinstance(f, (int, float)) or not (0 < float(f) <= 1):
        return None

    model = (default_spec.get("model") or {})
    theta = dict(model.get("theta") or {})
    if "F1" not in theta or "CL" not in theta:
        return None

    spec = copy.deepcopy(default_spec)
    spec["model"]["theta"]["F1"] = float(f)
    study = spec.setdefault("study", {})
    study["id"] = f"{study.get('id', 'OSP')}_Fcorrected"
    notes = list(spec["model"].get("notes") or [])
    notes.append(
        "F-corrected profile: theta.F1 set to label bioavailability and theta.CL kept "
        "as the systemic clearance, so simulated exposure is F*Dose/CL_systemic. This is "
        "a parameterization consistent with the systemic basis; it is still a fixture "
        "template, not a clinically validated PK model."
    )
    spec["model"]["notes"] = notes
    meta = spec.setdefault("meta", {})
    meta["profile"] = "oral_systemic_basis_Fcorrected"
    meta["derived_from"] = "drugs/{slug}/spec_pk1_oral.yml"
    return spec


def _profile_path(root: Path, slug: str) -> Path:
    return root / PROFILE_DIRNAME / f"{slug}_oral_systemic_basis.yml"


def _eligible(root: Path) -> List[str]:
    drugs_dir = root / "drugs"
    out: List[str] = []
    for drug_dir in sorted(p for p in drugs_dir.glob("*/") if (p / "pk.yml").exists()):
        slug = drug_dir.name
        default_spec_path = drug_dir / "spec_pk1_oral.yml"
        if not default_spec_path.exists():
            continue
        spec = calibrated_oral_spec(_load_yaml(default_spec_path), _load_yaml(drug_dir / "pk.yml"))
        if spec is not None:
            out.append(slug)
    return out


def generate_text(root: Path, slug: str) -> str:
    drug_dir = root / "drugs" / slug
    spec = calibrated_oral_spec(_load_yaml(drug_dir / "spec_pk1_oral.yml"), _load_yaml(drug_dir / "pk.yml"))
    if spec is None:
        raise ValueError(f"{slug} is not an eligible systemic-basis oral drug")
    text = _dump_yaml(spec)
    return text.replace("drugs/{slug}/spec_pk1_oral.yml", f"drugs/{slug}/spec_pk1_oral.yml")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".", help="library root (contains drugs/)")
    ap.add_argument("--write", action="store_true", help="write profiles/*.yml in place")
    ap.add_argument("--check", action="store_true", help="exit 1 if committed profiles drift")
    ap.add_argument("--drug", default=None, help="print one drug's profile to stdout")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    if args.drug:
        sys.stdout.write(generate_text(root, args.drug))
        return 0

    slugs = _eligible(root)
    changed = 0
    for slug in slugs:
        new = generate_text(root, slug)
        path = _profile_path(root, slug)
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        if old == new:
            continue
        changed += 1
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new, encoding="utf-8")
        elif not args.check:
            rel = path.relative_to(root)
            sys.stdout.writelines(difflib.unified_diff(
                old.splitlines(keepends=True), new.splitlines(keepends=True),
                fromfile=f"a/{rel}", tofile=f"b/{rel}"))

    verb = "wrote" if args.write else "would change"
    print(f"\ncalibrated profiles: {len(slugs)} eligible drug(s); {verb} {changed}.", file=sys.stderr)
    if args.check and changed:
        print("calibrated profiles drift detected (strict mode).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
