from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml
import pytest

from tools.render_manifest_viewer import render_manifest_viewer


ROOT = Path(__file__).resolve().parents[1]


def write_yaml(path: Path, obj: dict) -> None:
    path.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")


def test_render_manifest_viewer_creates_static_html_summary(tmp_path: Path) -> None:
    manifest = tmp_path / "HARNESS_MANIFEST.yml"
    out_html = tmp_path / "viewer.html"
    write_yaml(
        manifest,
        {
            "purpose": "pk_fixture_harness_entrypoint",
            "mode": "demo_set",
            "status": "WARN",
            "outputs": {"summary_csv": "summary.csv"},
            "counts": {"drugs": 2},
            "warnings": ["demo warning"],
            "safeguards": ["do not use for clinical inference"],
        },
    )

    result = render_manifest_viewer(manifest, out_html)

    assert result == out_html
    html = out_html.read_text(encoding="utf-8")
    assert "PK Fixture Manifest Viewer" in html
    assert "WARN" in html
    assert "demo warning" in html
    assert "summary.csv" in html


def test_render_manifest_viewer_cli(tmp_path: Path) -> None:
    manifest = tmp_path / "MANIFEST.yml"
    out_html = tmp_path / "viewer.html"
    write_yaml(manifest, {"purpose": "analysis_input_smoke_test_fixture", "status": "OK", "outputs": {}, "counts": {}, "warnings": []})

    completed = subprocess.run(
        [
            sys.executable,
            "tools/render_manifest_viewer.py",
            str(manifest),
            "--out-html",
            str(out_html),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Manifest viewer written" in completed.stdout
    assert out_html.exists()


def test_manifest_viewer_keeps_clinical_hold_separate_from_execution_ok(tmp_path):
    from tools.export_fixture_context import resolve_fixture_context

    manifest = tmp_path / "MANIFEST.yml"
    context = resolve_fixture_context(ROOT / "drugs/abciximab/spec_pk1_iv.yml")
    write_yaml(manifest, {"status": "OK", "fixture_context": context})
    html = render_manifest_viewer(manifest).read_text(encoding="utf-8")
    assert "Execution status:" in html
    assert "clinical_hold" in html and "not_approved" in html
    assert "computational_stress_test" in html


def test_manifest_viewer_keeps_each_drug_clinical_context(tmp_path):
    from tools.export_fixture_context import resolve_fixture_context

    manifest = tmp_path / "HARNESS_MANIFEST.yml"
    contexts = {slug: resolve_fixture_context(ROOT / f"drugs/{slug}/{spec}") for slug, spec in (
        ("triazolam", "spec_pk1_oral.yml"), ("albuterol", "spec_pk1_iv.yml"),
    )}
    write_yaml(manifest, {"status": "OK", "fixture_contexts": contexts})
    html = render_manifest_viewer(manifest).read_text(encoding="utf-8")
    assert "clinical_hold" in html
    assert "triazolam" in html and "albuterol" in html
    assert "not_assessed" in html


@pytest.mark.parametrize("declaration", [{"fixture_context": None}, {"fixture_contexts": None}, {"fixture_contexts": {}}, {"fixture_contexts": {"triazolam": None}}])
def test_manifest_viewer_rejects_invalid_declared_context(tmp_path, declaration):
    manifest = tmp_path / "HARNESS_MANIFEST.yml"
    write_yaml(manifest, {"status": "OK", **declaration})
    with pytest.raises(ValueError):
        render_manifest_viewer(manifest)
