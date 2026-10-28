import csv
from pathlib import Path

from tools.export_parameter_docs import main


def test_public_table_and_downloads_use_corrected_execution_parameters(tmp_path):
    root = Path(__file__).resolve().parents[1]
    assert main(["--root", str(root), "--out-dir", str(tmp_path)]) == 0
    with (tmp_path / "parameters/PARAMETER_PROVENANCE.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    adopted = {(row["drug"], row["parameter"]): row["fixture_value"] for row in rows
               if row["record_type"] == "model_parameter"}
    assert float(adopted["omeprazole", "model.theta.CL"]) == 37.44
    assert float(adopted["apixaban", "model.theta.F1"]) == 0.5
    assert float(adopted["sildenafil", "model.theta.CL"]) == 41
    table_rows = (tmp_path / "PARAMETERS.md").read_text(encoding="utf-8").splitlines()
    apixaban = next(line for line in table_rows if line.startswith("| apixaban |"))
    assert [float(value.strip()) for value in apixaban.split("|")[3:7]] == [3.3, 21, 1.2, 0.5]
    assert "臨床モデルとしては未承認" in "\n".join(table_rows)
    assert (tmp_path / "parameters/PARAMETER_PROVENANCE.md").read_text(encoding="utf-8").startswith("---\nlayout: page\n")
    assert not (tmp_path / "parameters/PARAMETER_PROVENANCE.yml").exists()

    assert "(https://y-fukiya.github.io/pkdummy-harness/parameters/PARAMETER_PROVENANCE.csv)" in "\n".join(table_rows)
    assert "(https://y-fukiya.github.io/pkdummy-harness/parameter-corrections/)" in "\n".join(table_rows)


def test_governance_downloads_expose_actual_doses_and_selection_rules(tmp_path):
    root = Path(__file__).resolve().parents[1]
    assert main(["--root", str(root), "--out-dir", str(tmp_path)]) == 0
    with (tmp_path / "parameters/FIXTURE_GOVERNANCE.csv").open(encoding="utf-8", newline="") as handle:
        rows = {row["drug"]: row for row in csv.DictReader(handle)}
    assert len(rows) == 37
    assert {row["clinical_assessment"] for row in rows.values()} == {"not_assessed", "clinical_hold"}
    assert all(row["dose_purpose"] == "computational_stress_test" and row["clinical_dose_verified"] == "False" for row in rows.values())
    assert sum(row["hold_candidate"] == "True" for row in rows.values()) == 10
    assert rows["felodipine"]["clinical_assessment"] == "clinical_hold"
    assert '"dose_mg": 100' in rows["ethinylestradiol"]["execution_arms"]
    with (tmp_path / "parameters/PARAMETER_SELECTIONS.csv").open(encoding="utf-8", newline="") as handle:
        selections = {(row["drug"], row["parameter"]): row for row in csv.DictReader(handle)}
    assert selections["alprazolam", "CL_abs_L_per_h_at_70kg"]["rule"] == "upper_bound"
    assert selections["efavirenz", "t_half_h"]["rule"] == "legacy_fixture_value"
    assert all(row["rule"] and row["rationale"] for row in selections.values())
