from __future__ import annotations

import json
from pathlib import Path

import yaml

import tools.fetch_cdisc_reference as adapter


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def test_fetch_cdisc_domains_downloads_and_validates_dm_ex(tmp_path: Path, monkeypatch) -> None:
    dm = (
        "STUDYID,DOMAIN,USUBJID,SUBJID,AGE,AGEU,SEX\n"
        "STUDY001,DM,STUDY001-001,001,40,YEARS,F\n"
        "STUDY001,DM,STUDY001-002,002,41,YEARS,M\n"
    ).encode()
    ex = (
        "STUDYID,DOMAIN,USUBJID,EXSEQ,EXTRT,EXDOSE,EXDOSU,EXROUTE\n"
        "STUDY001,EX,STUDY001-001,1,STUDY DRUG,100,mg,ORAL\n"
        "STUDY001,EX,STUDY001-002,1,STUDY DRUG,100,mg,ORAL\n"
    ).encode()
    calls: list[tuple[str, str]] = []
    responses = {
        "DM": {"success": True, "download_url": "/download/dm.csv", "filename": "dm.csv"},
        "EX": {"success": True, "download_url": "/download/ex.csv", "filename": "ex.csv"},
    }

    def fake_urlopen(request, timeout):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        method = request.get_method() if hasattr(request, "get_method") else "GET"
        calls.append((method, url))
        if method == "POST":
            payload = json.loads(request.data.decode("utf-8"))
            return FakeResponse(json.dumps(responses[payload["domain"]]).encode())
        return FakeResponse(dm if url.endswith("/dm.csv") else ex)

    monkeypatch.setattr(adapter, "urlopen", fake_urlopen)
    fetched, manifest_path = adapter.fetch_cdisc_domains(
        out_dir=tmp_path,
        domains=["DM", "EX"],
        num_subjects=2,
        therapeutic_area="Cardiology",
        base_url="https://example.test",
    )

    assert [item.domain for item in fetched] == ["DM", "EX"]
    assert [item.rows for item in fetched] == [2, 2]
    assert [item.subjects for item in fetched] == [2, 2]
    assert (tmp_path / "DM.csv").read_bytes() == dm
    assert (tmp_path / "EX.csv").read_bytes() == ex
    assert calls == [
        ("POST", "https://example.test/api/generate-sdtm"),
        ("GET", "https://example.test/download/dm.csv"),
        ("POST", "https://example.test/api/generate-sdtm"),
        ("GET", "https://example.test/download/ex.csv"),
    ]
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["purpose"] == "optional_cdisc_reference_fixture_not_pk_source"
    assert manifest["domains"]["DM"]["subjects"] == 2
    assert manifest["domains"]["EX"]["rows"] == 2


def test_fetch_cdisc_domains_rejects_pc_and_non_csv(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(ValueError, match="Choose DM or EX"):
        adapter.fetch_cdisc_domains(out_dir=tmp_path, domains=["PC"])
    with pytest.raises(ValueError, match="Only CSV"):
        adapter.fetch_cdisc_domains(out_dir=tmp_path, domains=["DM"], format="xpt")
    with pytest.raises(ValueError, match="positive integer"):
        adapter.fetch_cdisc_domains(out_dir=tmp_path, domains=["DM"], num_subjects=True)
    with pytest.raises(ValueError, match="positive finite"):
        adapter.fetch_cdisc_domains(out_dir=tmp_path, domains=["DM"], timeout=float("inf"))
    with pytest.raises(ValueError, match="absolute http"):
        adapter.fetch_cdisc_domains(out_dir=tmp_path, domains=["DM"], base_url="not-a-url")


def test_fetch_cdisc_domains_rejects_blank_required_values(tmp_path: Path, monkeypatch) -> None:
    import pytest

    payload = b"STUDYID,DOMAIN,USUBJID,SUBJID\nSTUDY001,DM,,001\n"

    def fake_urlopen(request, timeout):
        if request.get_method() == "POST":
            return FakeResponse(json.dumps({"success": True, "download_url": "/download/dm.csv"}).encode())
        return FakeResponse(payload)

    monkeypatch.setattr(adapter, "urlopen", fake_urlopen)
    with pytest.raises(adapter.CdiscApiError, match="blank USUBJID"):
        adapter.fetch_cdisc_domains(out_dir=tmp_path, domains=["DM"], num_subjects=1, base_url="https://example.test")
