import csv
from pathlib import Path

import pytest
import yaml

from tests.test_make_sdtm_like_domains import write_clinical_samples
from tools.make_analysis_inputs import make_analysis_inputs
from tools.make_sdtm_like_domains import make_sdtm_like_domains

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def generated(tmp_path):
    clinical = tmp_path / "clinical.csv"
    write_clinical_samples(clinical)
    sdtm = make_sdtm_like_domains(clinical_samples_csv=clinical, spec_yml=ROOT / "drugs/felodipine/spec_pk1_oral.yml", out_dir=tmp_path / "sdtm")
    return sdtm


def test_canonical_hold_and_dose_purpose_reach_ex_adpc_and_manifests(tmp_path):
    sdtm = generated(tmp_path)
    ex = rows(sdtm.files["EX"])
    assert ex[0].get("CLINICAL_ASSESSMENT") == "clinical_hold"
    assert ex[0]["DOSE_PURPOSE"] == "computational_stress_test"
    analysis = make_analysis_inputs(sdtm_like_dir=sdtm.out_dir, out_dir=tmp_path / "analysis")
    for key in ("ADPC", "NCA_INPUT", "POPPK_INPUT"):
        assert all(row["CLINICAL_ASSESSMENT"] == "clinical_hold" and row["CLINICAL_USE"] == "not_approved" for row in rows(analysis.files[key]))
    for path in (sdtm.files["MANIFEST"], analysis.files["MANIFEST"]):
        context = yaml.safe_load(path.read_text(encoding="utf-8"))["fixture_context"]
        assert context["simulation_validity"]["status"] == "clinical_hold"
        assert context["clinical_dose_verified"] is False


def test_analysis_rejects_forged_context(tmp_path):
    sdtm = generated(tmp_path)
    path = sdtm.files["EX"]
    ex = rows(path)
    ex[0]["CLINICAL_USE"] = "approved"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ex[0]))
        writer.writeheader()
        writer.writerows(ex)
    with pytest.raises(ValueError, match="context|CLINICAL_USE"):
        make_analysis_inputs(sdtm_like_dir=sdtm.out_dir, out_dir=tmp_path / "analysis")
