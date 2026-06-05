from __future__ import annotations

import math

from tools.pk_units import convert_clearance, convert_half_life_to_h, convert_volume


def test_bsa_normalized_clearance_does_not_average_denominator() -> None:
    q = convert_clearance(327, "mL/min/1.73 m2")
    assert q.unit == "L/h"
    assert math.isclose(q.value, 19.62, rel_tol=0, abs_tol=1e-12)
    assert any("1.73" in note for note in q.notes)


def test_clearance_milliliter_per_hour_per_kg() -> None:
    q = convert_clearance(12.5, "mL/hr/kg")
    assert q.unit == "L/h/kg"
    assert math.isclose(q.value, 0.0125, rel_tol=0, abs_tol=1e-12)


def test_clearance_l_per_hour_per_1_73m2_is_adult_ref() -> None:
    q = convert_clearance(4.2, "L/hr/1.73 m2")
    assert q.unit == "L/h"
    assert math.isclose(q.value, 4.2, rel_tol=0, abs_tol=1e-12)


def test_volume_bsa_and_per_kg_conversions() -> None:
    assert math.isclose(convert_volume(2, "L/m2").value, 3.46, rel_tol=0, abs_tol=1e-12)
    q = convert_volume(600, "mL/kg")
    assert q.unit == "L/kg"
    assert math.isclose(q.value, 0.6, rel_tol=0, abs_tol=1e-12)


def test_half_life_days_to_hours() -> None:
    q = convert_half_life_to_h(2, "days")
    assert q.unit == "h"
    assert q.value == 48
