from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from tools.make_downstream_adapters import make_downstream_adapters
from tools.validate_downstream_adapters import validate_adapter_dir

from tests.test_make_downstream_adapters import write_analysis_inputs


ROOT = Path(__file__).resolve().parents[1]


def test_validate_downstream_adapters_accepts_generated_contract_files(tmp_path: Path) -> None:
    analysis_dir = write_analysis_inputs(tmp_path)
    adapter_dir = tmp_path / "adapters"
    make_downstream_adapters(analysis_dir=analysis_dir, out_dir=adapter_dir)

    result = validate_adapter_dir(adapter_dir)

    assert result.status == "OK"
    assert result.files_checked == ["nca_phoenix.csv", "nca_r.csv", "poppk_nlmixr2.csv", "poppk_nonmem.csv"]
    assert result.issues == []


def test_validate_downstream_adapters_flags_missing_required_columns(tmp_path: Path) -> None:
    adapter_dir = tmp_path / "adapters"
    adapter_dir.mkdir()
    with (adapter_dir / "poppk_nonmem.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "TIME", "EVID"])
        writer.writeheader()
        writer.writerow({"ID": "1", "TIME": "0", "EVID": "1"})

    result = validate_adapter_dir(adapter_dir)

    assert result.status == "FAILED"
    assert any("poppk_nonmem.csv missing required columns" in issue for issue in result.issues)


def test_validate_downstream_adapters_cli(tmp_path: Path) -> None:
    analysis_dir = write_analysis_inputs(tmp_path)
    adapter_dir = tmp_path / "adapters"
    make_downstream_adapters(analysis_dir=analysis_dir, out_dir=adapter_dir)

    completed = subprocess.run(
        [
            sys.executable,
            "tools/validate_downstream_adapters.py",
            str(adapter_dir),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Downstream adapter validation: OK" in completed.stdout
