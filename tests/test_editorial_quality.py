from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.check_parameter_contract import check_source_contract
from tools.simulation_assessment import validate_fixture_context


@pytest.fixture
def context_inputs():
    pk = {"simulation_validity": {"status": "clinical_hold", "reasons": ["The model has not been qualified."]}}
    spec = {"regimen": {"arms": {"A": {"dose_mg": 100}}}}
    targets = {"scenario": {"purpose": "computational_stress_test", "clinical_dose_verified": False, "dose": {"value": 100, "unit": "mg"}}}
    return pk, spec, targets


def test_repeated_reason_is_rejected_even_when_lists_differ(context_inputs):
    pk, spec, targets = context_inputs
    pk["simulation_validity"]["correction_notes"] = ["Another historical change.", "  THE MODEL HAS\nNOT BEEN QUALIFIED!  "]
    issues = validate_fixture_context(pk, spec, targets)
    assert any("reasons" in issue and "correction_notes" in issue and "duplicate" in issue for issue in issues)


@pytest.mark.parametrize("field, value, diagnostic", [
    ("simulation_validity", [], "simulation_validity.status"),
    ("simulation_validity", 42, "simulation_validity.status"),
    ("reasons", 42, "simulation_validity.reasons"),
    ("correction_notes", 42, "simulation_validity.correction_notes"),
])
def test_malformed_editorial_fields_keep_validation_diagnostics(context_inputs, field, value, diagnostic):
    pk, spec, targets = context_inputs
    if field == "simulation_validity":
        pk[field] = value
    else:
        pk["simulation_validity"][field] = value
        pk["simulation_validity"]["source_correction_date"] = "2026-10-28"
    assert any(diagnostic in issue for issue in validate_fixture_context(pk, spec, targets))


@pytest.mark.parametrize("token", [
    "CL3.3", "Vss21", "half-life12", "approximately50%", "section5.2", "F50%",
    "followed7", "over5", "after10", "prior0.615", "elderly61", "young-subject62",
    "retained100", "clearance41", "The4",
])
def test_missing_prose_separator_is_rejected(context_inputs, token):
    pk, spec, targets = context_inputs
    pk["simulation_validity"]["reasons"] = [f"The fixture uses {token} as a summary."]
    issues = validate_fixture_context(pk, spec, targets)
    assert any("simulation_validity.reasons[0]" in issue and "space" in issue and token.rstrip("%") in issue for issue in issues)


def test_spacing_check_covers_authored_prose_fields(context_inputs):
    pk, spec, targets = context_inputs
    pk["simulation_validity"]["correction_notes"] = ["CL3.3 was corrected."]
    pk["pk_parsed"] = {"clearance_basis_note": "CL3.3 is systemic."}
    pk["value_provenance"] = {"CL": {
        "reviewer_note": "CL3.3 is systemic.", "source_locator": "section5.2",
        "selection": {"rule": "recorded_point_value", "rationale": "CL3.3 was selected."},
        "review_update": {"note": "CL3.3 was checked.", "note_en": "CL3.3 was checked."},
    }}
    pk["fixture_limitations"] = [{"statement": "CL3.3 remains a fixture.", "source_locator": "section5.2"}]
    pk["derived"] = {"notes": ["CL3.3 is retained."]}
    issues = validate_fixture_context(pk, spec, targets)
    for path in (
        "simulation_validity.correction_notes[0]", "pk_parsed.clearance_basis_note",
        "value_provenance.CL.reviewer_note", "value_provenance.CL.source_locator",
        "value_provenance.CL.selection.rationale", "value_provenance.CL.review_update.note",
        "value_provenance.CL.review_update.note_en", "fixture_limitations[0].statement",
        "fixture_limitations[0].source_locator", "derived.notes[0]",
    ):
        assert any(path in issue and "space" in issue for issue in issues), path


def test_scientific_identifiers_and_captured_material_are_preserved(context_inputs):
    pk, spec, targets = context_inputs
    pk["simulation_validity"]["reasons"] = [
        "F1, CDA1, V1/V2, m2, t1/2, CYP3, CYP3A4, CYP2D6, CYP3A-mediated, q12, q8, q12h and q8-12h are identifiers.",
        "CL 3.3 L/h is from source_1. See https://example.org/section5.2 and `CL3.3`.",
    ]
    pk["pk_raw"] = {"clearance": "CL3.3"}
    pk["value_provenance"] = {"CL": {
        "exact_quote": "CL3.3", "source_id": "study50", "raw_value": "CL3.3",
        "conversion": {"formula": "CL3.3"},
        "selection": {"rule": "recorded_point_value", "rationale": "An observed estimate."},
    }}
    assert validate_fixture_context(pk, spec, targets) == []


def test_contract_boundary_reports_editorial_errors(tmp_path: Path):
    from tests.test_parameter_contract import make_library

    folder = make_library(tmp_path)
    path = folder / "pk.yml"
    pk = yaml.safe_load(path.read_text(encoding="utf-8"))
    pk["simulation_validity"]["reasons"] = ["CL3.3 remains an approximation."]
    path.write_text(yaml.safe_dump(pk), encoding="utf-8")
    issues = check_source_contract(tmp_path)
    assert any("omeprazole: simulation_validity.reasons[0]" in issue and "space" in issue for issue in issues)
