#!/usr/bin/env python3
"""Check executable PK inputs and published projections without changing them.

These checks establish reproducibility and declared arithmetic, not clinical
validity or independent confirmation of the source literature.
Only finite scalar conversions with supported units are evaluated. Ranges and
source-specific formulas remain subject to source review.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import yaml

try:
    from simulation_assessment import validate_fixture_context
    from regen_check import build_index_text
    from template_gen import derive_quantities, normalize_route
except ModuleNotFoundError:  # supports package imports in tests
    from tools.simulation_assessment import validate_fixture_context
    from tools.regen_check import build_index_text
    from tools.template_gen import derive_quantities, normalize_route


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _equal(actual: Any, expected: Any) -> bool:
    a, b = _number(actual), _number(expected)
    return a is not None and b is not None and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


def _converted_value(entry: dict[str, Any], weight: float) -> float | None:
    raw = _number(entry.get("raw_value"))
    if raw is None:
        return None
    conversion = entry.get("conversion") or {}
    if conversion.get("method") not in {"direct", "unit_conversion", "body_weight_scaled"}:
        return None
    source = str(entry.get("raw_unit") or "").strip().lower().replace(" ", "")
    destination = str(entry.get("normalized_unit") or "").strip().lower().replace(" ", "")
    factors = {
        ("ml/min", "l/h"): 60 / 1000,
        ("l/min", "l/h"): 60,
        ("ml/h", "l/h"): 1 / 1000,
        ("ml/day", "l/h"): 1 / 1000 / 24,
        ("l/day", "l/h"): 1 / 24,
        ("ml/min/kg", "l/h"): 60 / 1000 * weight,
        ("ml/h/kg", "l/h"): weight / 1000,
        ("l/h/kg", "l/h"): weight,
        ("l/kg", "l"): weight,
        ("ml/kg", "l"): weight / 1000,
        ("ml", "l"): 1 / 1000,
    }
    if source == destination and source:
        return raw
    factor = factors.get((source, destination))
    return raw * factor if factor is not None else None


def check_source_contract(root: Path) -> list[str]:
    """Validate one canonical PK/spec/target triplet per drug and scalar conversions."""
    issues: list[str] = []
    paths = sorted((root / "drugs").glob("*/pk.yml"))
    if not paths:
        return ["drugs: no canonical pk.yml inputs found"]
    for path in paths:
        slug = path.parent.name
        pk = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        parsed, derived = pk.get("pk_parsed") or {}, pk.get("derived") or {}
        try:
            route = normalize_route(pk.get("route_inferred"))
        except ValueError as exc:
            issues.append(f"{slug}: {exc}")
            continue
        specs = sorted(path.parent.glob("spec_pk1_*.yml"))
        expected_name = "spec_pk1_oral.yml" if route in {"po", "sl"} else "spec_pk1_iv.yml"
        if len(specs) != 1 or specs[0].name != expected_name:
            issues.append(f"{slug}: expected exactly one {expected_name}")
            continue
        target_path = path.parent / "targets.yml"
        if not target_path.is_file():
            issues.append(f"{slug}: missing targets.yml")
            continue
        spec = yaml.safe_load(specs[0].read_text(encoding="utf-8")) or {}
        targets = yaml.safe_load(target_path.read_text(encoding="utf-8")) or {}
        issues.extend(f"{slug}: {issue}" for issue in validate_fixture_context(pk, spec, targets))
        for field, value in (
            ("regimen.route", (spec.get("regimen") or {}).get("route")),
            ("scenario.route", (targets.get("scenario") or {}).get("route")),
        ):
            try:
                matching = normalize_route(value) == route
            except ValueError:
                matching = False
            if not matching:
                issues.append(f"{slug}: {field} disagrees with route_inferred={route}")
        theta = ((spec.get("model") or {}).get("theta") or {})
        for parameter, key in (("CL", "CL_abs_L_per_h_at_70kg"), ("V", "V_abs_L_at_70kg")):
            value = _number(derived.get(key))
            if value is None or value <= 0:
                issues.append(f"{slug}: derived.{key} must be a finite positive number")
            elif not _equal(theta.get(parameter), value):
                issues.append(f"{slug}: model.theta.{parameter} is {theta.get(parameter)}, expected {value}")
        if route in {"po", "sl"}:
            basis = parsed.get("clearance_basis")
            if parsed.get("volume_basis") != basis:
                issues.append(f"{slug}: oral CL and V basis differ; mixed parameterization is unsupported")
            fraction = _number(parsed.get("bioavailability_frac"))
            if basis not in {"systemic", "apparent"}:
                issues.append(f"{slug}: oral clearance_basis must be explicit systemic or apparent")
            elif basis == "systemic" and (fraction is None or not 0 < fraction <= 1):
                issues.append(f"{slug}: systemic oral bioavailability_frac must be in (0, 1]")
            else:
                expected_f1 = fraction if basis == "systemic" else 1.0
                if not _equal(theta.get("F1"), expected_f1):
                    issues.append(f"{slug}: model.theta.F1 is {theta.get('F1')}, expected {expected_f1} for {basis} basis")
        weight = _number(parsed.get("weight_ref_kg_for_abs")) or 70.0
        try:
            expected_derived = derive_quantities(parsed, wt_kg=weight)
        except (KeyError, TypeError, ValueError) as exc:
            issues.append(f"{slug}: cannot derive canonical PK quantities: {exc}")
            continue
        for key, value in expected_derived.items():
            if key != "notes" and value is not None and not _equal(derived.get(key), value):
                issues.append(f"{slug}: derived.{key} is {derived.get(key)}, expected {value}")
        selected_values = {
            "CL_abs_L_per_h_at_70kg": derived.get("CL_abs_L_per_h_at_70kg"),
            "V_abs_L_at_70kg": derived.get("V_abs_L_at_70kg"),
            "t_half_h": parsed.get("half_life_h"),
            "bioavailability_frac": parsed.get("bioavailability_frac"),
        }
        for field, entry in (pk.get("value_provenance") or {}).items():
            if not isinstance(entry, dict):
                continue
            if field in selected_values and not _equal(entry.get("normalized_value"), selected_values[field]):
                issues.append(
                    f"{slug}: value_provenance.{field} normalized_value is {entry.get('normalized_value')}, "
                    f"but the selected canonical value is {selected_values[field]}"
                )
            expected = _converted_value(entry, weight)
            if expected is not None and not _equal(entry.get("normalized_value"), expected):
                issues.append(f"{slug}: value_provenance.{field} conversion is {entry.get('normalized_value')}, expected {expected}")
    return issues


def check_contract(root: Path, *, check_atlas: bool = True) -> list[str]:
    issues = check_source_contract(root)
    index = root / "INDEX.csv"
    if not index.is_file() or index.read_text(encoding="utf-8") != build_index_text(root):
        issues.append("INDEX.csv differs from canonical drug inputs; run tools/rebuild_index.py")
    if check_atlas and not issues:
        try:
            from build_docs_site import build_bundle
        except ModuleNotFoundError:
            from tools.build_docs_site import build_bundle
        atlas = root / "site" / "app" / "drugs.json"
        if not atlas.is_file() or json.loads(atlas.read_text(encoding="utf-8")) != build_bundle(root):
            issues.append("site/app/drugs.json differs from canonical inputs; run tools/build_docs_site.py")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--source-only", action="store_true", help="Check canonical inputs and INDEX before regenerating the atlas.")
    args = parser.parse_args()
    try:
        issues = check_contract(args.root.resolve(), check_atlas=not args.source_only)
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        print(f"Parameter contract check: FAILED\n- {exc}")
        return 1
    if issues:
        print("Parameter contract check: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Parameter contract check: OK (reproducibility, not clinical validation)")
    print("Range-valued and unsupported-unit conversions were not evaluated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
