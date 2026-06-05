"""DailyMed (NLM) REST API helpers and SPL text extraction."""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests
from lxml import etree

DAILYMED_BASE = "https://dailymed.nlm.nih.gov/dailymed/services/v2"

@dataclass
class SplHit:
    setid: str
    title: str
    published_date: str
    spl_version: str

def _parse_published_date(s: str) -> Optional[_dt.date]:
    try:
        return _dt.datetime.strptime(s.strip(), "%b %d, %Y").date()
    except Exception:
        return None

def search_spls(drug_name: str, pagesize: int = 25, page: int = 1) -> List[SplHit]:
    params = {"drug_name": drug_name, "pagesize": pagesize, "page": page}
    url = f"{DAILYMED_BASE}/spls.json?{urlencode(params)}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    j = r.json()
    hits = []
    for item in j.get("data", []):
        hits.append(SplHit(
            setid=item.get("setid",""),
            title=item.get("title",""),
            published_date=item.get("published_date",""),
            spl_version=item.get("spl_version",""),
        ))
    return hits

def pick_best_setid(drug_name: str, hits: List[SplHit]) -> Optional[SplHit]:
    if not hits:
        return None
    dn = drug_name.lower()
    def score(h: SplHit) -> Tuple[int, int]:
        title = (h.title or "").lower()
        s = 0
        if dn in title:
            s += 20
        if "tablet" in title or "capsule" in title or "injection" in title:
            s += 2
        # prefer newer published_date
        d = _parse_published_date(h.published_date) or _dt.date(1900,1,1)
        return (s, int(d.strftime("%Y%m%d")))
    return sorted(hits, key=score, reverse=True)[0]

def fetch_spl_xml(setid: str) -> bytes:
    url = f"{DAILYMED_BASE}/spls/{setid}.xml"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content

