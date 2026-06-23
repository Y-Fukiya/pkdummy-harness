"""Extract PK parameters from free text (label/paper).

This module uses conservative regex heuristics. It aims to pull a *single*
representative CL and V value, plus optional half-life and bioavailability.
It also returns evidence snippets so you can audit what was extracted.

Notes:
  - Full-text tables may be messy when converted to text.
  - For PubMed abstracts, CL/V may be absent even if present in the paper.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

from .pk_units import (
    convert_clearance,
    convert_volume,
    convert_half_life_to_h,
)

_WS = re.compile(r"\s+")
_DASH = re.compile(r"[\u2010\u2011\u2012\u2013\u2212]")  # hyphen variants
_SECTION_H = re.compile(r"(?m)^\s*##\s*(.+?)\s*$")

def normalize_text(text: str) -> str:
    # Preserve markdown section headings as tokens so scoring can prefer PK sections.
    text = _SECTION_H.sub(lambda m: f" SECTION[{m.group(1)}] ", text)
    text = _DASH.sub("-", text)
    text = text.replace("\u00b7", "/")  # middle dot
    text = text.replace("\u00d7", "x")
    text = text.replace("\xa0", " ")
    text = _WS.sub(" ", text)
    return text.strip()

# numeric patterns
NUM = r"(?:\d+(?:\.\d+)?|\d*\.\d+)(?:e[-+]?\d+)?"
RANGE = rf"(?P<lo>{NUM})\s*(?:-|to)\s*(?P<hi>{NUM})"
PM = rf"(?P<mean>{NUM})\s*(?:\u00b1|\+/-)\s*(?P<sd>{NUM})"

# unit patterns (CL)
#
# IMPORTANT: Many sources write "hr" instead of "h" (e.g., L/hr, mL/hr/kg).
# Our regex extractor must match these forms *before* unit normalization.
CL_UNIT = r"(?:mL\s*/\s*min\s*/\s*kg|mL\s*/\s*min\s*/\s*70\s*kg|mL\s*/\s*min\s*/\s*1\.\s*73\s*m\s*2|mL\s*/\s*min\s*/\s*m\s*2|mL\s*/\s*min|mL\s*/\s*(?:h|hr)\s*/\s*70\s*kg|mL\s*/\s*(?:h|hr)\s*/\s*kg|mL\s*/\s*(?:h|hr)|L\s*/\s*(?:h|hr)\s*/\s*kg|L\s*/\s*(?:h|hr)\s*/\s*70\s*kg|L\s*/\s*(?:h|hr)\s*/\s*m\s*2|L\s*/\s*(?:h|hr)\s*/\s*1\.\s*73\s*m\s*2|L\s*/\s*(?:h|hr)|L\s*/\s*min|L\s*/\s*day)"
V_UNIT  = r"(?:mL\s*/\s*kg|mL\s*/\s*70\s*kg|L\s*/\s*kg|L\s*/\s*70\s*kg|L\s*/\s*1\.\s*73\s*m\s*2|L\s*/\s*m\s*2|mL(?!\s*/)|L(?!\s*/))"

# keyword patterns
CL_KW = r"(?:\bclearance\b|\bcl\b|\bcl\/f\b|\bapparent\s+clearance\b|\bsystemic\s+clearance\b|\btotal\s+clearance\b)"
V_KW  = r"(?:\bvolume\s+of\s+distribution\b|\bvd\b|\bv\b|\bv\/f\b|\bapparent\s+volume\s+of\s+distribution\b|\bvss\b|\bvdss\b)"
T12_KW = r"(?:half-?life|t\s*1\s*/\s*2|t½)"
F_KW = r"(?:bioavailability|\bF\b)"

@dataclass
class Evidence:
    param: str
    value_raw: str
    context: str

def _pick_value(value_str: str) -> float:
    """Pick a representative value from a matched numeric expression."""
    m = re.search(PM, value_str, flags=re.I)
    if m:
        return float(m.group("mean"))
    m = re.search(RANGE, value_str, flags=re.I)
    if m:
        lo = float(m.group("lo"))
        hi = float(m.group("hi"))
        return (lo + hi) / 2.0
    # fallback: first number
    m = re.search(NUM, value_str, flags=re.I)
    if not m:
        raise ValueError(f"no number in: {value_str}")
    return float(m.group(0))

@dataclass
class Candidate:
    value: float
    unit_raw: str
    context: str
    kw: str
    basis: str  # 'systemic' | 'apparent' | 'unknown'
    distance: int
    pos: int


def _extract_pkrow_segments(text: str) -> List[str]:
    """Return list of "PKROW:" segments (rendered table rows) from text."""
    segs: List[str] = []
    for m in re.finditer(r"PKROW:\s*([^;\n]{1,240})", text, flags=re.I):
        s = (m.group(1) or "").strip()
        if s:
            segs.append(s)
    return segs


def _parse_pkrow_segments(text: str, *, route: str = "oral", prefer_basis: str = "auto") -> Dict[str, Any]:
    """Extract CL/V from 'PKROW:' segments.

    This is a *fallback* path designed to handle SPL tables where our keyword-window
    candidate finder misses values due to formatting. We parse lines like:

      PKROW: Clearance 5.2 L/hr
      PKROW: Vc 35 L

    We intentionally accept more label variants (Vc, V1, central volume).
    """
    segs = _extract_pkrow_segments(text)
    if not segs:
        return {
            "clearance": None,
            "volume": None,
            "clearance_basis": None,
            "volume_basis": None,
            "half_life_h": None,
            "bioavailability_frac": None,
            "evidence": [],
            "notes": [],
            "diagnostics": {"pkrow_segments": 0},
        }

    # Broad unit capture: stop at segment end.
    _UNIT_TAIL = r"(?:L|mL)\s*/\s*(?:h|hr|min|day)(?:\s*/\s*(?:kg|70\s*kg|m\s*2|1\.\s*73\s*m\s*2))?|(?:L|mL)(?:\s*/\s*(?:kg|70\s*kg|m\s*2|1\.\s*73\s*m\s*2))?|%|percent"
    pat = re.compile(rf"^(?P<label>[^\d]{{1,80}}?)\s+(?P<numexpr>{PM}|{RANGE}|{NUM})\s*(?P<unit>{_UNIT_TAIL})?\s*$", flags=re.I)

    cl_cands: List[Candidate] = []
    v_cands: List[Candidate] = []
    ev: List[Dict[str, str]] = []
    notes: List[str] = []

    def _label_basis(kind: str, label: str, ctx: str) -> str:
        return _infer_basis(kind, label, ctx)

    for i, seg in enumerate(segs[:400]):
        m = pat.match(seg)
        if not m:
            continue
        label = (m.group("label") or "").strip()
        numexpr = (m.group("numexpr") or "").strip()
        unit_raw = (m.group("unit") or "").strip()
        try:
            val = _pick_value(numexpr)
        except Exception:
            continue

        lab_l = label.lower()
        ctx = f"PKROW[{i}]: {seg}"[:400]

        # Clearance label heuristics
        if any(k in lab_l for k in ["clearance", " cl", "cl/", "cl ", "total cl", "systemic cl", "oral clearance", "clt", "cltot"]):
            basis = _label_basis("clearance", label, ctx)
            cl_cands.append(Candidate(value=val, unit_raw=unit_raw or "", context=ctx, kw=label, basis=basis, distance=0, pos=i))
            ev.append({"param": "clearance", "value_raw": f"{val} {unit_raw}".strip(), "context": ctx})
            continue

        # Volume label heuristics
        if any(k in lab_l for k in ["volume", "vd", "vss", "vdss", "v/f", " v1", "v1 ", " vc", "vc ", "central volume", "peripheral volume", "v2", "vp"]):
            basis = _label_basis("volume", label, ctx)
            v_cands.append(Candidate(value=val, unit_raw=unit_raw or "", context=ctx, kw=label, basis=basis, distance=0, pos=i))
            ev.append({"param": "volume", "value_raw": f"{val} {unit_raw}".strip(), "context": ctx})
            continue

        # Half-life label heuristics
        if any(k in lab_l for k in ["half-life", "t1/2", "t 1/2", "t½"]):
            # unit_raw could be h/hr/day/min
            if unit_raw:
                pq = convert_half_life_to_h(val, unit_raw)
                notes.extend(pq.notes)
                # Store only first for now
                return {
                    "clearance": None,
                    "volume": None,
                    "clearance_basis": None,
                    "volume_basis": None,
                    "half_life_h": pq.value if pq.unit == "h" else None,
                    "bioavailability_frac": None,
                    "evidence": ev[:6],
                    "notes": notes,
                    "diagnostics": {"pkrow_segments": len(segs), "pkrow_matched": i + 1},
                }

    out: Dict[str, Any] = {
        "clearance": None,
        "volume": None,
        "clearance_basis": None,
        "volume_basis": None,
        "half_life_h": None,
        "bioavailability_frac": None,
        "evidence": [],
        "notes": [],
        "diagnostics": {"pkrow_segments": len(segs)},
    }

    if cl_cands:
        cl = _best(cl_cands, kind="clearance", text_len=len(text), route=route, prefer_basis=prefer_basis)
        pq = convert_clearance(cl.value, cl.unit_raw)
        out["clearance"] = {"value": pq.value, "unit": pq.unit}
        out["clearance_basis"] = cl.basis
        out["notes"].extend(pq.notes)
        out["evidence"].append({"param": "clearance", "value_raw": f"{cl.value} {cl.unit_raw}".strip(), "context": cl.context[:400]})

    if v_cands:
        v = _best(v_cands, kind="volume", text_len=len(text), route=route, prefer_basis=prefer_basis)
        pq = convert_volume(v.value, v.unit_raw)
        out["volume"] = {"value": pq.value, "unit": pq.unit}
        out["volume_basis"] = v.basis
        out["notes"].extend(pq.notes)
        out["evidence"].append({"param": "volume", "value_raw": f"{v.value} {v.unit_raw}".strip(), "context": v.context[:400]})

    if out.get("clearance") or out.get("volume"):
        out["notes"].append("Rescue extractor used PKROW segments (table-derived lines) to recover parameters.")
    return out

def _infer_basis(kind: str, kw: str, ctx: str) -> str:
    """Infer whether a candidate is systemic (CL, V) or apparent (CL/F, V/F)."""
    k = (kw or "").lower()
    c = (ctx or "").lower()
    if "/f" in k or "cl/f" in k or "v/f" in k:
        return "apparent"
    if "apparent" in k:
        return "apparent"
    if "systemic" in k or "total clearance" in k:
        return "systemic"
    # Context hints
    if any(t in c for t in ["cl/f", "v/f", "apparent"]):
        return "apparent"
    if any(t in c for t in ["systemic", "total clearance", "intravenous", "iv "]):
        return "systemic"
    # For volume, Vss/Vdss are typically systemic (not V/F) unless explicitly stated
    if kind == "volume" and any(t in k for t in ["vss", "vdss"]):
        return "systemic"
    return "unknown"

def _extract_sentence(text: str, rel_start: int, rel_end: int) -> str:
    """Extract a sentence-like window around [rel_start, rel_end) in `text`."""
    # Look for sentence boundary punctuation.
    left = max(text.rfind(".", 0, rel_start), text.rfind(";", 0, rel_start), text.rfind(":", 0, rel_start), text.rfind("\n", 0, rel_start))
    right = min(
        [p for p in [text.find(".", rel_end), text.find(";", rel_end), text.find(":", rel_end), text.find("\n", rel_end)] if p != -1]
        + [len(text)]
    )
    return text[max(0, left + 1): right].strip()

def _find_candidates(text: str, kw_pattern: str, unit_pattern: str, *, kind: str, window: int = 280) -> List[Candidate]:
    """Return list of candidates near each keyword occurrence."""
    out: List[Candidate] = []
    for m in re.finditer(kw_pattern, text, flags=re.I):
        kw = m.group(0)
        # Avoid the bare "v" match (too ambiguous) for volume.
        if kw.strip().lower() == "v":
            continue

        start = max(0, m.start() - window)
        end = min(len(text), m.end() + window)
        chunk = text[start:end]

        # Find all number+unit pairs in this window.
        for m2 in re.finditer(rf"({PM}|{RANGE}|{NUM})\s*({unit_pattern})", chunk, flags=re.I):
            value_raw = m2.group(1)
            unit_raw = m2.group(m2.lastindex)
            try:
                val = _pick_value(value_raw)
            except Exception:
                continue
            # Distance from keyword start to this numeric match
            kw_abs = m.start()
            cand_abs = start + m2.start()
            dist = abs(kw_abs - cand_abs)
            ctx = _extract_sentence(chunk, m2.start(), m2.end()) or chunk
            # Attach nearest section token (if any) to help scoring.
            sec_pos = chunk.rfind("SECTION[", 0, m2.start())
            if sec_pos != -1:
                sec_end = chunk.find("]", sec_pos)
                if sec_end != -1 and sec_end - sec_pos < 120:
                    sec_tok = chunk[sec_pos:sec_end+1]
                    if sec_tok not in ctx:
                        ctx = (sec_tok + " " + ctx).strip()
            basis = _infer_basis(kind, kw, ctx)
            out.append(Candidate(value=val, unit_raw=unit_raw, context=ctx, kw=kw, basis=basis, distance=dist, pos=cand_abs))
    return out

def _best(cands: List[Candidate], kind: str, text_len: int, *, route: str = "oral", prefer_basis: str = "auto") -> Optional[Candidate]:
    if not cands:
        return None

    # Decide preferred basis.
    pref = (prefer_basis or "auto").lower()
    if pref == "auto":
        pref = "apparent" if (route or "").lower().startswith("o") else "systemic"
    if pref not in {"systemic", "apparent", "any"}:
        pref = "any"

    def score(c: Candidate) -> float:
        u2 = c.unit_raw.lower().replace(" ", "")
        ctx = c.context.lower()

        s = 0.0
        # Prefer being close to the keyword.
        s -= (c.distance / 25.0)

        # Prefer explicit L-based units.
        if "l/" in u2:
            s += 10.0
        if "ml/" in u2:
            s += 5.0
        if "kg" in u2:
            s += 2.0
        if "m2" in u2 or "1.73" in u2:
            s += 1.0
        if "70kg" in u2:
            s += 1.0

        # Prefer PK sections.
        if "section[" in ctx and any(k in ctx for k in ["clinical pharmacology", "pharmacokinet", "absorption", "distribution", "metabolism", "elimination", "excretion"]):
            s += 6.0

        # Context clues (small)
        if any(w in ctx for w in ["terminal", "elimination"]):
            s += 1.0

        # Basis preference
        if pref != "any":
            if c.basis == pref:
                s += 6.0
            elif c.basis != "unknown":
                s -= 2.5
        if "in vitro" in ctx or "reconstitut" in ctx or "vial" in ctx:
            s -= 4.0

        # Sanity checks (very gentle)
        if c.value <= 0:
            s -= 50.0
        if kind == "clearance" and c.value > 1e5:
            s -= 20.0
        if kind == "volume" and c.value > 1e7:
            s -= 20.0

        # Slight preference for later mentions (summaries often appear later).
        s += (c.pos / max(1.0, float(text_len)))
        return s

    return sorted(cands, key=score, reverse=True)[0]


_PKROW_SEG = re.compile(r"PKROW:\s*([^;]{1,240})", flags=re.I)
_UNIT_TOKEN = re.compile(r"(?i)^[a-z%][a-z0-9/\.\-\s\*]{0,24}$")


def _extract_pkrow_segments(text: str) -> List[str]:
    """Return PKROW segments found in (possibly flattened) text."""
    if not text:
        return []
    return [m.group(1).strip() for m in _PKROW_SEG.finditer(text)]


def extract_pk_from_pkrow(raw_text: str, *, route: str = "oral", prefer_basis: str = "auto") -> Dict[str, Any]:
    """Best-effort extraction from synthesized `PKROW:` segments.

    DailyMed extraction renders SPL tables into segments like:
      PKROW: Clearance 5.2 L/h
      PKROW: Vc 35 L

    Our main regex extractor is keyword-window based, which can miss when the
    table text is flattened. This helper parses PKROW segments directly and
    produces the same schema as `extract_pk_from_text` (partial results allowed).
    """
    segs = [m.group(1).strip() for m in _PKROW_SEG.finditer(raw_text or "")]
    if not segs:
        return {
            "clearance": None,
            "volume": None,
            "clearance_basis": None,
            "volume_basis": None,
            "half_life_h": None,
            "bioavailability_frac": None,
            "evidence": [],
            "notes": [],
            "diagnostics": {"pkrow_segments": 0},
        }

    pref = (prefer_basis or "auto").lower()
    if pref == "auto":
        pref = "apparent" if (route or "").lower().startswith("o") else "systemic"
    if pref not in {"systemic", "apparent", "any"}:
        pref = "any"

    # Candidate containers
    cl_cands: List[Candidate] = []
    v_cands: List[Candidate] = []
    hl_cands: List[Tuple[float, str, str, int]] = []
    f_cands: List[Tuple[float, bool, str, str, int]] = []

    # Parse each segment as: label + numeric + optional unit
    # Example: "Clearance 5.2 L/h" / "Apparent oral clearance (CL/F) 1.1 L/hr".
    seg_re = re.compile(rf"^(?P<label>.+?)\s+(?P<numexpr>{PM}|{RANGE}|{NUM})(?:\s+(?P<unit>[^;]+))?$", flags=re.I)
    for i, seg in enumerate(segs):
        s = seg.strip()
        m = seg_re.match(s)
        if not m:
            continue
        label = (m.group("label") or "").strip()
        numexpr = (m.group("numexpr") or "").strip()
        unit = (m.group("unit") or "").strip()
        # If unit looks suspiciously long, drop it (we'll still keep the numeric value).
        if unit and (len(unit) > 32 or not _UNIT_TOKEN.match(unit.replace(" ", ""))):
            unit = ""

        try:
            val = _pick_value(numexpr)
        except Exception:
            continue

        lbl = label.lower()
        ctx = f"PKROW: {seg}"[:480]

        # Half-life
        if any(k in lbl for k in ["half-life", "half life", "t1/2", "t 1/2"]):
            # If unit missing, try to infer from label.
            u = unit or ("h" if "h" in lbl or "hr" in lbl else "")
            if u:
                score = 1
                if "terminal" in lbl or "elimination" in lbl:
                    score += 2
                hl_cands.append((val, u, ctx, score))
            continue

        # Bioavailability
        if "bioavailability" in lbl or re.search(r"\bf\b", lbl):
            is_percent = False
            if unit.strip().startswith("%") or "percent" in unit.lower():
                is_percent = True
            if unit == "" and val > 1 and val <= 100:
                # Heuristic: if 0<val<=1.5 treat as fraction, else treat as percent
                is_percent = True
            score = 1
            if "absolute" in lbl:
                score += 2
            f_cands.append((val, is_percent, f"{numexpr}{unit}".strip(), ctx, score))
            continue

        # Clearance / Volume routing based on label.
        is_cl = (
            "clearance" in lbl
            or re.search(r"\bcl\b", lbl)
            or "cl/f" in lbl
            or "clt" in lbl
            or "total body" in lbl
            or "systemic clearance" in lbl
            or "oral clearance" in lbl
        )
        is_v = (
            "volume" in lbl
            or "vd" in lbl
            or "vss" in lbl
            or "vdss" in lbl
            or re.fullmatch(r"v\s*/\s*f", lbl.replace(" ", "")) is not None
            or re.search(r"\b(v1|vc|vp|v2)\b", lbl) is not None
            or "central" in lbl
            or re.fullmatch(r"v", lbl.strip()) is not None
        )

        # If neither, skip.
        if not is_cl and not is_v:
            continue

        basis = _infer_basis("clearance" if is_cl else "volume", label, ctx)
        # Approx distance/pos for scoring compatibility
        pos = i
        dist = 0
        if is_cl:
            # Require a plausible unit or leave to conversion notes.
            if unit:
                cl_cands.append(Candidate(value=val, unit_raw=unit, context=ctx, kw=label, basis=basis, distance=dist, pos=pos))
            else:
                # Without unit it's risky; keep only if the label includes a unit in parentheses.
                cl_cands.append(Candidate(value=val, unit_raw="L/h", context=ctx + " (unit defaulted to L/h)", kw=label, basis=basis, distance=dist, pos=pos))
        elif is_v:
            if unit:
                v_cands.append(Candidate(value=val, unit_raw=unit, context=ctx, kw=label, basis=basis, distance=dist, pos=pos))
            else:
                v_cands.append(Candidate(value=val, unit_raw="L", context=ctx + " (unit defaulted to L)", kw=label, basis=basis, distance=dist, pos=pos))

    out: Dict[str, Any] = {
        "clearance": None,
        "volume": None,
        "clearance_basis": None,
        "volume_basis": None,
        "half_life_h": None,
        "bioavailability_frac": None,
        "evidence": [],
        "notes": [],
        "diagnostics": {"pkrow_segments": len(segs), "clearance_candidates": len(cl_cands), "volume_candidates": len(v_cands)},
    }

    # Select best candidates with the same scorer as the main extractor.
    cl = _best(cl_cands, kind="clearance", text_len=max(1, len(raw_text)), route=route, prefer_basis=pref)
    if cl:
        pq = convert_clearance(cl.value, cl.unit_raw)
        out["clearance"] = {"value": pq.value, "unit": pq.unit}
        out["clearance_basis"] = cl.basis
        out["notes"].extend(pq.notes)
        out["evidence"].append({"param": "clearance", "value_raw": f"{cl.value} {cl.unit_raw}", "context": cl.context[:400]})

    v = _best(v_cands, kind="volume", text_len=max(1, len(raw_text)), route=route, prefer_basis=pref)
    if v:
        pq = convert_volume(v.value, v.unit_raw)
        out["volume"] = {"value": pq.value, "unit": pq.unit}
        out["volume_basis"] = v.basis
        out["notes"].extend(pq.notes)
        out["evidence"].append({"param": "volume", "value_raw": f"{v.value} {v.unit_raw}", "context": v.context[:400]})

    if hl_cands:
        val, unit, ctx, _ = sorted(hl_cands, key=lambda x: x[3], reverse=True)[0]
        pq = convert_half_life_to_h(val, unit)
        out["half_life_h"] = pq.value if pq.unit == "h" else val
        out["notes"].extend(pq.notes)
        out["evidence"].append({"param": "half_life", "value_raw": f"{val} {unit}", "context": ctx[:400]})

    if f_cands:
        val, is_percent, value_raw, ctx, _ = sorted(f_cands, key=lambda x: x[4], reverse=True)[0]
        if is_percent:
            val = val / 100.0
        if 0 < val <= 1.5:
            out["bioavailability_frac"] = max(0.0, min(1.0, float(val)))
            out["evidence"].append({"param": "bioavailability", "value_raw": value_raw or str(val), "context": ctx[:400]})

    if out.get("clearance") or out.get("volume"):
        out["notes"].append("Extracted one or more PK parameters from DailyMed PKROW table segments.")

    return out


# Backward-compatible alias (internal)
_extract_pk_from_pkrow = extract_pk_from_pkrow

def extract_pk_from_text(text: str, *, route: str = "oral", prefer_basis: str = "auto") -> Dict[str, Any]:
    """Extract CL, V, half-life, F from text.

    Args:
      route: "oral" or "iv" (used only for basis preference when prefer_basis="auto").
      prefer_basis: "auto" (default), "apparent", "systemic", or "any".

    Rationale:
      - Oral labels often report CL/F and V/F (apparent), so default prefers apparent.
      - IV labels typically report systemic CL and V.
    """
    text = normalize_text(text)

    res: Dict[str, Any] = {
        "clearance": None,
        "volume": None,
        "clearance_basis": None,
        "volume_basis": None,
        "half_life_h": None,
        "bioavailability_frac": None,
        "evidence": [],
        "notes": [],
        "diagnostics": {},
    }

    # Diagnostics helpers
    pkrow_segs = _extract_pkrow_segments(text)
    res["diagnostics"].update({
        "has_pkrow": bool(pkrow_segs),
        "pkrow_segments": len(pkrow_segs),
    })

    # Clearance
    cl_cands = _find_candidates(text, CL_KW, CL_UNIT, kind="clearance")
    res["diagnostics"].update({
        "clearance_kw_hits": len(list(re.finditer(CL_KW, text, flags=re.I))),
        "clearance_candidates": len(cl_cands),
    })
    cl = _best(cl_cands, kind="clearance", text_len=len(text), route=route, prefer_basis=prefer_basis)
    if cl:
        val, unit_raw, ctx = cl.value, cl.unit_raw, cl.context
        pq = convert_clearance(val, unit_raw)
        res["clearance"] = {"value": pq.value, "unit": pq.unit}
        res["clearance_basis"] = cl.basis
        res["notes"].extend(pq.notes)
        res["evidence"].append({"param": "clearance", "value_raw": f"{val} {unit_raw}", "context": ctx[:400]})

    # Volume
    v_cands = _find_candidates(text, V_KW, V_UNIT, kind="volume")
    res["diagnostics"].update({
        "volume_kw_hits": len(list(re.finditer(V_KW, text, flags=re.I))),
        "volume_candidates": len(v_cands),
    })
    v = _best(v_cands, kind="volume", text_len=len(text), route=route, prefer_basis=prefer_basis)
    if v:
        val, unit_raw, ctx = v.value, v.unit_raw, v.context
        pq = convert_volume(val, unit_raw)
        res["volume"] = {"value": pq.value, "unit": pq.unit}
        res["volume_basis"] = v.basis
        res["notes"].extend(pq.notes)
        res["evidence"].append({"param": "volume", "value_raw": f"{val} {unit_raw}", "context": ctx[:400]})

    # Add a note on basis selection when we succeeded.
    if res.get("clearance") or res.get("volume"):
        pref = (prefer_basis or "auto").lower()
        if pref == "auto":
            pref = "apparent" if (route or "").lower().startswith("o") else "systemic"
        res["notes"].append(
            f"Basis preference used for extraction: prefer_basis={prefer_basis} (resolved to '{pref}' for route='{route}')."
        )

    # Half-life (t1/2)
    # We capture "half-life ... 3 h" etc.
    hl_cands: List[Tuple[float, str, str, int]] = []
    for m in re.finditer(rf"{T12_KW}[^\d]{{0,90}}(?P<numexpr>{PM}|{RANGE}|{NUM})\s*(?P<u>h|hr|hours|min|day|days)", text, flags=re.I):
        try:
            val = _pick_value(m.group("numexpr"))
        except Exception:
            continue
        unit = m.group("u")
        ctx = text[max(0, m.start() - 140): min(len(text), m.end() + 140)]
        # Prefer terminal/elimination half-life when present.
        s = 0
        clx = ctx.lower()
        if "terminal" in clx or "elimination" in clx or "t1/2" in clx or "half-life" in clx:
            s += 2
        if "distribution" in clx or "alpha" in clx:
            s -= 1
        hl_cands.append((val, unit, ctx, s))
    if hl_cands:
        val, unit, ctx, _ = sorted(hl_cands, key=lambda x: x[3], reverse=True)[0]
        pq = convert_half_life_to_h(val, unit)
        res["half_life_h"] = pq.value if pq.unit == "h" else val
        res["notes"].extend(pq.notes)
        res["evidence"].append({"param": "half_life", "value_raw": f"{val} {unit}", "context": ctx[:400]})

    # Bioavailability
    # matches "bioavailability ... 60%" or "F = 0.6"
    f_cands: List[Tuple[float, bool, str, str, int]] = []
    for m in re.finditer(rf"(?P<kw>bioavailability|\\bF\\b)[^\d]{{0,90}}(?P<numexpr>{PM}|{RANGE}|{NUM})\s*(?P<pct>%|percent)?", text, flags=re.I):
        try:
            val = _pick_value(m.group("numexpr"))
        except Exception:
            continue
        pct = (m.group("pct") or "")
        is_percent = pct.startswith("%") or "percent" in pct.lower()
        value_raw = (m.group("numexpr") + pct).strip()
        ctx = text[max(0, m.start() - 140): min(len(text), m.end() + 140)]
        s = 0
        clx = ctx.lower()
        if "absolute" in clx:
            s += 2
        if "relative" in clx:
            s -= 1
        f_cands.append((val, is_percent, value_raw, ctx, s))
    if f_cands:
        val, is_percent, value_raw, ctx, _ = sorted(f_cands, key=lambda x: x[4], reverse=True)[0]
        if is_percent:
            val = val / 100.0
        if 0 < val <= 1.5:
            res["bioavailability_frac"] = max(0.0, min(1.0, val))
            res["evidence"].append({"param": "bioavailability", "value_raw": value_raw or str(val), "context": ctx[:400]})

    return res


def rescue_extract_pk_from_text(text: str, *, route: str = "oral", prefer_basis: str = "auto") -> Dict[str, Any]:
    """Run main extractor, then fallback to PKROW parsing if still missing.

    Returns the same schema as extract_pk_from_text, plus notes/diagnostics.
    """
    base = extract_pk_from_text(text, route=route, prefer_basis=prefer_basis)
    missing_cl = not base.get("clearance")
    missing_v = not base.get("volume")
    if not (missing_cl or missing_v):
        return base

    if base.get("diagnostics", {}).get("has_pkrow"):
        pkrow = _parse_pkrow_segments(text, route=route, prefer_basis=prefer_basis)
        # Merge, preferring base then pkrow for gaps
        merged = dict(base)
        for k in ["clearance", "volume", "clearance_basis", "volume_basis", "half_life_h", "bioavailability_frac"]:
            merged[k] = merged.get(k) or pkrow.get(k)
        merged["evidence"] = (base.get("evidence") or []) + (pkrow.get("evidence") or [])
        merged["notes"] = (base.get("notes") or []) + (pkrow.get("notes") or [])
        md = dict(base.get("diagnostics") or {})
        md.update({"pkrow_rescue_used": True})
        if pkrow.get("diagnostics"):
            md.update({f"pkrow_{k}": v for k, v in pkrow["diagnostics"].items()})
        merged["diagnostics"] = md
        return merged

    return base
