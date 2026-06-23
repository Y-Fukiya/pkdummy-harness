"""Version single-source + provenance stamping.

tools.__version__ must match pyproject so a fixture's stamped version is
trustworthy, and every validation summary must carry the harness version and the
NCA recalculation method that produced its numbers.
"""

from __future__ import annotations

import re
from pathlib import Path

import math
import yaml

import tools
from tools.validate_simulation import (
    HARNESS_VERSION,
    NCA_RECALC_METHOD,
    read_csv_rows,
    validate_simulation,
)
from tools.run_demo_set import make_demo_sim_full

ROOT = Path(__file__).resolve().parents[1]


def test_tools_version_matches_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    assert m, "version not found in pyproject.toml"
    assert tools.__version__ == m.group(1)


def test_validation_summary_is_self_describing(tmp_path: Path) -> None:
    spec = ROOT / "drugs" / "albuterol" / "spec_pk1_iv.yml"
    sim = tmp_path / "sim.csv"
    make_demo_sim_full(spec_yml=spec, out_csv=sim,
                       variability={"iiv_cv": 0.0, "residual_cv": 0.0, "seed": 1})
    result = validate_simulation(
        sim, ROOT / "drugs/albuterol/pk.yml", ROOT / "drugs/albuterol/targets.yml"
    )
    assert result.summary["harness_version"] == HARNESS_VERSION
    assert result.summary["nca_recalc_method"] == NCA_RECALC_METHOD
    assert "linear_trapezoid" in result.summary["nca_recalc_method"]
