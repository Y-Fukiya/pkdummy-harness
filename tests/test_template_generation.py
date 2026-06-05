from __future__ import annotations

import math
from pathlib import Path

import yaml

from tools.template_gen import generate_drug_folder, normalize_route


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_route_normalization() -> None:
    assert normalize_route("oral") == "po"
    assert normalize_route("po") == "po"
    assert normalize_route("intravenous") == "iv"
    assert normalize_route("iv") == "iv"


def test_generate_oral_folder_uses_repo_route_code(tmp_path: Path) -> None:
    out_dir = generate_drug_folder(
        out_root=tmp_path,
        name="Example Drug",
        route="oral",
        dose_mg=100,
        pk_text="CL/F 10 L/h; V/F 50 L; t1/2 3 h",
        sources=[{"type": "test", "url": "https://example.test/pk"}],
        pk_parsed={
            "clearance": {"value": 10.0, "unit": "L/h"},
            "volume": {"value": 50.0, "unit": "L"},
            "clearance_basis": "apparent",
            "volume_basis": "apparent",
            "half_life_h": 3.0,
            "bioavailability_frac": 0.5,
        },
    )
    assert out_dir.name == "example_drug"
    pk = load_yaml(out_dir / "pk.yml")
    targets = load_yaml(out_dir / "targets.yml")
    spec = load_yaml(out_dir / "spec_pk1_oral.yml")

    assert pk["route_inferred"] == "po"
    assert targets["scenario"]["route"] == "po"
    assert spec["regimen"]["route"] == "oral"
    assert spec["model"]["theta"]["CL"] == 10.0
    assert spec["model"]["theta"]["V"] == 50.0
    assert math.isclose(pk["derived"]["CL_systemic_L_per_h_at_70kg"], 5.0)
