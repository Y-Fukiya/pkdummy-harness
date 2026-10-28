import csv
from pathlib import Path

import yaml

from tests.test_export_fixture_context import generated, rows
from tools.make_analysis_inputs import make_analysis_inputs
from tools.make_downstream_adapters import make_downstream_adapters
from tools.make_repeated_nca import make_repeated_nca
from tools.make_site_adapters import make_site_adapters
from tools.export_fixture_context import resolve_fixture_context

ROOT = Path(__file__).resolve().parents[1]


def test_tool_and_site_adapters_preserve_clinical_hold(tmp_path):
    sdtm = generated(tmp_path)
    analysis = make_analysis_inputs(sdtm_like_dir=sdtm.out_dir, out_dir=tmp_path / "analysis")
    result = make_downstream_adapters(analysis_dir=analysis.out_dir, out_dir=tmp_path / "adapters")
    for key, path in result.files.items():
        if key != "manifest":
            assert all(row["CLINICAL_ASSESSMENT"] == "clinical_hold" and row["CLINICAL_USE"] == "not_approved" for row in rows(path))
    manifest = yaml.safe_load(result.files["manifest"].read_text(encoding="utf-8"))
    assert manifest["fixture_context"]["clinical_dose_verified"] is False
    spec = tmp_path / "site.yml"
    spec.write_text(yaml.safe_dump({"adapters": {"test": {"source": "ADPC", "columns": [{"name": "CONC", "source": "AVAL"}]}}}), encoding="utf-8")
    site = make_site_adapters(analysis_dir=analysis.out_dir, spec_yml=spec, out_dir=tmp_path / "site")
    assert all(row["CLINICAL_ASSESSMENT"] == "clinical_hold" for row in rows(site.files["test"]))
    assert yaml.safe_load(site.files["manifest"].read_text(encoding="utf-8"))["fixture_context"] == manifest["fixture_context"]


def test_repeated_nca_preserves_explicit_hold_and_computational_dose(tmp_path):
    samples = tmp_path / "clinical.csv"
    data = []
    for time in (0, 12, 13, 14, 16, 120, 144):
        data.append({"USUBJID": "fixture-001", "STUDYID": "fixture", "TIME_H": time, "DV": 10, "IPRED": 10,
                     "DV_UNIT": "ng/mL", "MDV": 0, "TROUGHFL": "Y" if time in (0, 120, 144) else "N",
                     "SSNCAFL": "Y" if time in (12, 13, 14, 16) else "N", "TAD_H": time - 12, "DOSESEQ_REF": 3})
    with samples.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    context = resolve_fixture_context(ROOT / "drugs/abciximab/spec_pk1_iv.yml")
    result = make_repeated_nca(clinical_samples_csv=samples, out_dir=tmp_path / "nca", analysis_dose_time_h=12,
                               interval_h=4, trough_times_h=[0, 120, 144], ss_times_after_dose_h=[0, 1, 2, 4],
                               partial_intervals_h=[(0, 2), (2, 4)], fixture_context=context)
    for key, path in result.files.items():
        if key != "MANIFEST":
            assert all(row["CLINICAL_ASSESSMENT"] == "clinical_hold" for row in rows(path))
    assert yaml.safe_load(result.files["MANIFEST"].read_text(encoding="utf-8"))["fixture_context"] == context
