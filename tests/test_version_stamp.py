"""Version single-source + provenance stamping.

tools.__version__ must match pyproject so a fixture's stamped version is
trustworthy, and every validation summary must carry the harness version and the
NCA recalculation method that produced its numbers.
"""

from __future__ import annotations

import re
from pathlib import Path


import tools
from tools.validate_simulation import (
    HARNESS_VERSION,
    NCA_RECALC_METHOD,
    validate_simulation,
)
from tools.run_demo_set import make_demo_sim_full

ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_version_is_single_sourced_from_tools() -> None:
    # pyproject uses a dynamic version sourced from tools.__version__, so there is
    # only one place to bump. Assert the wiring is intact and the value is sane.
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in text
    m = re.search(r'version\s*=\s*\{\s*attr\s*=\s*"([^"]+)"\s*\}', text)
    assert m and m.group(1) == "tools.__version__", "dynamic version must source tools.__version__"
    assert re.match(r"^\d+\.\d+", tools.__version__), tools.__version__


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
