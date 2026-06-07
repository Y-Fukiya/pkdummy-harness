from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_powershell_harness_check_script_mirrors_core_make_target() -> None:
    script = ROOT / "scripts" / "harness-check.ps1"

    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert "param(" in text
    assert "$Python" in text
    assert "$StepArgs" in text
    assert "tools/validate_library.py" in text
    assert "tools/codex_harness_check.py" in text
    assert "-m pytest" in text
    assert "tools/regen_check.py" in text
    assert "-m tools.pk_fixture_cli --help" in text
    assert "-m tools.pk_fixture_cli doctor --json" in text
    assert "tools/check_examples.py" in text
    assert "tools/run_downstream_smoke.py" in text
    assert "tools/make_site_adapters.py" in text
    assert "tools/run_external_tool_validation.py" in text
    assert "outputs/downstream_smoke_check/minimal_aciclovir" in text


def test_powershell_acceptance_script_runs_harness_then_doctor() -> None:
    script = ROOT / "scripts" / "acceptance-check.ps1"

    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert "./harness-check.ps1" in text
    assert "tools/doctor.py" in text


def test_windows_powershell_doc_gives_no_make_quickstart_and_boundaries() -> None:
    doc = ROOT / "docs" / "WINDOWS_POWERSHELL.md"

    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "py -3.11" in text
    assert "python -m venv .venv" in text
    assert ".\\.venv\\Scripts\\Activate.ps1" in text
    assert "Set-ExecutionPolicy -Scope Process Bypass" in text
    assert ".\\scripts\\harness-check.ps1" in text
    assert "python -m tools.pk_fixture_cli" in text
    assert "simPop" in text
    assert "Rtools" in text
    assert "not for clinical inference" in text


def test_readme_and_acceptance_docs_link_windows_powershell_guide() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    acceptance = (ROOT / "docs" / "ACCEPTANCE_TEST.md").read_text(encoding="utf-8")

    assert "docs/WINDOWS_POWERSHELL.md" in readme
    assert "WINDOWS_POWERSHELL.md" in acceptance


def test_ci_has_windows_powershell_smoke_job() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "windows-latest" in workflow
    assert "scripts/harness-check.ps1" in workflow
    assert "-SkipExternalProbe" in workflow


def test_validation_release_checklist_covers_remaining_operational_gaps() -> None:
    doc = ROOT / "docs" / "VALIDATION_AND_RELEASE_CHECKLIST.md"

    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    assert "Phoenix" in text
    assert "NONMEM" in text
    assert "nlmixr2" in text
    assert "README-only" in text
    assert "site_adapter_template.yml" in text
    assert "Rtools" in text
    assert "release tag" in text
    assert "not for clinical inference" in text
