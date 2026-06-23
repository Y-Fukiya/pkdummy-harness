# Changelog

All notable changes to pkdummy-harness are recorded here. The format is loosely
based on Keep a Changelog. Per-release narrative notes live under
`docs/releases/`; this file is the single chronological index. Because the
harness is a fixture generator whose value is reproducibility and auditability,
changes to the validation recalculation method (the trust anchor) and to the
drug library's derived semantics are called out explicitly.

## [Unreleased]

## [0.11.0] - 2026-06-24

### Added
- `tools/check_derived_drift.py`: diagnoses divergence between committed pk.yml
  `derived` blocks and `derive_quantities`; `--strict` is wired into
  `make harness-check` as a regression lock.
- `tools/regen_derived.py`: deterministic regeneration of `derived` from
  `pk_parsed` (`--write`) with a dry-run unified diff.
- Independent closed-form ground-truth tests for the NCA recalculation
  (`tests/test_nca_recalc_ground_truth.py`), an optional PKNCA differential hook
  (skipped unless rpy2 is present).
- Harmonic-mean (and geometric-mean) summary support for terminal half-life;
  `summary: harmonic_mean` / `geometric_mean` are now honored instead of silently
  falling back to the arithmetic mean.
- `harness_version` and `nca_recalc_method` are stamped into every validation
  summary so a fixture self-describes the version and method that produced it.
- Coverage for the ug/mL (biologic) AUC unit path and a days-scale terminal
  half-life fixture.
- Library-validation warning for oral drugs whose source clearance uses a
  systemic-style unit but was treated as apparent; silence per drug with
  `pk_parsed.clearance_basis_source: confirmed`.
- `tools/make_calibrated_oral_spec.py` + `profiles/<slug>_oral_systemic_basis.yml`:
  F-corrected oral profiles for the nine systemic-basis drugs (theta.F1 set to
  label bioavailability so exposure is F*Dose/CL_systemic). Profiles live under
  `profiles/` (outside `drugs/`) so they never collide with the one-spec-per-drug
  rule; `--check` is wired into `make harness-check` as a drift lock. Still fixture
  templates, not clinically validated. See `docs/CALIBRATED_PROFILES.md`.
- Lint gate: added ruff (rules E, F, W; E501 line-length and E402 are not
  enforced — E402 is expected from the sys.path bootstrap). Cleaned up unused
  imports/variables and a few style nits across tools/ and tests/. `make lint`
  and a dedicated CI `lint` job run `ruff check .`; harness-check stays
  dependency-light (PyYAML + pytest) and does not require ruff.
- CI now runs the Ubuntu harness on Python 3.10, 3.11, 3.12, and 3.13.

### Changed
- Treated as a git-checkout / Makefile tool (not pip-distributed): removed the
  `pk-fixture` console script; the CLI is invoked as `python -m tools.pk_fixture_cli`
  from the repository root. README/docs/help updated; pyproject documents that the
  wheel ships `tools/` only (no drug-library data).
- Dependency hygiene: core runtime is PyYAML only; requests/lxml (harvest) and
  pandas (jobs) moved to optional extras; requirements.txt slimmed and
  requirements-dev.txt de-duplicated; CI installs requirements-dev.txt; pyproject
  version is dynamic from tools.__version__; Python 3.11-3.13 classifiers added.
- Canonical ke is now CL/V. `validate_library` checks `derived.ke == CL_abs/V_abs`
  (the convention the simulator obeys); the t_half-vs-CL/V discrepancy remains a
  1-compartment attainability warning. See `docs/DERIVED_DRIFT_DECISIONS.md`.
- All 37 `pk.yml` `derived` blocks regenerated under the CL/V convention with an
  explicit, persisted `clearance_basis` (route-auto default: oral -> apparent,
  iv -> systemic). `CL_systemic` values are unchanged where bioavailability is
  known; `ke` now reflects CL/V and `CL_apparent`/`V_apparent` are populated.

### Fixed
- Oral CL basis worklist resolved: the nine oral drugs whose source clearance
  used a mL/min-family unit (aciclovir, alprazolam, cimetidine, felodipine,
  itraconazole, montelukast, omeprazole, triazolam, verapamil) are re-labelled
  `clearance_basis: systemic` (provenance `unit_inferred`). `CL_systemic` now
  holds the source value instead of the inverted `CL_abs*F`, and `CL_apparent =
  CL/F` is populated. Specs are untouched, so fixture profiles are unchanged;
  only the basis metadata is corrected. `validate_library` consistency checks are
  now basis-aware (systemic vs apparent). See `docs/BASIS_WORKLIST_RESOLUTION.md`.

## [0.10.4] and earlier

See `docs/releases/` for prior per-release notes.
