# F-corrected oral profiles (systemic-basis drugs)

The nine oral drugs whose basis was corrected to `systemic`
(docs/BASIS_WORKLIST_RESOLUTION.md) keep, in their DEFAULT spec, `theta.F1 = 1.0`
with `theta.CL` set to the systemic clearance. The default simulated exposure is
therefore `Dose / CL_systemic` — it treats the systemic CL as if it were an
apparent `CL/F`. That is acceptable as an internal fixture but is inconsistent
with the declared systemic basis.

`tools/make_calibrated_oral_spec.py` emits a SEPARATE profile per drug under
`profiles/<slug>_oral_systemic_basis.yml`. The only parameter change is
`theta.F1 = bioavailability` (CL stays the systemic value), so the simulated
exposure becomes `F * Dose / CL_systemic`, consistent with "systemic CL +
bioavailability". Because `CL_abs == CL_systemic` for a systemic-basis drug, no
other theta change is needed.

These profiles live under `profiles/` (outside `drugs/`) on purpose: `run_demo_set`
and `run_workflow` require exactly one `spec_pk1_*.yml` per drug directory, so a
second spec inside `drugs/<slug>/` would break the pipeline. The profiles do not
participate in the default workflow; they are an opt-in alternative.

Important: these remain fixture TEMPLATES, not clinically validated PK models.
The F-correction makes the parameterization internally consistent with the
systemic basis; it does not calibrate against observed clinical data.

## Commands

    python tools/make_calibrated_oral_spec.py . --write     # (re)write profiles
    python tools/make_calibrated_oral_spec.py . --check      # drift lock (CI)
    python tools/make_calibrated_oral_spec.py . --drug aciclovir   # print one

`--check` is wired into `make harness-check` so the committed profiles cannot
drift from the generator.

## Exposure relationship

For each profile, simulated `AUC0-inf(profile) == F * AUC0-inf(default)` exactly
(F1 scales concentrations linearly), and `AUC0-inf(profile) ~= F * Dose /
CL_systemic` within the dense-grid trapezoid bias. Both are checked in
`tests/test_calibrated_profiles.py`.
