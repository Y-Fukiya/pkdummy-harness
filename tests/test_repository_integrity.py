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
