"""Generate pk.yml / targets.yml / spec files in the same schema as v0.3."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

SUBJECT_CSV_REQUIRED_COLUMNS = ["ID", "ARM", "DOSE_MG", "WT", "AGE", "SEX"]
SUBJECT_CSV_OPTIONAL_COLUMNS = ["USUBJID", "STUDYID", "HEIGHT_CM"]


def make_simpop_subject_source(path: str = "subjects.csv") -> Dict[str, Any]:
    """Return an optional external subject-covariate source block.

    This deliberately records simPop as a demographic covariate generator only.
    PK inter-individual variability remains controlled by the model/iiv blocks.
    """
    return {
        "type": "external_csv",
        "path": path,
        "generator": "simPop",
        "required_columns": list(SUBJECT_CSV_REQUIRED_COLUMNS),
        "optional_columns": list(SUBJECT_CSV_OPTIONAL_COLUMNS),
        "notes": [
            "Optional subject-level covariate input. If omitted or unavailable, runners should use population.covariates as the fallback.",
            "simPop is used only to generate demographic covariates; PK IIV remains defined in iiv/model.",
        ],
    }


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"\(.*?\)", "", s)  # remove parenthetical
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "drug"

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def normalize_route(route: str) -> str:
    """Return repository route code: 'po' or 'iv'."""
    r = (route or "").strip().lower()
    if r in {"po", "oral", "p.o.", "per os"} or r.startswith("oral"):
        return "po"
    if r in {"iv", "i.v.", "intravenous"} or r.startswith("iv") or r.startswith("intraven"):
        return "iv"
    raise ValueError(f"Unsupported route: {route!r}; expected oral/po or iv")

def _cl_to_abs(cl: Dict[str, Any], wt_kg: float) -> float:
    if cl["unit"] == "L/h":
        return float(cl["value"])
    if cl["unit"] == "L/h/kg":
        return float(cl["value"]) * wt_kg
    # unknown: assume already L/h
    return float(cl["value"])

def _v_to_abs(v: Dict[str, Any], wt_kg: float) -> float:
    if v["unit"] == "L":
        return float(v["value"])
    if v["unit"] == "L/kg":
        return float(v["value"]) * wt_kg
    return float(v["value"])

def derive_quantities(pk_parsed: Dict[str, Any], wt_kg: float = 70.0) -> Dict[str, Any]:
    notes: List[str] = []
    cl = pk_parsed.get("clearance")
    v = pk_parsed.get("volume")
    f = pk_parsed.get("bioavailability_frac")

    cl_basis = (pk_parsed.get("clearance_basis") or "unknown").lower()
    v_basis = (pk_parsed.get("volume_basis") or "unknown").lower()

    cl_abs = _cl_to_abs(cl, wt_kg) if cl else None
    v_abs = _v_to_abs(v, wt_kg) if v else None

    derived: Dict[str, Any] = {
        "ke_1_per_h": None,
        "CL_abs_L_per_h_at_70kg": cl_abs,
        "V_abs_L_at_70kg": v_abs,
        "CL_apparent_L_per_h_at_70kg": None,
        "V_apparent_L_at_70kg": None,
        "CL_systemic_L_per_h_at_70kg": None,
        "V_systemic_L_at_70kg": None,
        "notes": [],
    }

    if cl_abs and v_abs and v_abs > 0:
        derived["ke_1_per_h"] = cl_abs / v_abs

    # Interpret basis when available
    if cl_abs is not None and v_abs is not None:
        if cl_basis == "apparent" or v_basis == "apparent":
            derived["CL_apparent_L_per_h_at_70kg"] = cl_abs
            derived["V_apparent_L_at_70kg"] = v_abs
            if f is not None:
                # If CL/V are apparent (CL/F, V/F), systemic = apparent * F
                derived["CL_systemic_L_per_h_at_70kg"] = cl_abs * f
                derived["V_systemic_L_at_70kg"] = v_abs * f
                notes.append("Systemic CL/V were derived as (apparent CL/V) * F (assumes values are CL/F, V/F).")
            notes.append("Basis detected/selected: apparent (CL/F, V/F). Model default can use CL_abs/V_abs as apparent and set F1=1.")
        elif cl_basis == "systemic" or v_basis == "systemic":
            derived["CL_systemic_L_per_h_at_70kg"] = cl_abs
            derived["V_systemic_L_at_70kg"] = v_abs
            if f is not None and f > 0:
                derived["CL_apparent_L_per_h_at_70kg"] = cl_abs / f
                derived["V_apparent_L_at_70kg"] = v_abs / f
                notes.append("Apparent CL/V were derived as (systemic CL/V) / F.")
            notes.append("Basis detected/selected: systemic (CL, V). Oral models typically use F1=bioavailability with systemic CL/V.")
        else:
            notes.append("Basis was not confidently determined (systemic vs apparent). Treat CL_abs/V_abs as 'as-extracted' and reconcile with your modeling assumptions.")

    notes.append("Reminder: Oral labels often report apparent parameters (CL/F, V/F). IV labels typically report systemic parameters.")
    derived["notes"] = notes
    return derived

def compute_auc_ng_h_per_ml(dose_mg: float, cl_L_per_h: float) -> float:
    # AUC = Dose/CL in ng*h/mL
    # mg -> ng: *1e6 ; L -> mL: *1000 => factor 1000
    return (dose_mg * 1000.0) / cl_L_per_h

def write_yaml(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True)

def make_pk_yml(
    name: str,
    route_inferred: str,
    sources: List[Dict[str, Any]],
    pk_raw: Dict[str, Any],
    pk_parsed: Dict[str, Any],
    wt_kg: float = 70.0,
) -> Dict[str, Any]:
    pk_parsed = dict(pk_parsed)
    pk_parsed.setdefault("weight_ref_kg_for_abs", wt_kg)
    derived = derive_quantities(pk_parsed, wt_kg)
    return {
        "id": f"OSP_{slugify(name)}",
        "name": name,
        "route_inferred": normalize_route(route_inferred),
        "sources": sources,
        "pk_raw": pk_raw,
        "pk_parsed": pk_parsed,
        "derived": derived,
    }

def make_targets_yml(
    name: str,
    route: str,
    dose_mg: float,
    half_life_h: Optional[float],
    cl_for_auc_L_per_h: float,
) -> Dict[str, Any]:
    route_code = normalize_route(route)
    auc = compute_auc_ng_h_per_ml(dose_mg, cl_for_auc_L_per_h)
    targets = {
        "auc": {
            "type": "AUC0-inf",
            "value": float(auc),
            "unit": "ng*h/mL",
            "summary": "geometric_mean",
            "variability": {"type": "gcv_percent", "value": 35},
        }
    }
    if half_life_h is not None:
        targets["t_half"] = {
            "phase": "terminal",
            "value": float(half_life_h),
            "unit": "h",
            "summary": "arithmetic_mean",
            "variability": {"type": "sd", "value": 1.0},
        }
    return {
        "scenario": {
            "id": f"{slugify(name)}_dose{dose_mg:g}mg_{route_code}_single",
            "route": route_code,
            "regimen": "single",
            "dose": {"value": float(dose_mg), "unit": "mg"},
            "population": {"species": "human", "group": "adult_healthy"},
        },
        "targets": targets,
        "notes": [
            "AUC is computed as Dose/CL using the extracted CL. For oral, this is often apparent CL/F unless you explicitly choose systemic parameters.",
            "Variability fields are placeholders unless you replace them with drug-specific PopPK values.",
        ],
    }

def _default_population(wt_kg: float, subject_source: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    population: Dict[str, Any] = {
        "n": 100,
        "covariates": {
            "wt_kg": {"dist": "lognormal", "median": float(wt_kg), "cv": 0.25, "min": 40, "max": 120}
        },
    }
    if subject_source is not None:
        population["subject_source"] = subject_source
    return population


def make_spec_oral(
    name: str,
    cl_L_per_h: float,
    v_L: float,
    dose_mg: float,
    wt_kg: float = 70.0,
    subject_source: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "version": 0.1,
        "study": {
            "id": f"OSP_{slugify(name)}",
            "title": f"{name} (template from label/PopPK source)",
        },
        "population": _default_population(wt_kg, subject_source),
        "regimen": {
            "route": "oral",
            "units": {"dose": "mg"},
            "arms": {"A": {"n": 100, "dose_mg": float(dose_mg)}},
        },
        "sampling": {"t_end_h": 72.0, "dt_h": 0.5, "include_t0": True},
        "model": {
            "template": "pk1_oral_ode",
            "units": {"conc": "ng/mL", "mult": 1000},
            "theta": {"CL": float(cl_L_per_h), "V": float(v_L), "KA": 1.2, "F1": 1.0, "ALAG1": 0.5},
            "notes": [
                "Default assumes CL and V from sources are apparent (CL/F, V/F). Set theta.F1 to your chosen bioavailability AND adjust CL/V accordingly if your sources report systemic CL/V."
            ],
        },
        "iiv": {"eta": {"CL": 0.09, "V": 0.04, "KA": 0.16}, "corr": False},
        "residual": {"type": "prop+add", "prop": 0.25, "add": 0.0},
        "output": {"include": ["IPRED", "DV", "CP", "AUC"], "format": "csv"},
        "meta": {"generated_by": "tools/template_gen.py"},
    }

def make_spec_iv(
    name: str,
    cl_L_per_h: float,
    v_L: float,
    dose_mg: float,
    wt_kg: float = 70.0,
    subject_source: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "version": 0.1,
        "study": {
            "id": f"OSP_{slugify(name)}",
            "title": f"{name} (template from label/PopPK source)",
        },
        "population": _default_population(wt_kg, subject_source),
        "regimen": {
            "route": "iv",
            "units": {"dose": "mg"},
            "arms": {"A": {"n": 100, "dose_mg": float(dose_mg), "infusion_h": 1.0}},
        },
        "sampling": {"t_end_h": 72.0, "dt_h": 0.5, "include_t0": True},
        "model": {
            "template": "pk1_iv_ode",
            "units": {"conc": "ng/mL", "mult": 1000},
            "theta": {"CL": float(cl_L_per_h), "V": float(v_L)},
        },
        "iiv": {"eta": {"CL": 0.09, "V": 0.04}, "corr": False},
        "residual": {"type": "prop+add", "prop": 0.25, "add": 0.0},
        "output": {"include": ["IPRED", "DV", "CP", "AUC"], "format": "csv"},
        "meta": {"generated_by": "tools/template_gen.py"},
    }

def generate_drug_folder(
    out_root: Path,
    name: str,
    route: str,
    dose_mg: float,
    pk_text: str,
    sources: List[Dict[str, Any]],
    pk_parsed: Dict[str, Any],
    wt_kg: float = 70.0,
    subject_source: Optional[Dict[str, Any]] = None,
) -> Path:
    route_code = normalize_route(route)
    slug = slugify(name)
    ddir = out_root / "drugs" / slug
    _ensure_dir(ddir)

    pk_yml = make_pk_yml(
        name=name,
        route_inferred=route_code,
        sources=sources,
        pk_raw={"text": pk_text[:5000]},
        pk_parsed=pk_parsed,
        wt_kg=wt_kg,
    )
    write_yaml(ddir / "pk.yml", pk_yml)

    # Determine CL/V to use in model (default: apparent for oral)
    derived = pk_yml["derived"]
    cl_L_per_h = derived["CL_abs_L_per_h_at_70kg"]
    v_L = derived["V_abs_L_at_70kg"]
    if cl_L_per_h is None or v_L is None:
        raise ValueError("Cannot generate spec: missing CL or V (even after rescue).")

    if route_code == "po":
        spec = make_spec_oral(name, cl_L_per_h, v_L, dose_mg, wt_kg, subject_source)
        write_yaml(ddir / "spec_pk1_oral.yml", spec)
        targets = make_targets_yml(name, route=route_code, dose_mg=dose_mg, half_life_h=pk_parsed.get("half_life_h"), cl_for_auc_L_per_h=cl_L_per_h)
    else:
        spec = make_spec_iv(name, cl_L_per_h, v_L, dose_mg, wt_kg, subject_source)
        write_yaml(ddir / "spec_pk1_iv.yml", spec)
        targets = make_targets_yml(name, route=route_code, dose_mg=dose_mg, half_life_h=pk_parsed.get("half_life_h"), cl_for_auc_L_per_h=cl_L_per_h)

    write_yaml(ddir / "targets.yml", targets)
    return ddir
