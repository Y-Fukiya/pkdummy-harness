from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml

from tools.build_docs_site import build_drug
from tools.check_parameter_contract import check_source_contract
from tools.template_gen import make_pk_yml, make_targets_yml

ROOT = Path(__file__).resolve().parents[1]


def test_every_canonical_drug_declares_clinical_assessment():
    missing = []
    for path in (ROOT / "drugs").glob("*/pk.yml"):
        pk = yaml.safe_load(path.read_text(encoding="utf-8"))
        if (pk.get("simulation_validity") or {}).get("status") not in {"not_assessed", "clinical_hold"}:
            missing.append(path.parent.name)
    assert missing == []


def test_public_projection_separates_screening_from_manual_status():
    drug = build_drug(ROOT / "drugs/abciximab/pk.yml")
    assert drug["simulation_validity"]["status"] == "not_assessed"
    screening = drug["fixture_assessment"]["half_life_check"]
    assert screening["evaluated"] is True
    assert screening["hold_candidate"] is True
    assert screening["ratio"] == pytest.approx(15.271964109386333)
    assert drug["fixture_assessment"]["dose_context"]["clinical_dose_verified"] is False
    assert drug["fixture_assessment"]["dose_context"]["arms"]["A"]["dose_mg"] == 100


def test_contract_rejects_missing_or_unknown_assessment(tmp_path):
    from tests.test_parameter_contract import make_library

    folder = make_library(tmp_path)
    path = folder / "pk.yml"
    pk = yaml.safe_load(path.read_text(encoding="utf-8"))
    pk.pop("simulation_validity", None)
    path.write_text(yaml.safe_dump(pk), encoding="utf-8")
    assert any("simulation_validity.status" in issue for issue in check_source_contract(tmp_path))
    pk["simulation_validity"] = {"status": "approved", "reasons": []}
    path.write_text(yaml.safe_dump(pk), encoding="utf-8")
    assert any("simulation_validity.status" in issue for issue in check_source_contract(tmp_path))
