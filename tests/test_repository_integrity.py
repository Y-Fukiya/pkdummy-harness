import csv
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_validate_library_cli_passes():
    completed = subprocess.run(
        [sys.executable, "tools/validate_library.py", "."],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert completed.returncode == 0, completed.stdout


def test_validate_library_reports_one_compartment_attainability_warnings():
    completed = subprocess.run(
        [sys.executable, "tools/validate_library.py", "."],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Library validation: OK" in completed.stdout
    assert "1-compartment attainability warnings:" in completed.stdout
    assert "verapamil: t_half_h 5.1 h conflicts with CL/V implied" in completed.stdout


def test_regen_check_cli_passes():
    completed = subprocess.run(
        [sys.executable, "tools/regen_check.py", "."],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert completed.returncode == 0, completed.stdout


def test_catalog_counts_match_index_and_drug_folders():
    with (ROOT / "INDEX.csv").open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    drug_dirs = sorted(p for p in (ROOT / "drugs").iterdir() if p.is_dir())
    library = yaml.safe_load((ROOT / "pk_library.yml").read_text(encoding="utf-8"))

    assert len(rows) == len(drug_dirs) == library["counts"]["selected"] == 37
    assert library["counts"]["excluded"] == 0
    assert {row["slug"] for row in rows} == {p.name for p in drug_dirs}


def test_excluded_csv_is_header_only_when_library_has_no_exclusions():
    lines = (ROOT / "EXCLUDED.csv").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("drug,slug,route_inferred,status,missing")


def test_github_actions_use_node24_ready_action_versions():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "actions/checkout@v6" in workflow
    assert "actions/setup-python@v6" in workflow
    assert "actions/checkout@v4" not in workflow
    assert "actions/setup-python@v5" not in workflow


def test_acceptance_check_is_documented_for_readme_only_users():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    acceptance_doc = ROOT / "docs" / "ACCEPTANCE_TEST.md"

    assert "acceptance-check:" in makefile
    assert acceptance_doc.exists()
    doc = acceptance_doc.read_text(encoding="utf-8")
    assert "make acceptance-check" in doc
    assert "external_validation/tool_profiles.yml" in doc
    assert "external_validation/site_adapter_template.yml" in doc


def test_claude_code_shim_points_to_shared_agent_rules():
    claude_md = ROOT / "CLAUDE.md"

    assert claude_md.exists()
    text = claude_md.read_text(encoding="utf-8")
    assert "AGENTS.md" in text
    assert "make validate" in text
    assert "make harness-check" in text
    assert "clinical inference" in text
    assert ".claude" not in text


def test_minimal_examples_are_versioned_for_new_users():
    examples = {
        "minimal_aciclovir": {"subjects": {"EXAMPLE-001", "EXAMPLE-002"}, "route": "ORAL"},
        "minimal_albuterol_iv": {"subjects": {"EXAMPLE_IV-001", "EXAMPLE_IV-002"}, "route": "INTRAVENOUS"},
    }
    for name, expected in examples.items():
        example_dir = ROOT / "examples" / name
        required = [
            example_dir / "README.md",
            example_dir / "harness.yml",
            example_dir / "sdtm_like" / "DM.csv",
            example_dir / "sdtm_like" / "VS.csv",
            example_dir / "sdtm_like" / "LB.csv",
            example_dir / "sdtm_like" / "EX.csv",
            example_dir / "sdtm_like" / "PC.csv",
            example_dir / "workflow" / "analysis_inputs" / "ADPC.csv",
            example_dir / "workflow" / "analysis_inputs" / "NCA_INPUT.csv",
            example_dir / "workflow" / "analysis_inputs" / "POPPK_INPUT.csv",
            example_dir / "workflow" / "reports" / "pk_fixture_report" / "REPORT.md",
        ]
        for path in required:
            assert path.exists(), f"Missing minimal example artifact: {path.relative_to(ROOT)}"

        with (example_dir / "workflow" / "analysis_inputs" / "ADPC.csv").open("r", encoding="utf-8", newline="") as f:
            adpc_rows = list(csv.DictReader(f))
        assert len(adpc_rows) == 4
        assert {row["USUBJID"] for row in adpc_rows} == expected["subjects"]
        assert {row["ROUTE"] for row in adpc_rows} == {expected["route"]}
