"""Read-only, reproducible internal audit. No scientific input files are rewritten.

Run with the repository root as cwd. External source judgments are in group-*.json.
This script checks documented arithmetic and fixture consistency, not PK validity.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LN2 = math.log(2)


def read(path):
    return yaml.safe_load(path.read_text())


def close(left, right):
    return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-12)


def selected_raw(raw, formula):
    if isinstance(raw, (int, float)):
        return float(raw)
    match = re.fullmatch(r"([\d.]+)-([\d.]+)", str(raw))
    if not match:
        return None
    low, high = map(float, match.groups())
    if "lower bound" in formula:
        return low
    if "upper bound" in formula:
        return high
    if any(word in formula for word in ("midpoint", "mean of", " / 2")):
        return (low + high) / 2
    return None  # Deliberate representative selection is not assumed to be a mean.


def expected_value(key, entry, cl, volume, half, weight):
    formula = entry.get("conversion", {}).get("formula", "")
    if "ln(2)" in formula:
        if key == "V_abs_L_at_70kg":
            return cl * half / LN2, "V = CL * t_half / ln(2)"
        if key == "CL_abs_L_per_h_at_70kg":
            return volume * LN2 / half, "CL = V * ln(2) / t_half"
        if key == "t_half_h":
            return LN2 * volume / cl, "t_half = ln(2) * V / CL"
    raw = selected_raw(entry.get("raw_value"), formula)
    if raw is None:
        return None, "Formula not independently evaluated; see manual review"
    unit = entry.get("raw_unit")
    factors = {
        "L/h": 1, "L/min": 60, "mL/min": 60 / 1000,
        "mL/h": 1 / 1000, "mL/day": 1 / 1000 / 24,
        "mL/min/kg": 60 / 1000 * weight,
        "mL/kg/min": 60 / 1000 * weight,
        "L/h/kg": weight,
        # This is a reference-BSA fixture, not an individualized BSA adjustment.
        "mL/min/1.73 m2": 60 / 1000,
        "L": 1, "L/kg": weight, "L/70 kg": 1,
        "h": 1, "min": 1 / 60, "days": 24,
        "percent": 1 / 100, "fraction": 1,
    }
    if unit not in factors:
        return None, "Unit/context requires manual review"
    return raw * factors[unit], f"selected raw {raw:g} * factor {factors[unit]:.15g}"


def leaves(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            if key not in ("notes", "meta", "output", "title"):
                yield from leaves(child, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from leaves(child, f"{path}[{index}]")
    else:
        yield path, value


def main():
    manifest = json.loads((OUT / "input-manifest.json").read_text())
    changed = [item["path"] for item in manifest["files"]
               if hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() != item["sha256"]]
    assert not changed, f"Canonical inputs changed during audit: {changed}"
    records, arithmetic, scalar_rows = [], [], []
    for pk_path in sorted((ROOT / "drugs").glob("*/pk.yml")):
        slug = pk_path.parent.name
        pk = read(pk_path)
        spec_paths = list(pk_path.parent.glob("spec_pk1_*.yml"))
        assert len(spec_paths) == 1, (slug, spec_paths)
        spec = read(spec_paths[0])
        target = read(pk_path.parent / "targets.yml")
        parsed, derived = pk["pk_parsed"], pk["derived"]
        theta = spec["model"]["theta"]
        cl, volume, half = (derived["CL_abs_L_per_h_at_70kg"],
                            derived["V_abs_L_at_70kg"], parsed["half_life_h"])
        weight = parsed.get("weight_ref_kg_for_abs", 70)
        modeled_half = LN2 * theta["V"] / theta["CL"]
        relative_difference = abs(modeled_half - half) / half
        issues = []
        for key, value in (("CL", cl), ("V", volume)):
            if not close(theta[key], value):
                issues.append(f"spec.{key} differs from derived absolute parameter")
        if not close(target["targets"]["t_half"]["value"], half):
            issues.append("target half-life differs from parsed half-life")
        if not close(derived["ke_1_per_h"], cl / volume):
            issues.append("derived ke differs from CL/V")
        f1 = theta.get("F1", 1)
        basis = parsed.get("clearance_basis")
        if spec["regimen"]["route"] in ("oral", "sublingual"):
            expected_f1 = 1 if basis == "apparent" else parsed.get("bioavailability_frac")
            if expected_f1 is None or not close(f1, expected_f1):
                issues.append("F1 does not follow declared basis policy")
        derived_parameters = []
        for key, entry in pk.get("value_provenance", {}).items():
            if key not in ("CL_abs_L_per_h_at_70kg", "V_abs_L_at_70kg", "t_half_h", "bioavailability_frac"):
                continue
            formula = entry.get("conversion", {}).get("formula", "")
            if "ln(2)" in formula:
                derived_parameters.append(key)
            expected, method = expected_value(key, entry, cl, volume, half, weight)
            stored = entry.get("normalized_value")
            status = "NOT_EVALUATED" if expected is None else ("MATCH" if close(stored, expected) else "MISMATCH")
            arithmetic.append(dict(slug=slug, parameter=key, raw_value=entry.get("raw_value"),
                                   raw_unit=entry.get("raw_unit"), stored=stored,
                                   computed=expected, status=status, calculation=method,
                                   documented_formula=formula))
        auc = target["targets"]["auc"]
        arm = spec["regimen"]["arms"]["A"]
        expected_auc = arm["dose_mg"] * f1 / theta["CL"] * 1000
        if not auc.get("independent_literature_target") and not close(auc["value"], expected_auc):
            issues.append("AUC consistency target differs from dose*F1/CL*1000")
        record = dict(
            slug=slug, route=spec["regimen"]["route"], dose_mg=arm["dose_mg"],
            infusion_h=arm.get("infusion_h"), CL_L_h=theta["CL"], V_L=theta["V"],
            clearance_basis=basis, volume_basis=parsed.get("volume_basis"),
            F_reported=parsed.get("bioavailability_frac"), F1_model=f1,
            KA_h_1=theta.get("KA"), ALAG1_h=theta.get("ALAG1"),
            stored_half_h=half, one_compartment_half_h=modeled_half,
            relative_half_difference=relative_difference,
            repository_25_percent_half_warning=relative_difference > .25,
            derived_parameters=derived_parameters,
            half_independent_of_CL_V=not bool(derived_parameters),
            target_claims_half_not_used_to_calibrate=target["targets"]["t_half"].get("used_to_calibrate_cl_v") is False,
            independent_literature_auc=auc.get("independent_literature_target", False),
            stored_auc_ng_h_mL=auc["value"], calculated_auc_ng_h_mL=expected_auc,
            population=target["scenario"].get("population"),
            weight_distribution=spec["population"].get("covariates"),
            sampling=spec["sampling"],
            sampling_end_over_stored_half=spec["sampling"]["t_end_h"] / half,
            iiv=spec["iiv"], residual=spec["residual"],
            target_half_summary=target["targets"]["t_half"].get("summary"),
            target_half_variability=target["targets"]["t_half"].get("variability"),
            target_auc_summary=auc.get("summary"), target_auc_variability=auc.get("variability"),
            internal_mapping_issues=issues,
            clinical_use_status="HOLD: source/context review and drug-specific variability/model validation required",
        )
        records.append(record)
        for origin, data in (("spec", spec), ("targets", target)):
            for path, value in leaves(data):
                scalar_rows.append(dict(slug=slug, origin=origin, path=path, value=value,
                                        review_scope="internal inventory; source judgments in group reports"))
    assert len(records) == manifest["drug_count"] == 37
    summary = dict(
        audit_date="2026-10-02", drug_count=len(records), input_hashes_unchanged=True,
        formula_counts=dict(Counter(item["status"] for item in arithmetic)),
        formula_mismatches=[item for item in arithmetic if item["status"] == "MISMATCH"],
        half_warning_drugs=[r["slug"] for r in records if r["repository_25_percent_half_warning"]],
        CL_V_half_dependency_drugs=[r["slug"] for r in records if r["derived_parameters"]],
        no_independent_auc_count=sum(not r["independent_literature_auc"] for r in records),
        shorter_than_one_stored_half_drugs=[r["slug"] for r in records if r["sampling_end_over_stored_half"] < 1],
        default_dose_100mg_count=sum(r["dose_mg"] == 100 for r in records),
        common_iiv_patterns=dict(Counter(json.dumps(r["iiv"], sort_keys=True) for r in records)),
        common_residual_patterns=dict(Counter(json.dumps(r["residual"], sort_keys=True) for r in records)),
        records=records, arithmetic_checks=arithmetic,
        limitations=["Internal arithmetic matches do not prove source accuracy or clinical validity.",
                     "25% is a repository warning threshold, not a clinical acceptance criterion.",
                     "Unparsed formulas require manual review; no blanket arithmetic pass is claimed.",
                     "Scalar inventory does not establish external validation for any parameter."])
    (OUT / "internal-audit.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    for name, rows in (("all-drug-internal.csv", records), ("arithmetic-checks.csv", arithmetic),
                       ("model-and-target-scalars.csv", scalar_rows)):
        with (OUT / name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                                 for key, value in row.items()})
    print(json.dumps({key: value for key, value in summary.items() if key not in ("records", "arithmetic_checks")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
