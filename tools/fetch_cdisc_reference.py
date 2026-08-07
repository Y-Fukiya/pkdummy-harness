#!/usr/bin/env python3
"""Fetch optional DM/EX reference fixtures from the CDISC Dataset Generator API.

This tool is deliberately outside the PK workflow.  The downloaded domains are
reference fixtures for schema/column mapping checks; they are not joined to the
pkdummy concentration data automatically.  PC data must continue to come from
the same pkdummy simulation that produced the workflow's DM/EX fixtures.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

import yaml


DEFAULT_BASE_URL = "https://cdiscdataset.com"
SUPPORTED_DOMAINS = ("DM", "EX")
DOMAIN_REQUIRED_COLUMNS = {
    "DM": ("USUBJID",),
    "EX": ("USUBJID", "EXTRT", "EXDOSE", "EXROUTE"),
}


class CdiscApiError(RuntimeError):
    """Raised when the optional API cannot provide a valid reference domain."""


@dataclass(frozen=True)
class DomainFetch:
    domain: str
    path: Path
    source_url: str
    rows: int
    subjects: int
    sha256: str
    response: dict[str, Any]


def _json_request(url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise CdiscApiError(f"CDISC API request failed: {url}: {exc}") from exc
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CdiscApiError(f"CDISC API returned non-JSON response: {url}") from exc
    if not isinstance(decoded, dict):
        raise CdiscApiError("CDISC API response must be a JSON object.")
    if decoded.get("success") is False:
        raise CdiscApiError(f"CDISC API rejected request: {decoded}")
    return decoded


def _download_bytes(url: str, *, timeout: float) -> bytes:
    request = Request(url, headers={"Accept": "text/csv,application/octet-stream"}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise CdiscApiError(f"CDISC API download failed: {url}: {exc}") from exc


def _resolve_download_url(base_url: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CdiscApiError("CDISC API response did not include download_url.")
    candidate = value.strip()
    if candidate.startswith("http://") or candidate.startswith("https://"):
        return candidate
    # The current service returns /download/... while older documentation
    # advertises /api/download/....  Resolve both against the API origin.
    origin = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
    return urljoin(origin.rstrip("/") + "/", candidate.lstrip("/"))


def _validate_csv(domain: str, payload: bytes, *, requested_subjects: int) -> tuple[int, int]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CdiscApiError(f"{domain} download is not UTF-8 CSV.") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    fields = reader.fieldnames or []
    missing = [column for column in DOMAIN_REQUIRED_COLUMNS[domain] if column not in fields]
    if missing:
        raise CdiscApiError(f"{domain} download is missing required columns: {', '.join(missing)}")
    rows = list(reader)
    if not rows:
        raise CdiscApiError(f"{domain} download has no data rows.")
    for index, row in enumerate(rows, start=2):
        for column in DOMAIN_REQUIRED_COLUMNS[domain]:
            if not str(row.get(column) or "").strip():
                raise CdiscApiError(f"{domain} download has a blank {column} at CSV row {index}.")
    observed_domains = {str(row.get("DOMAIN") or "").strip().upper() for row in rows}
    if "DOMAIN" in fields and observed_domains != {domain}:
        raise CdiscApiError(f"{domain} download has unexpected DOMAIN values: {sorted(observed_domains)}")
    subjects = {str(row.get("USUBJID") or "").strip() for row in rows if str(row.get("USUBJID") or "").strip()}
    if len(subjects) < requested_subjects:
        raise CdiscApiError(
            f"{domain} download contains {len(subjects)} subjects; expected at least {requested_subjects}."
        )
    return len(rows), len(subjects)


def fetch_cdisc_domains(
    *,
    out_dir: Path | str,
    domains: Iterable[str] = SUPPORTED_DOMAINS,
    num_subjects: int = 50,
    therapeutic_area: str = "Cardiology",
    format: str = "csv",
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 30.0,
) -> tuple[list[DomainFetch], Path]:
    """Fetch and validate reference domains, returning files and manifest path."""

    if isinstance(num_subjects, bool) or not isinstance(num_subjects, int) or num_subjects < 1:
        raise ValueError("num_subjects must be a positive integer.")
    if format.lower() != "csv":
        raise ValueError("Only CSV format is supported by the local reference adapter.")
    try:
        parsed_timeout = float(timeout)
    except (TypeError, ValueError) as exc:
        raise ValueError("timeout must be a positive finite number.") from exc
    if not math.isfinite(parsed_timeout) or parsed_timeout <= 0:
        raise ValueError("timeout must be a positive finite number.")
    parsed_base = urlparse(base_url)
    if parsed_base.scheme not in {"http", "https"} or not parsed_base.netloc:
        raise ValueError("base_url must be an absolute http(s) URL.")
    normalized_domains = list(dict.fromkeys(str(domain).strip().upper() for domain in domains if str(domain).strip()))
    if not normalized_domains:
        raise ValueError("At least one domain is required.")
    invalid = sorted(set(normalized_domains) - set(SUPPORTED_DOMAINS))
    if invalid:
        raise ValueError(f"Unsupported reference domains: {', '.join(invalid)}. Choose DM or EX.")

    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    endpoint = urljoin(base_url.rstrip("/") + "/", "api/generate-sdtm")
    fetched: list[DomainFetch] = []
    for domain in normalized_domains:
        response = _json_request(
            endpoint,
            {
                "domain": domain,
                "numSubjects": num_subjects,
                "therapeuticArea": therapeutic_area,
                "format": "csv",
            },
            timeout=parsed_timeout,
        )
        download_url = _resolve_download_url(base_url, response.get("download_url"))
        content = _download_bytes(download_url, timeout=parsed_timeout)
        rows, subjects = _validate_csv(domain, content, requested_subjects=num_subjects)
        path = output / f"{domain}.csv"
        path.write_bytes(content)
        fetched.append(
            DomainFetch(
                domain=domain,
                path=path,
                source_url=download_url,
                rows=rows,
                subjects=subjects,
                sha256=hashlib.sha256(content).hexdigest(),
                response=response,
            )
        )

    manifest = output / "CDISC_API_MANIFEST.yml"
    manifest_data = {
        "purpose": "optional_cdisc_reference_fixture_not_pk_source",
        "status": "OK",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "api": {
            "base_url": base_url,
            "endpoint": endpoint,
            "therapeutic_area": therapeutic_area,
            "num_subjects": num_subjects,
            "format": "csv",
        },
        "domains": {
            item.domain: {
                "path": str(item.path),
                "source_url": item.source_url,
                "rows": item.rows,
                "subjects": item.subjects,
                "sha256": item.sha256,
                "response": item.response,
            }
            for item in fetched
        },
        "safeguards": [
            "Reference domains are not automatically joined to pkdummy DM/EX/PC outputs.",
            "PC and concentration-time data remain generated by the pkdummy workflow.",
            "This service is an educational/research fixture source, not a submission-readiness validator.",
        ],
    }
    with manifest.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(manifest_data, handle, sort_keys=False, allow_unicode=True)
    return fetched, manifest


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--domains", default="DM,EX", help="Comma-separated reference domains (DM and/or EX)")
    parser.add_argument("--num-subjects", type=int, default=50)
    parser.add_argument("--therapeutic-area", default="Cardiology")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        fetched, manifest = fetch_cdisc_domains(
            out_dir=args.out_dir,
            domains=args.domains.split(","),
            num_subjects=args.num_subjects,
            therapeutic_area=args.therapeutic_area,
            base_url=args.base_url,
            timeout=args.timeout,
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"CDISC reference domains: {len(fetched)}")
    for item in fetched:
        print(f"{item.domain}: {item.rows} rows / {item.subjects} subjects -> {item.path}")
    print(f"manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
