#!/usr/bin/env python3
"""Codex harness sanity checks for the PK template repository.

These checks complement tools/validate_library.py. They focus on repository
hygiene for coding agents: required harness files, generated artifact counts,
route-specific spec presence, and absence of common junk files.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Any

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.validate_manifest import validate_manifest_file


JUNK_FILE_NAMES = {".DS_Store"}
JUNK_DIR_NAMES = {"__MACOSX", "__pycache__", ".pytest_cache"}
REQUIRED_FILES = [
    ".github/workflows/ci.yml",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/ACCEPTANCE_TEST.md",
    "docs/APP_DECISION.md",
    "docs/WINDOWS_POWERSHELL.md",
    "docs/VALIDATION_AND_RELEASE_CHECKLIST.md",
    "docs/USER_TEST_REPORT_TEMPLATE.md",
    "docs/EXTERNAL_TOOL_VALIDATION_GUIDE.md",
    "docs/SITE_ADAPTER_GUIDE.md",
    "docs/RELEASE_NOTES_TEMPLATE.md",
    "docs/LAUNCHER_CONTRACT.md",
    "docs/DOWNSTREAM_E2E.md",
    "docs/PROCESS_FLOW.md",
    "docs/QUICKSTART.md",
    "docs/USER_GUIDE.md",
    "docs/CODEX_HARNESS.md",
    "docs/assets/pk-harness-workflow.png",
    "docs/assets/pk-harness-process.drawio",
    "docs/assets/pk-fixture-end-to-end-workflow.drawio",
    "examples/minimal_aciclovir/README.md",
    "examples/minimal_aciclovir/harness.yml",
    "examples/minimal_aciclovir/sdtm_like/DM.csv",
    "examples/minimal_aciclovir/sdtm_like/VS.csv",
    "examples/minimal_aciclovir/sdtm_like/LB.csv",
    "examples/minimal_aciclovir/sdtm_like/EX.csv",
    "examples/minimal_aciclovir/sdtm_like/PC.csv",
    "examples/minimal_aciclovir/workflow/analysis_inputs/ADPC.csv",
    "examples/minimal_aciclovir/workflow/analysis_inputs/NCA_INPUT.csv",
    "examples/minimal_aciclovir/workflow/analysis_inputs/POPPK_INPUT.csv",
    "examples/minimal_aciclovir/workflow/reports/pk_fixture_report/REPORT.md",
    "examples/minimal_albuterol_iv/README.md",
    "examples/minimal_albuterol_iv/harness.yml",
    "examples/minimal_albuterol_iv/sdtm_like/DM.csv",
    "examples/minimal_albuterol_iv/sdtm_like/VS.csv",
    "examples/minimal_albuterol_iv/sdtm_like/LB.csv",
    "examples/minimal_albuterol_iv/sdtm_like/EX.csv",
    "examples/minimal_albuterol_iv/sdtm_like/PC.csv",
    "examples/minimal_albuterol_iv/workflow/analysis_inputs/ADPC.csv",
    "examples/minimal_albuterol_iv/workflow/analysis_inputs/NCA_INPUT.csv",
    "examples/minimal_albuterol_iv/workflow/analysis_inputs/POPPK_INPUT.csv",
    "examples/minimal_albuterol_iv/workflow/reports/pk_fixture_report/REPORT.md",
    "external_validation/site_adapter_template.yml",
    "external_validation/tool_profiles.yml",
    "external_validation/tool_profiles.windows.example.yml",
    "harness_examples/demo_set.yml",
    "harness_examples/post_simulation_template.yml",
    "Makefile",
    "scripts/harness-check.ps1",
    "scripts/acceptance-check.ps1",
    "scripts/release-check.ps1",
    "requirements-dev.txt",
    "pyproject.toml",
    "templates/README.md",
    "templates/pk_fixture_report.qmd",
    "templates/pk_fixture_reference_source.qmd",
    "templates/pk_fixture_reference.docx",
    "tools/validate_library.py",
    "tools/rebuild_index.py",
    "tools/regen_check.py",
    "tools/pk_fixture_cli.py",
    "tools/validate_subjects_csv.py",
    "tools/run_harness.py",
    "tools/run_workflow.py",
    "tools/validate_simulation.py",
    "tools/sample_clinical_timepoints.py",
    "tools/make_sdtm_like_domains.py",
    "tools/make_analysis_inputs.py",
    "tools/make_downstream_adapters.py",
    "tools/make_site_adapters.py",
    "tools/validate_downstream_adapters.py",
    "tools/run_downstream_smoke.py",
    "tools/run_external_tool_validation.py",
    "tools/render_manifest_viewer.py",
    "tools/check_examples.py",
    "tools/doctor.py",
    "tools/validate_manifest.py",
    "tools/report_pk_fixture.R",
    "tools/render_pk_fixture_quarto.R",
    "tools/run_demo_set.py",
    "tools/make_simpop_subjects.R",
    "tests/test_repository_integrity.py",
    "tests/test_pk_fixture_cli.py",
    "tests/test_windows_powershell_support.py",
    "tests/test_operational_readiness_pack.py",
    "tests/test_pk_units.py",
    "tests/test_pk_extract.py",
    "tests/test_template_gen.py",
    "tests/test_validate_subjects_csv.py",
    "tests/test_run_harness.py",
    "tests/test_run_workflow.py",
    "tests/test_simpop_subjects_script.py",
    "tests/test_validate_simulation.py",
    "tests/test_make_sdtm_like_domains.py",
    "tests/test_make_analysis_inputs.py",
    "tests/test_make_downstream_adapters.py",
    "tests/test_make_site_adapters.py",
    "tests/test_validate_downstream_adapters.py",
    "tests/test_run_downstream_smoke.py",
    "tests/test_run_external_tool_validation.py",
    "tests/test_render_manifest_viewer.py",
    "tests/test_validate_harness_config.py",
    "tests/test_check_examples.py",
    "tests/test_doctor.py",
    "tests/test_validate_manifest.py",
    "tests/test_report_pk_fixture_script.py",
    "tests/test_render_pk_fixture_quarto_script.py",
    "tests/test_run_demo_set.py",
]
EXCLUDED_COLUMNS = [
    "drug",
    "slug",
    "route_inferred",
    "status",
    "missing",
    "reason",
    "reason_json",
    "remediation_hint",
]
INDEX_COLUMNS = [
    "drug",
    "slug",
    "route",
    "half_life_h",
    "CL_abs_L_h_at_70kg",
    "V_abs_L_at_70kg",
    "F",
    "spec_file",
    "pk_file",
    "sources_n",
    "targets_file",
]


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def csv_columns(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        return next(reader, [])


def normalize_route(route: Any) -> str:
    r = str(route or "").strip().lower()
    if r in {"po", "oral", "p.o.", "per os"} or r.startswith("oral"):
        return "po"
    if r in {"iv", "i.v.", "intravenous"} or r.startswith("iv") or r.startswith("intraven"):
        return "iv"
    return r


def check_no_junk(root: Path, issues: list[str]) -> None:
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        # Test runs naturally create caches; they are ignored here and excluded from the zip.
        if any(part in JUNK_DIR_NAMES for part in rel.parts):
            continue
        if path.is_file():
            if path.name in JUNK_FILE_NAMES or path.name.startswith("._") or path.suffix == ".pyc":
                issues.append(f"junk file present: {rel}")


def check_required_files(root: Path, issues: list[str]) -> None:
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            issues.append(f"missing required harness file: {rel}")


def check_manifest_counts(root: Path, issues: list[str]) -> None:
    pk_library_path = root / "pk_library.yml"
    index_path = root / "INDEX.csv"
    excluded_path = root / "EXCLUDED.csv"
    drugs_dir = root / "drugs"

    for path in [pk_library_path, index_path, excluded_path, drugs_dir]:
        if not path.exists():
            issues.append(f"missing required library artifact: {path.relative_to(root)}")
            return

    library = read_yaml(pk_library_path)
    index_rows = read_csv(index_path)
    excluded_rows = read_csv(excluded_path)
    drug_dirs = sorted(p.name for p in drugs_dir.iterdir() if p.is_dir())

    counts = library.get("counts") or {}
    selected = counts.get("selected")
    excluded = counts.get("excluded")
    if selected is not None and int(selected) != len(index_rows):
        issues.append(f"pk_library.yml counts.selected={selected} but INDEX.csv has {len(index_rows)} rows")
    if excluded is not None and int(excluded) != len(excluded_rows):
        issues.append(f"pk_library.yml counts.excluded={excluded} but EXCLUDED.csv has {len(excluded_rows)} rows")
    if len(drug_dirs) != len(index_rows):
        issues.append(f"drugs/ has {len(drug_dirs)} dirs but INDEX.csv has {len(index_rows)} rows")

    index_slugs = {r.get("slug", "") for r in index_rows}
    actual_slugs = set(drug_dirs)
    if index_slugs != actual_slugs:
        issues.append(
            "INDEX.csv slugs differ from drugs/: "
            f"index_only={sorted(index_slugs - actual_slugs)}, actual_only={sorted(actual_slugs - index_slugs)}"
        )

    if csv_columns(index_path) != INDEX_COLUMNS:
        issues.append("INDEX.csv columns differ from expected harness schema")
    if csv_columns(excluded_path) != EXCLUDED_COLUMNS:
        issues.append("EXCLUDED.csv columns differ from expected harness schema")


def check_drug_files(root: Path, issues: list[str]) -> None:
    drugs_dir = root / "drugs"
    if not drugs_dir.exists():
        issues.append("missing drugs directory")
        return
    for drug_dir in sorted(drugs_dir.glob("*")):
        if not drug_dir.is_dir():
            continue
        pk_path = drug_dir / "pk.yml"
        if not pk_path.exists():
            issues.append(f"{drug_dir.name}: missing pk.yml")
            continue
        pk = read_yaml(pk_path)
        route = normalize_route(pk.get("route_inferred"))
        expected_spec = "spec_pk1_oral.yml" if route == "po" else "spec_pk1_iv.yml" if route == "iv" else ""
        if not expected_spec:
            issues.append(f"{drug_dir.name}: unsupported route_inferred={pk.get('route_inferred')!r}")
            continue
        if not (drug_dir / expected_spec).exists():
            issues.append(f"{drug_dir.name}: missing expected spec {expected_spec}")
        spec_files = sorted(p.name for p in drug_dir.glob("spec_pk1_*.yml"))
        if spec_files != [expected_spec]:
            issues.append(f"{drug_dir.name}: unexpected spec file set {spec_files}, expected {[expected_spec]}")
        if not (drug_dir / "targets.yml").exists():
            issues.append(f"{drug_dir.name}: missing targets.yml")

        sources = pk.get("sources") or []
        if not sources:
            issues.append(f"{drug_dir.name}: pk.yml has no sources")
        derived = pk.get("derived") or {}
        if derived.get("CL_abs_L_per_h_at_70kg") is None or derived.get("V_abs_L_at_70kg") is None:
            issues.append(f"{drug_dir.name}: missing derived CL or V at 70kg")


def check_versioned_manifests(root: Path, issues: list[str]) -> None:
    for path in sorted((root / "examples").glob("minimal_*/workflow/**/MANIFEST.yml")):
        rel = path.relative_to(root)
        for issue in validate_manifest_file(path):
            issues.append(f"{rel}: {issue}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    issues: list[str] = []
    check_required_files(root, issues)
    check_no_junk(root, issues)
    check_manifest_counts(root, issues)
    check_drug_files(root, issues)
    check_versioned_manifests(root, issues)

    if issues:
        print("Codex harness check: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Codex harness check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
