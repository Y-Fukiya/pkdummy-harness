from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tools.make_site_adapters import make_site_adapters

from tests.test_make_downstream_adapters import write_analysis_inputs


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_yaml(path: Path, obj: dict) -> None:
    path.write_text(yaml.safe_dump(obj, sort_keys=False), encoding="utf-8")


def test_make_site_adapters_maps_analysis_inputs_to_site_specific_columns(tmp_path: Path) -> None:
    analysis_dir = write_analysis_inputs(tmp_path)
    spec_yml = tmp_path / "site_adapter.yml"
    out_dir = tmp_path / "site_adapters"
    write_yaml(
        spec_yml,
        {
            "version": "0.1",
            "adapters": {
                "site_nca": {
                    "source": "ADPC",
                    "output": "site_nca.csv",
                    "columns": [
                        {"name": "SUBJECT", "source": "USUBJID"},
                        {"name": "TIME", "source": "TIME_H"},
                        {"name": "CONC", "source": "AVAL"},
                        {"name": "STUDY", "value": "SYNTH_PK"},
                    ],
                    "required_nonblank": ["SUBJECT", "TIME", "CONC"],
                },
                "site_poppk": {
                    "source": "POPPK_INPUT",
                    "output": "site_poppk.csv",
                    "columns": [
                        {"name": "ID", "source": "ID"},
                        {"name": "TIME", "source": "TIME"},
                        {"name": "EVID", "source": "EVID"},
                        {"name": "DV", "source": "DV"},
                    ],
                },
            },
        },
    )

    result = make_site_adapters(analysis_dir=analysis_dir, spec_yml=spec_yml, out_dir=out_dir)

    assert result.status == "OK"
    assert result.counts == {"site_nca_rows": 2, "site_poppk_rows": 2}
    assert read_csv(out_dir / "site_nca.csv")[1] == {
        "SUBJECT": "OSP_demo-001",
        "TIME": "1",
        "CONC": "50",
        "STUDY": "SYNTH_PK",
    }
    manifest = yaml.safe_load((out_dir / "SITE_ADAPTER_MANIFEST.yml").read_text(encoding="utf-8"))
    assert manifest["purpose"] == "site_specific_adapter_fixture"
    assert manifest["adapters"] == ["site_nca", "site_poppk"]


def test_make_site_adapters_fails_when_required_source_column_is_missing(tmp_path: Path) -> None:
    analysis_dir = write_analysis_inputs(tmp_path)
    spec_yml = tmp_path / "site_adapter.yml"
    write_yaml(
        spec_yml,
        {
            "version": "0.1",
            "adapters": {
                "bad": {
                    "source": "ADPC",
                    "output": "bad.csv",
                    "columns": [{"name": "MISSING", "source": "DOES_NOT_EXIST"}],
                }
            },
        },
    )

    with pytest.raises(ValueError, match="bad: source column not found: DOES_NOT_EXIST"):
        make_site_adapters(analysis_dir=analysis_dir, spec_yml=spec_yml, out_dir=tmp_path / "out")


def test_make_site_adapters_rejects_output_paths_outside_out_dir(tmp_path: Path) -> None:
    analysis_dir = write_analysis_inputs(tmp_path)
    spec_yml = tmp_path / "site_adapter.yml"
    write_yaml(
        spec_yml,
        {
            "version": "0.1",
            "adapters": {
                "unsafe": {
                    "source": "ADPC",
                    "output": "../unsafe.csv",
                    "columns": [{"name": "SUBJECT", "source": "USUBJID"}],
                }
            },
        },
    )

    with pytest.raises(ValueError, match="unsafe: output path must stay inside out_dir"):
        make_site_adapters(analysis_dir=analysis_dir, spec_yml=spec_yml, out_dir=tmp_path / "out")


def test_make_site_adapters_cli(tmp_path: Path) -> None:
    analysis_dir = write_analysis_inputs(tmp_path)
    spec_yml = tmp_path / "site_adapter.yml"
    out_dir = tmp_path / "site_adapters"
    write_yaml(
        spec_yml,
        {
            "version": "0.1",
            "adapters": {
                "site_nca": {
                    "source": "ADPC",
                    "output": "site_nca.csv",
                    "columns": [
                        {"name": "SUBJECT", "source": "USUBJID"},
                        {"name": "TIME", "source": "TIME_H"},
                    ],
                }
            },
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            "tools/make_site_adapters.py",
            "--analysis-dir",
            str(analysis_dir),
            "--spec-yml",
            str(spec_yml),
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "Site adapters written: OK" in completed.stdout
    assert (out_dir / "site_nca.csv").exists()
