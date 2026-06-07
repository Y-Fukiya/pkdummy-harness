from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_readme_user_test_report_template_captures_actual_user_evidence() -> None:
    doc = ROOT / "docs" / "USER_TEST_REPORT_TEMPLATE.md"

    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "README-only user test report" in text
    assert "Windows PowerShell" in text
    assert "macOS/Linux" in text
    assert "python -m tools.pk_fixture_cli doctor" in text
    assert "python -m tools.pk_fixture_cli run harness_examples/demo_set.yml" in text
    assert ".\\scripts\\acceptance-check.ps1 -SkipExternalProbe" in text
    assert "make acceptance-check" in text
    assert "not for clinical inference" in text
    assert "Questions asked by tester" in text


def test_external_tool_validation_guide_and_windows_profile_are_configurable() -> None:
    doc = ROOT / "docs" / "EXTERNAL_TOOL_VALIDATION_GUIDE.md"
    windows_profile = ROOT / "external_validation" / "tool_profiles.windows.example.yml"

    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "Phoenix" in text
    assert "NONMEM" in text
    assert "nlmixr2" in text
    assert "tool_profiles.windows.example.yml" in text
    assert "--execute" in text
    assert "success_artifacts" in text
    assert "EXTERNAL_TOOL_VALIDATION.yml" in text
    assert "SKIPPED is not automatically a harness failure" in text

    assert windows_profile.exists()
    profile = yaml.safe_load(windows_profile.read_text(encoding="utf-8"))
    assert profile["purpose"] == "optional_external_tool_validation_profiles_windows_example"
    profiles = profile["profiles"]
    assert {"phoenix", "nonmem", "nlmixr2"} <= set(profiles)
    assert "C:/Program Files" in " ".join(str(token) for token in profiles["phoenix"]["command"])
    assert "nmfe75" in " ".join(str(token) for token in profiles["nonmem"]["command"])
    assert "Rscript" in profiles["nlmixr2"]["command"][0]


def test_site_adapter_guide_explains_facility_mapping_review() -> None:
    doc = ROOT / "docs" / "SITE_ADAPTER_GUIDE.md"

    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "site_adapter_template.yml" in text
    assert "required_nonblank" in text
    assert "SITE_ADAPTER_MANIFEST.yml" in text
    assert "Phoenix" in text
    assert "NONMEM" in text
    assert "nlmixr2" in text
    assert "submission-ready ADaM" in text
    assert "facility-specific" in text


def test_release_note_template_and_release_checks_are_documented() -> None:
    template = ROOT / "docs" / "RELEASE_NOTES_TEMPLATE.md"
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    ps1 = ROOT / "scripts" / "release-check.ps1"

    assert template.exists()
    text = template.read_text(encoding="utf-8")
    assert "Release notes template" in text
    assert "Version" in text
    assert "Commit" in text
    assert "Verification matrix" in text
    assert "Windows PowerShell smoke" in text
    assert "Known limitations" in text
    assert "not for clinical inference" in text

    assert "release-check:" in makefile
    assert "make acceptance-check" in makefile

    assert ps1.exists()
    ps1_text = ps1.read_text(encoding="utf-8")
    assert "acceptance-check.ps1" in ps1_text
    assert "-SkipExternalProbe" in ps1_text


def test_main_docs_link_operational_readiness_pack() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    checklist = (ROOT / "docs" / "VALIDATION_AND_RELEASE_CHECKLIST.md").read_text(encoding="utf-8")

    for required in [
        "docs/USER_TEST_REPORT_TEMPLATE.md",
        "docs/EXTERNAL_TOOL_VALIDATION_GUIDE.md",
        "docs/SITE_ADAPTER_GUIDE.md",
        "docs/RELEASE_NOTES_TEMPLATE.md",
    ]:
        assert required in readme
        assert Path(required).name in checklist
