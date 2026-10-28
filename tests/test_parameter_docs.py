import csv
from pathlib import Path

from tools.export_parameter_docs import main


def test_public_table_and_downloads_use_corrected_execution_parameters(tmp_path):
    root = Path(__file__).resolve().parents[1]
    assert main(["--root", str(root), "--out-dir", str(tmp_path)]) == 0
    with (tmp_path / "parameters/PARAMETER_PROVENANCE.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    adopted = {(row["drug"], row["parameter"]): row["fixture_value"] for row in rows
               if row["record_type"] == "model_parameter"}
    assert float(adopted["omeprazole", "model.theta.CL"]) == 37.44
    assert float(adopted["apixaban", "model.theta.F1"]) == 0.5
    assert float(adopted["sildenafil", "model.theta.CL"]) == 41
    table_rows = (tmp_path / "PARAMETERS.md").read_text().splitlines()
    apixaban = next(line for line in table_rows if line.startswith("| apixaban |"))
    assert [float(value.strip()) for value in apixaban.split("|")[3:7]] == [3.3, 21, 1.2, 0.5]
    assert "臨床採用保留" in "\n".join(table_rows)
    assert (tmp_path / "parameters/PARAMETER_PROVENANCE.md").read_text().startswith("---\nlayout: page\n")
    assert not (tmp_path / "parameters/PARAMETER_PROVENANCE.yml").exists()

    assert "(/pkdummy-harness/parameters/PARAMETER_PROVENANCE.csv)" in "\n".join(table_rows)
    assert "(/pkdummy-harness/parameter-corrections/)" in "\n".join(table_rows)
