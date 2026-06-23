"""NCBI Entrez E-utilities helpers for PubMed/PMC."""

from __future__ import annotations

from typing import List
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

def esearch(db: str, term: str, retmax: int = 20) -> List[str]:
    params = {"db": db, "term": term, "retmax": str(retmax), "retmode": "xml"}
    url = f"{EUTILS_BASE}/esearch.fcgi?{urlencode(params)}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    return [id_el.text for id_el in root.findall(".//Id") if id_el.text]

def elink_pubmed_to_pmc(pmids: List[str]) -> List[str]:
    if not pmids:
        return []
    params = {"dbfrom": "pubmed", "db": "pmc", "linkname": "pubmed_pmc", "id": ",".join(pmids), "retmode": "xml"}
    url = f"{EUTILS_BASE}/elink.fcgi?{urlencode(params)}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    pmcids = []
    for linkset in root.findall(".//LinkSetDb"):
        for id_el in linkset.findall(".//Link/Id"):
            if id_el.text:
                pmcids.append(id_el.text)
    # Deduplicate
    return sorted(set(pmcids), key=lambda x: int(x) if x.isdigit() else x)

def efetch_pubmed_abstract(pmid: str) -> str:
    params = {"db": "pubmed", "id": pmid, "retmode": "xml"}
    url = f"{EUTILS_BASE}/efetch.fcgi?{urlencode(params)}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    parts = []
    for ab in root.findall(".//AbstractText"):
        if ab.text:
            parts.append(ab.text.strip())
    return "\n".join(parts).strip()

def efetch_pmc_fulltext_xml(pmcid: str) -> str:
    # pmcid here is numeric id in PMC (not including 'PMC')
    params = {"db": "pmc", "id": pmcid, "rettype": "full", "retmode": "xml"}
    url = f"{EUTILS_BASE}/efetch.fcgi?{urlencode(params)}"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.text

def strip_xml_to_text(xml_text: str) -> str:
    # very lightweight xml->text for PMC NXML
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return xml_text
    texts = []
    for el in root.iter():
        if el.text and el.text.strip():
            texts.append(el.text.strip())
    return " ".join(texts)
