"""Unit parsing and conversion helpers for PK parameters.

This repo stores:
  - Clearance: L/h OR L/h/kg
  - Volume:    L OR L/kg
  - Half-life: hours
  - F:         fraction (0-1)

We intentionally keep conversions conservative and record any assumptions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

_SPACE_RE = re.compile(r"\s+")
_UNIT_CLEAN = {
    "hr": "h",
    "hrs": "h",
    "hour": "h",
    "hours": "h",
    "min": "min",
    "mins": "min",
    "day": "day",
    "days": "day",
    "l": "L",
    "ml": "mL",
    "kg": "kg",
    "m2": "m2",
    "m²": "m2",
    "1.73m2": "1.73 m2",
    "1.73 m²": "1.73 m2",
}

def _norm_unit(u: str) -> str:
    u = u.strip()
    u = u.replace("·", "/")
    u = u.replace("−", "-").replace("–", "-")
    u = u.replace("^", "")
    u = u.replace("per", "/")
    u = u.replace(" ", "")
    # common synonyms
    for k, v in _UNIT_CLEAN.items():
        u = re.sub(rf"(?i)\b{k}\b", v, u)
    # restore separators for readability
    u = u.replace("L/","L/").replace("mL/","mL/")
    return u

@dataclass
class ParsedQuantity:
    value: float
    unit: str
    notes: List[str]

def convert_clearance(value: float, unit_raw: str, bsa_m2_ref: float = 1.73) -> ParsedQuantity:
    """Convert clearance to L/h or L/h/kg when possible."""
    notes: List[str] = []
    u = _norm_unit(unit_raw)

    # Normalize separators
    u = u.replace("Lh", "L/h").replace("Lhr", "L/h").replace("Lh-1", "L/h")
    u = u.replace("mLmin", "mL/min").replace("mLmin-1", "mL/min")
    u = u.replace("Lmin", "L/min")

    # Remove parentheses etc.
    u = u.strip("()")

    # L/h/kg
    if re.fullmatch(r"(?i)L/(?:h|hr)/kg", u) or re.fullmatch(r"(?i)L/h/kg", u):
        return ParsedQuantity(value=value, unit="L/h/kg", notes=notes)

    if re.fullmatch(r"(?i)mL/min/kg", u):
        # mL/min/kg -> L/h/kg
        v = value * 60.0 / 1000.0
        return ParsedQuantity(value=v, unit="L/h/kg", notes=notes + ["Converted mL/min/kg -> L/h/kg"])

    if re.fullmatch(r"(?i)mL/(?:h|hr)/kg", u) or re.fullmatch(r"(?i)mL/h/kg", u):
        # mL/h/kg -> L/h/kg
        v = value / 1000.0
        return ParsedQuantity(value=v, unit="L/h/kg", notes=notes + ["Converted mL/h/kg -> L/h/kg"])

    # L/h
    if re.fullmatch(r"(?i)L/(?:h|hr)", u) or re.fullmatch(r"(?i)L/h", u):
        return ParsedQuantity(value=value, unit="L/h", notes=notes)

    # L/h/70kg (adult-normalized)
    if re.fullmatch(r"(?i)L/(?:h|hr)/70kg", u) or re.fullmatch(r"(?i)L/h/70kg", u):
        notes.append("Treated clearance normalized to 70kg as adult L/h")
        return ParsedQuantity(value=value, unit="L/h", notes=notes)

    if re.fullmatch(r"(?i)L/(?:h|hr)/1\.73m2", u.replace(" ", "")) or re.fullmatch(r"(?i)L/h/1\.73m2", u.replace(" ", "")):
        notes.append("Treated L/h/1.73m2 as adult-ref clearance; kept as L/h")
        return ParsedQuantity(value=value, unit="L/h", notes=notes)

    if re.fullmatch(r"(?i)mL/(?:h|hr)", u) or re.fullmatch(r"(?i)mL/h", u):
        v = value / 1000.0
        return ParsedQuantity(value=v, unit="L/h", notes=notes + ["Converted mL/h -> L/h"])

    if re.fullmatch(r"(?i)mL/min", u):
        v = value * 60.0 / 1000.0
        return ParsedQuantity(value=v, unit="L/h", notes=notes + ["Converted mL/min -> L/h"])

    if re.fullmatch(r"(?i)mL/min/70kg", u):
        v = value * 60.0 / 1000.0
        notes.append("Treated mL/min/70kg as adult-ref clearance")
        return ParsedQuantity(value=v, unit="L/h", notes=notes)

    if re.fullmatch(r"(?i)mL/(?:h|hr)/70kg", u) or re.fullmatch(r"(?i)mL/h/70kg", u):
        v = value / 1000.0
        notes.append("Treated mL/h/70kg as adult-ref clearance")
        return ParsedQuantity(value=v, unit="L/h", notes=notes)

    if re.fullmatch(r"(?i)L/min", u):
        v = value * 60.0
        return ParsedQuantity(value=v, unit="L/h", notes=notes + ["Converted L/min -> L/h"])

    if re.fullmatch(r"(?i)L/day", u):
        v = value / 24.0
        return ParsedQuantity(value=v, unit="L/h", notes=notes + ["Converted L/day -> L/h"])

    # BSA-normalized
    if re.fullmatch(r"(?i)L/h/m2", u) or re.fullmatch(r"(?i)L/hr/m2", u):
        v = value * bsa_m2_ref
        notes.append(f"Assumed adult BSA {bsa_m2_ref} m2 to convert L/h/m2 -> L/h")
        return ParsedQuantity(value=v, unit="L/h", notes=notes)

    if re.fullmatch(r"(?i)mL/min/1\.73m2", u.replace(" ", "")) or re.fullmatch(r"(?i)mL/min/1\.73m2", u):
        # treat as per 1.73 m2 (i.e., adult ref). Convert to L/h.
        v = value * 60.0 / 1000.0
        notes.append("Treated mL/min/1.73m2 as adult-ref clearance; converted to L/h")
        return ParsedQuantity(value=v, unit="L/h", notes=notes)

    if re.fullmatch(r"(?i)mL/(?:h|hr)/1\.73m2", u.replace(" ", "")):
        v = value / 1000.0
        notes.append("Treated mL/h/1.73m2 as adult-ref clearance; converted to L/h")
        return ParsedQuantity(value=v, unit="L/h", notes=notes)

    # If we can't convert, keep raw
    notes.append(f"Unrecognized clearance unit: {unit_raw}")
    return ParsedQuantity(value=value, unit=unit_raw, notes=notes)

def convert_volume(value: float, unit_raw: str, bsa_m2_ref: float = 1.73) -> ParsedQuantity:
    """Convert volume to L or L/kg when possible."""
    notes: List[str] = []
    u = _norm_unit(unit_raw)
    u = u.strip("()")

    if re.fullmatch(r"(?i)L/kg", u):
        return ParsedQuantity(value=value, unit="L/kg", notes=notes)

    if re.fullmatch(r"(?i)mL/kg", u):
        v = value / 1000.0
        return ParsedQuantity(value=v, unit="L/kg", notes=notes + ["Converted mL/kg -> L/kg"])

    if re.fullmatch(r"(?i)L", u):
        return ParsedQuantity(value=value, unit="L", notes=notes)

    # L/70kg (adult-normalized)
    if re.fullmatch(r"(?i)L/70kg", u):
        notes.append("Treated volume normalized to 70kg as adult L")
        return ParsedQuantity(value=value, unit="L", notes=notes)

    if re.fullmatch(r"(?i)mL", u):
        v = value / 1000.0
        return ParsedQuantity(value=v, unit="L", notes=notes + ["Converted mL -> L"])

    if re.fullmatch(r"(?i)mL/70kg", u):
        v = value / 1000.0
        notes.append("Treated mL/70kg as adult-ref volume")
        return ParsedQuantity(value=v, unit="L", notes=notes)

    if re.fullmatch(r"(?i)L/m2", u):
        v = value * bsa_m2_ref
        notes.append(f"Assumed adult BSA {bsa_m2_ref} m2 to convert L/m2 -> L")
        return ParsedQuantity(value=v, unit="L", notes=notes)

    if re.fullmatch(r"(?i)L/1\.73m2", u.replace(" ", "")):
        notes.append("Treated L/1.73m2 as adult-ref volume; kept as L")
        return ParsedQuantity(value=value, unit="L", notes=notes)

    notes.append(f"Unrecognized volume unit: {unit_raw}")
    return ParsedQuantity(value=value, unit=unit_raw, notes=notes)

def convert_half_life_to_h(value: float, unit_raw: str) -> ParsedQuantity:
    notes: List[str] = []
    u = _norm_unit(unit_raw).lower()
    u = u.strip("()")

    if u in ("h", "hour", "hours") or u == "h":
        return ParsedQuantity(value=value, unit="h", notes=notes)
    if u in ("min",):
        return ParsedQuantity(value=value/60.0, unit="h", notes=notes + ["Converted min -> h"])
    if u in ("day", "days"):
        return ParsedQuantity(value=value*24.0, unit="h", notes=notes + ["Converted day -> h"])

    notes.append(f"Unrecognized half-life unit: {unit_raw}")
    return ParsedQuantity(value=value, unit=unit_raw, notes=notes)
