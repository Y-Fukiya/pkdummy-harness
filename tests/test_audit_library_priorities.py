from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import yaml

from tools.audit_library_priorities import audit_library


ROOT = Path(__file__).resolve().parents[1]


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def write_drug(
    root: Path,
    slug: str,
    *,
    name: str,
    t_half: float,
    cl: float,
    v: float,
    route: str = "iv",
    sources: list[dict[str, str]] | None = None,
    stress: bool = False,
) -> None:
    drug_dir = root / "drugs" / slug
    notes = [
        "Demo theta policy: CL and V are the independent simulation parameters.",
    ]
    target_notes = [
        "AUC target provenance: computed as Dose/CL from the extracted CL used by this fixture.",
        "Parameter-pair policy: spec theta uses CL and V from pk.yml derived absolute values.",
    ]
    if stress:
        notes.append("Known stress-test label: library validation flags CL/V/t_half structural mismatch.")
        target_notes.append("Known 1-compartment attainability issue: stress-test fixture.")

    write_yaml(
        drug_dir / "pk.yml",
        {
            "id": f"osp::{slug}",
            "name": name,
            "route_inferred": "po" if route == "oral" else route,
            "sources": sources or [],
            "pk_raw": {"half_life": f"{t_half} h", "clearance": f"{cl} L/h", "volume": f"{v} L"},
            "pk_parsed": {
                "half_life_h": t_half,
                "clearance": {"value": cl, "unit": "L/h"},
                "volume": {"value": v, "unit": "L"},
                "bioavailability_frac": 1.0 if route == "iv" else None,
            },
            "derived": {
                "ke_1_per_h": 0.6931471805599453 / t_half,
                "CL_abs_L_per_h_at_70kg": cl,
                "V_abs_L_at_70kg": v,
            },
        },
    )
    write_yaml(
        drug_dir / "targets.yml",
        {
            "scenario": {"dose": {"value": 100.0, "unit": "mg"}},
            "targets": {"auc": {"value": 1000.0 / cl, "unit": "ng*h/mL"}, "t_half": {"value": t_half, "unit": "h"}},
            "notes": target_notes,
        },
    )
    spec_name = "spec_pk1_oral.yml" if route == "oral" else "spec_pk1_iv.yml"
    write_yaml(
        drug_dir / spec_name,
        {
            "study": {"id": f"OSP_{slug}", "title": name},
            "regimen": {"route": route, "arms": {"A": {"n": 1, "dose_mg": 100}}},
            "model": {"theta": {"CL": cl, "V": v}, "notes": notes},
        },
    )


def test_audit_library_priorities_uses_tiered_priority_and_stress_escape(tmp_path: Path) -> None:
    write_drug(tmp_path, "bad_identity", name="Bad Identity", t_half=1.0, cl=1.0, v=100.0, sources=[{"url": "x"}])
    write_drug(tmp_path, "thin_provenance", name="Thin Provenance", t_half=69.31471805599453, cl=1.0, v=100.0)
    write_drug(tmp_path, "stress_identity", name="Stress Identity", t_half=1.0, cl=1.0, v=100.0, stress=True)

    rows = {row["slug"]: row for row in audit_library(tmp_path)}

    assert rows["bad_identity"]["overall_internal_priority"] == "P0_CORRECTNESS"
    assert rows["thin_provenance"]["overall_internal_priority"] == "P2_PROVENANCE"
    assert rows["stress_identity"]["overall_internal_priority"] == "STRESS_FIXTURE"
    assert rows["bad_identity"]["target_independence_status"] == "HAS_GENERATIVE_DERIVED_TARGETS"


def test_audit_library_priorities_uses_local_snapshots_only(tmp_path: Path) -> None:
    write_drug(tmp_path, "sample_drug", name="Sample Drug", t_half=69.31471805599453, cl=1.0, v=100.0, sources=[{"url": "x"}])
    snapshot_dir = tmp_path / "external_sources" / "snapshots"
    snapshot_dir.mkdir(parents=True)
    with (snapshot_dir / "osp_model_index.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "evaluation_report_url"])
        writer.writeheader()
        writer.writerow({"name": "Sample Drug", "evaluation_report_url": "https://example.test/report.pdf"})
    with (snapshot_dir / "pkdb_substance_index.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["substance_name"])
        writer.writeheader()
        writer.writerow({"substance_name": "Sample Drug"})
        writer.writerow({"substance_name": "Sample Drug"})

    rows = audit_library(
        tmp_path,
        osp_snapshot=snapshot_dir / "osp_model_index.csv",
        pkdb_snapshot=snapshot_dir / "pkdb_substance_index.csv",
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["osp_model_match"] == "yes"
    assert row["osp_evaluation_report"] == "yes"
    assert row["pkdb_exact_hit_count"] == "2"
    assert row["pkdb_role"] == "sampling/profile reference only"


def test_audit_library_priorities_cli_writes_csv_and_markdown(tmp_path: Path) -> None:
    out_dir = tmp_path / "audit"
    completed = subprocess.run(
        [sys.executable, "tools/audit_library_priorities.py", ".", "--out-dir", str(out_dir)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Library priority audit: OK" in completed.stdout
    assert (out_dir / "library_priority_audit.csv").exists()
    assert (out_dir / "library_priority_audit.md").exists()
    rows = list(csv.DictReader((out_dir / "library_priority_audit.csv").open(encoding="utf-8", newline="")))
    assert len(rows) == 37
    assert "overall_internal_priority" in rows[0]
