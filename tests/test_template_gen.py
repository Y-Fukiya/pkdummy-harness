import math

from tools.template_gen import (
    compute_auc_ng_h_per_ml,
    derive_quantities,
    make_simpop_subject_source,
    make_spec_oral,
)


def test_derive_apparent_oral_parameters_to_systemic_with_f():
    derived = derive_quantities(
        {
            "clearance": {"value": 10, "unit": "L/h"},
            "volume": {"value": 100, "unit": "L"},
            "bioavailability_frac": 0.4,
            "clearance_basis": "apparent",
            "volume_basis": "apparent",
        }
    )

    assert math.isclose(derived["CL_abs_L_per_h_at_70kg"], 10.0)
    assert math.isclose(derived["V_abs_L_at_70kg"], 100.0)
    assert math.isclose(derived["CL_systemic_L_per_h_at_70kg"], 4.0)
    assert math.isclose(derived["V_systemic_L_at_70kg"], 40.0)


def test_auc_rule_is_dose_times_1000_over_clearance():
    assert math.isclose(compute_auc_ng_h_per_ml(100, 20), 5000.0)


def test_oral_spec_defaults_to_apparent_parameters_with_f1_one():
    spec = make_spec_oral("Test Drug", cl_L_per_h=10, v_L=100, dose_mg=50)
    theta = spec["model"]["theta"]
    assert theta["CL"] == 10.0
    assert theta["V"] == 100.0
    assert theta["F1"] == 1.0
    assert spec["model"]["template"] == "pk1_oral_ode"


def test_oral_spec_can_reference_optional_simpop_subject_csv():
    subject_source = make_simpop_subject_source(path="subjects/test_drug_subjects.csv")

    spec = make_spec_oral(
        "Test Drug",
        cl_L_per_h=10,
        v_L=100,
        dose_mg=50,
        subject_source=subject_source,
    )

    assert spec["population"]["n"] == 100
    assert spec["population"]["covariates"]["wt_kg"]["dist"] == "lognormal"
    assert spec["population"]["subject_source"] == {
        "type": "external_csv",
        "path": "subjects/test_drug_subjects.csv",
        "generator": "simPop",
        "required_columns": ["ID", "ARM", "DOSE_MG", "WT", "AGE", "SEX"],
        "optional_columns": ["USUBJID", "STUDYID", "HEIGHT_CM"],
        "notes": [
            "Optional subject-level covariate input. If omitted or unavailable, runners should use population.covariates as the fallback.",
            "simPop is used only to generate demographic covariates; PK IIV remains defined in iiv/model.",
        ],
    }
