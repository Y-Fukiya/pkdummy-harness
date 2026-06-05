from __future__ import annotations

import math

from tools.pk_extract import extract_pk_from_pkrow, extract_pk_from_text


def test_extracts_bsa_normalized_clearance_from_text() -> None:
    text = (
        "Clinical pharmacokinetics: apparent clearance CL/F was "
        "327 mL/min/1.73 m2 and volume of distribution Vd was 0.6 L/kg. "
        "Terminal half-life was 2.5 hours. Absolute bioavailability was 10%."
    )
    pk = extract_pk_from_text(text, route="oral")
    assert pk["clearance"] == {"value": 19.62, "unit": "L/h"}
    assert pk["volume"] == {"value": 0.6, "unit": "L/kg"}
    assert math.isclose(pk["half_life_h"], 2.5)
    assert math.isclose(pk["bioavailability_frac"], 0.1)
    assert pk["clearance_basis"] == "apparent"


def test_extract_pkrow_rescue_handles_compact_table_rows() -> None:
    text = "PKROW: Clearance 5.2 L/hr; PKROW: Vc 35 L; PKROW: Terminal half-life 4 h;"
    pk = extract_pk_from_pkrow(text, route="iv", prefer_basis="systemic")
    assert pk["clearance"] == {"value": 5.2, "unit": "L/h"}
    assert pk["volume"] == {"value": 35.0, "unit": "L"}
    assert pk["half_life_h"] == 4.0
    assert pk["diagnostics"]["pkrow_segments"] == 3
