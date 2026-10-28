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


def test_standalone_spec_defaults_unassessed_and_pk_only_hold_is_preserved(tmp_path):
    from tools.export_fixture_context import resolve_fixture_context

    spec = tmp_path / "spec.yml"
    spec.write_text("model: {}\n", encoding="utf-8")
    context = resolve_fixture_context(spec)
    assert context["simulation_validity"]["status"] == "not_assessed"
    assert context["clinical_use"] == "not_approved"
    (tmp_path / "pk.yml").write_text(yaml.safe_dump({"simulation_validity": {"status": "clinical_hold", "reasons": ["Unresolved matrix"]}}), encoding="utf-8")
    assert resolve_fixture_context(spec)["simulation_validity"]["status"] == "clinical_hold"


def test_csv_only_analysis_keeps_hold_and_missing_context_is_not_approval(tmp_path):
    sdtm = generated(tmp_path)
    sdtm.files["MANIFEST"].unlink()
    analysis = make_analysis_inputs(sdtm_like_dir=sdtm.out_dir, out_dir=tmp_path / "csv_only")
    assert rows(analysis.files["ADPC"])[0]["CLINICAL_ASSESSMENT"] == "clinical_hold"
    from tools.export_fixture_context import CONTEXT_FIELDS

    for domain in ("EX", "PC"):
        legacy_rows = [{key: value for key, value in row.items() if key not in CONTEXT_FIELDS} for row in rows(sdtm.files[domain])]
        with sdtm.files[domain].open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(legacy_rows[0]))
            writer.writeheader()
            writer.writerows(legacy_rows)
    analysis = make_analysis_inputs(sdtm_like_dir=sdtm.out_dir, out_dir=tmp_path / "legacy")
    assert rows(analysis.files["ADPC"])[0]["CLINICAL_ASSESSMENT"] == "not_assessed"
    assert rows(analysis.files["ADPC"])[0]["CLINICAL_USE"] == "not_approved"


def test_manifest_hold_cannot_lose_csv_context(tmp_path):
    sdtm = generated(tmp_path)
    ex = rows(sdtm.files["EX"])
    for row in ex:
        row.pop("HOLD_REASONS")
    with sdtm.files["EX"].open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ex[0]))
        writer.writeheader()
        writer.writerows(ex)
    with pytest.raises(ValueError, match="incomplete"):
        make_analysis_inputs(sdtm_like_dir=sdtm.out_dir, out_dir=tmp_path / "analysis")


def test_workflow_success_and_validation_failure_preserve_hold(tmp_path):
    from tests.test_run_workflow import write_inputs
    from tools.run_workflow import run_workflow

    sim, pk_path, targets, spec = write_inputs(tmp_path)
    pk = yaml.safe_load(pk_path.read_text(encoding="utf-8"))
    pk["simulation_validity"] = {"status": "clinical_hold", "reasons": ["Source context not resolved"]}
    pk_path.write_text(yaml.safe_dump(pk), encoding="utf-8")
    for fail in (False, True):
        if fail:
            data = yaml.safe_load(targets.read_text(encoding="utf-8"))
            data["targets"]["auc"]["value"] = 1
            targets.write_text(yaml.safe_dump(data), encoding="utf-8")
        result = run_workflow(sim_full_csv=sim, pk_yml=pk_path, targets_yml=targets, spec_yml=spec, out_dir=tmp_path / str(fail), times_h=[0, 1, 2, 3])
        context = yaml.safe_load(result.files["manifest"].read_text(encoding="utf-8"))["fixture_context"]
        assert context["simulation_validity"]["status"] == "clinical_hold"
        assert context["clinical_use"] == "not_approved"