def extract_relevant_text_from_spl_xml(xml_bytes: bytes, only_pk_sections: bool = True) -> str:
    """Extract likely PK-related sections as plain text.

    Improvements in v0.5:
      - Section title fallback to <code displayName> when <title> missing.
      - Narrative text excludes table cell text to reduce noise.
      - Tables are rendered row-wise with separators so CL/V patterns survive.
    """
    # SPL namespace
    NS = {"h": "urn:hl7-org:v3"}
    root = etree.fromstring(xml_bytes)

    def _clean(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").strip())

    # Very loose unit detector used for table header inference.
    _UNIT_LIKE = re.compile(
        r"(?i)^(%|percent|h|hr|hours|min|day|days|l|ml|ng/mL|mg/L|l/h|l/hr|ml/min|ml/min/kg|ml/min/70\s*kg|l/h/kg|l/kg|ml/kg|l/m2|l/h/m2|ml/min/1\.73\s*m2|l/h/1\.73\s*m2|1/h)$"
    )

    def _extract_unit_from_text(s: str) -> str:
        s = _clean(s)
        m = re.search(r"\(([^\)]+)\)", s)
        if m:
            u = _clean(m.group(1))
            # Keep short unit-like strings
            if 1 <= len(u) <= 32:
                return u
        # Try comma-separated tail
        if "," in s:
            tail = _clean(s.split(",")[-1])
            if _UNIT_LIKE.match(tail.replace(" ", "")):
                return tail
        return ""

    def _looks_like_number(s: str) -> bool:
        s = s.strip()
        return bool(re.search(r"\d", s)) and bool(re.search(r"\d(?:\.\d+)?", s))

    def _looks_like_unit(s: str) -> bool:
        s = _clean(s)
        if not s:
            return False
        s2 = s.replace(" ", "")
        if _UNIT_LIKE.match(s2):
            return True
        # Common composites
        return bool(re.match(r"(?i)^(ml|min|hr|h|day|l)(/|\b)", s2))

    def _table_to_lines(table_el) -> List[str]:
        """Render SPL tables to text, with extra synthesized 'PKROW' lines.

        Why:
          - Raw row-wise rendering is useful for humans but sometimes loses the
            (value, unit) association required by regex extractors.
          - We add lightweight header/unit inference to emit canonical lines like:
              PKROW: Clearance 5.2 L/h
              PKROW: Vd 35 L
        """
        rows: List[Tuple[List[str], List[str]]] = []  # (cells, types)
        for tr in table_el.xpath(".//*[local-name()='tr']"):
            cells = tr.xpath("./*[local-name()='th' or local-name()='td']")
            row_txt: List[str] = []
            row_typ: List[str] = []
            for c in cells:
                typ = c.tag.split("}")[-1].lower()
                ct = _clean(" ".join([t for t in c.itertext() if t and t.strip()]))
                row_txt.append(ct)
                row_typ.append(typ)
            if any(x for x in row_txt if x):
                rows.append((row_txt, row_typ))

        if not rows:
            return []

        # 1) Raw rendering (as before)
        raw_lines: List[str] = []
        for row, _ in rows:
            compact = [c for c in row if c]
            if compact:
                raw_lines.append(" | ".join(compact))

        # 2) Header inference
        header_idx: Optional[int] = None
        for i, (row, typs) in enumerate(rows[:3]):
            if any(t == "th" for t in typs):
                header_idx = i
                break
        if header_idx is None:
            r0 = " ".join(rows[0][0]).lower()
            if any(k in r0 for k in ["parameter", "unit", "mean", "value", "pk"]):
                header_idx = 0

        headers: List[str] = []
        if header_idx is not None:
            headers = [_clean(h) for h in rows[header_idx][0]]

        # Identify unit column if exists
        unit_col: Optional[int] = None
        for j, h in enumerate(headers):
            if "unit" in (h or "").lower():
                unit_col = j
                break

        # Identify likely parameter column
        param_col: int = 0
        if headers:
            for j, h in enumerate(headers):
                if any(k in (h or "").lower() for k in ["parameter", "pk parameter", "parameter (", "parameter,"]):
                    param_col = j
                    break

        # Identify likely value column
        val_col: Optional[int] = None
        if headers:
            for j, h in enumerate(headers):
                hl = (h or "").lower()
                if j == unit_col:
                    continue
                if any(k in hl for k in ["value", "mean", "median", "estimate", "typical"]):
                    val_col = j
                    break

        # Fallbacks for common 2-3 col tables
        if val_col is None:
            if unit_col is not None and unit_col > 0:
                val_col = unit_col - 1
            else:
                val_col = 1 if len(rows[0][0]) > 1 else None

        # Header units on value column
        header_unit_for_val = _extract_unit_from_text(headers[val_col]) if headers and val_col is not None and val_col < len(headers) else ""

        # 3) Synthesize canonical "PKROW" lines
        start_i = (header_idx + 1) if header_idx is not None else 0
        kv_lines: List[str] = []
        for row, _ in rows[start_i:]:
            if not row:
                continue

            # Try (param, value, unit)
            p = row[param_col] if param_col < len(row) else ""
            v = row[val_col] if (val_col is not None and val_col < len(row)) else ""
            u = ""
            if unit_col is not None and unit_col < len(row) and _looks_like_unit(row[unit_col]):
                u = row[unit_col]
            if not u:
                u = _extract_unit_from_text(p) or header_unit_for_val

            # If param cell contains both name+unit in parentheses, strip the unit part
            if p and "(" in p and ")" in p:
                p_clean = re.sub(r"\([^\)]+\)", "", p).strip()
            else:
                p_clean = p.strip()

            # Sometimes the value is actually in another column (e.g., 3rd column)
            if not _looks_like_number(v):
                for cand in row:
                    if cand != p and _looks_like_number(cand):
                        v = cand
                        break

            # If unit is still empty but value contains a unit, keep as-is.
            if not p_clean or not v:
                continue

            if u and u not in v:
                kv_lines.append(f"{p_clean} {v} {u}")
            else:
                kv_lines.append(f"{p_clean} {v}")

        # Emit PKROW lines first to aid extraction, then the raw lines for audit.
        out_lines: List[str] = []
        for l in kv_lines[:120]:
            out_lines.append("PKROW: " + l)
        out_lines.extend(raw_lines[:200])
        return out_lines

    sections: List[Tuple[str, str]] = []
    for sec in root.xpath(".//h:section", namespaces=NS):
        title_el = sec.find("h:title", namespaces=NS)
        title = (title_el.text or "").strip() if title_el is not None else ""
        if not title:
            code_el = sec.find("h:code", namespaces=NS)
            if code_el is not None:
                title = (code_el.get("displayName") or code_el.get("code") or "").strip()

        text_el = sec.find("h:text", namespaces=NS)
        if text_el is None:
            continue

        # Narrative text excluding table cells
        narr_nodes = text_el.xpath(".//text()[not(ancestor::*[local-name()='table'])]")
        narr = _clean(" ".join([t for t in narr_nodes if t and t.strip()]))

        # Structured tables
        table_lines: List[str] = []
        for tbl in text_el.xpath(".//*[local-name()='table']"):
            tl = _table_to_lines(tbl)
            if tl:
                table_lines.extend(tl[:80])  # safety cap per table

        txt_parts: List[str] = []
        if narr:
            txt_parts.append(narr)
        if table_lines:
            txt_parts.append("TABLE: " + " ; ".join(table_lines))
        txt = _clean(" ".join(txt_parts))
        if not txt:
            continue
        sections.append((title, txt))

    # prioritize likely PK / clinical pharmacology sections
    keep: List[Tuple[str, str]] = []
    keys = [
        "CLINICAL PHARMACOLOGY",
        "PHARMACOKINETICS",
        "PHARMACOKINETIC",
        "ABSORPTION",
        "DISTRIBUTION",
        "METABOLISM",
        "ELIMINATION",
        "EXCRETION",
    ]
    for title, txt in sections:
        t = (title or "").upper()
        if any(k in t for k in keys):
            keep.append((title, txt))

    def _order_key(title: str) -> int:
        t = (title or "").upper()
        if "CLINICAL PHARMACOLOGY" in t:
            return 10
        if "PHARMACOKINET" in t:
            return 20
        if "ABSORPTION" in t:
            return 30
        if "DISTRIBUTION" in t:
            return 40
        if "METABOLISM" in t:
            return 50
        if "ELIMINATION" in t or "EXCRETION" in t:
            return 60
        return 99

    if keep and only_pk_sections:
        keep_sorted = sorted(keep, key=lambda x: _order_key(x[0]))
        return "\n\n".join([f"## {t}\n{txt}" for t, txt in keep_sorted])

    # fallback: return full text (may be huge)
    return "\n\n".join([f"## {t}\n{txt}" for t, txt in sections])