def test_repeated_demo_independent_manifests_preserve_hold(tmp_path):
    from tools.run_repeated_oral_demo import run_repeated_oral_demo

    config = yaml.safe_load((ROOT / "harness_examples/demo_repeated_oral_trough_ss_50.yml").read_text(encoding="utf-8"))
    config["simulation"]["n_subjects"] = 1
    result = run_repeated_oral_demo(config=config, out_dir=tmp_path / "repeat", drugs_dir=ROOT / "drugs")
    for key in ("manifest", "workflow_manifest", "sdtm_manifest", "analysis_manifest"):
        context = yaml.safe_load(result.files[key].read_text(encoding="utf-8"))["fixture_context"]
        assert context["simulation_validity"]["status"] == "clinical_hold"
        assert context["clinical_dose_verified"] is False


def test_direct_r_manifest_preserves_canonical_hold(tmp_path):
    import json
    import shutil
    import subprocess

    if not shutil.which("Rscript"):
        pytest.skip("Rscript not available")
    check = subprocess.run(["Rscript", "-e", "quit(status=ifelse(requireNamespace('yaml',quietly=TRUE)&&requireNamespace('mrgsolve',quietly=TRUE),0,1))"], capture_output=True)
    if check.returncode:
        pytest.skip("R yaml/mrgsolve unavailable")
    manifest = tmp_path / "r-manifest.yml"
    spec_path = ROOT / "drugs/felodipine/spec_pk1_oral.yml"
    script = f'''expressions <- parse({json.dumps(str(ROOT / 'tools/mrgsolve_runner.R'))})
for (expression in head(expressions, -1)) eval(expression)
spec_path <- {json.dumps(str(spec_path))}
spec <- yaml::read_yaml(spec_path)
write_manifest({json.dumps(str(manifest))}, spec_path, "simulation.csv", NULL, spec, "oral", data.frame(ID=1), c(0,1), 1L, 12, 1L, TRUE)
'''
    completed = subprocess.run(["Rscript", "-e", script], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    context = yaml.safe_load(manifest.read_text(encoding="utf-8"))["fixture_context"]
    from tools.export_fixture_context import resolve_fixture_context

    expected = resolve_fixture_context(spec_path)
    assert context["simulation_validity"] == expected["simulation_validity"]
    assert context["clinical_use"] == expected["clinical_use"]
    assert context["half_life_check"]["hold_candidate"] == expected["half_life_check"]["hold_candidate"]
    assert context["half_life_check"]["ratio"] == pytest.approx(expected["half_life_check"]["ratio"])


@pytest.mark.parametrize("tamper", ["approved", "partial"])
def test_analysis_rejects_conflicting_or_partial_pc_context(tmp_path, tamper):
    sdtm = generated(tmp_path)
    path = sdtm.files["PC"]
    pc = rows(path)
    if tamper == "approved":
        pc[0]["CLINICAL_USE"] = "approved"
    else:
        pc[0]["CLINICAL_USE"] = ""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(pc[0]))
        writer.writeheader()
        writer.writerows(pc)
    with pytest.raises(ValueError, match="context"):
        make_analysis_inputs(sdtm_like_dir=sdtm.out_dir, out_dir=tmp_path / "analysis")


def test_sdtm_rejects_known_hold_on_samples_when_standalone_spec_has_no_context(tmp_path):
    from tools.export_fixture_context import attach_context, resolve_fixture_context

    clinical = tmp_path / "clinical.csv"
    write_clinical_samples(clinical)
    samples = rows(clinical)
    attach_context(samples, resolve_fixture_context(ROOT / "drugs/felodipine/spec_pk1_oral.yml"))
    with clinical.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(samples[0]))
        writer.writeheader()
        writer.writerows(samples)
    standalone = tmp_path / "spec.yml"
    standalone.write_bytes((ROOT / "drugs/felodipine/spec_pk1_oral.yml").read_bytes())
    with pytest.raises(ValueError, match="context"):
        make_sdtm_like_domains(clinical_samples_csv=clinical, spec_yml=standalone, out_dir=tmp_path / "sdtm")
