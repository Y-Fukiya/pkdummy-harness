# pkdummy-harness

*English | [日本語](README.ja.md)*

[![CI](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/codeql.yml/badge.svg)](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/codeql.yml)
[![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A safe, deterministic **fixture generator** for CDISC PK pipelines. It produces
structurally consistent SDTM/ADaM/NCA/PopPK *workflow fixtures* from a small
1-compartment model — for **building and testing downstream tooling**, not for
clinical inference, dose selection, or regulatory model qualification.

> **Safe by design:** no patient data, no IP, fully deterministic and
> reproducible. That boundary is the point — see "Scope" below.

---

## Why this exists

Validating an SDTM → ADaM → NCA/PopPK pipeline needs realistic-*shaped* inputs,
but real patient data carries privacy and IP constraints and is slow to obtain.
`pkdummy-harness` gives you fixtures with the right structure and plausible PK
shapes, from a single input set, that you can regenerate byte-for-byte.

- Reproducible SDTM/ADaM-like intermediates from one input set.
- Built-in recalculation checks (AUC / Cmax / Tmax / t½) over the generated data.
- Thin adapter CSVs to feed NCA / PopPK tools.
- `pk.yml` / `targets.yml` are **never auto-edited**; a manifest and trace log
  keep every run auditable.
- Works with existing site data shapes (DM / LB / VS / PC).

Typical uses: input fixtures for downstream parsers and conformance engines,
fixed CI inputs and smoke tests, and demos / onboarding without any data
sensitivity.

---

## What it generates

- Drug PK parameters: `drugs/<slug>/pk.yml`
- Targets (AUC / t½ etc.): `drugs/<slug>/targets.yml`
- 1-compartment simulation spec: `drugs/<slug>/spec_pk1_*.yml`
- Run definitions: `harness_examples/*.yml`

Flow diagrams: [docs/assets/pk-harness-process.drawio](docs/assets/pk-harness-process.drawio),
the end-to-end view [docs/assets/pk-fixture-end-to-end-workflow.drawio](docs/assets/pk-fixture-end-to-end-workflow.drawio),
and how to read them in [docs/PROCESS_FLOW.md](docs/PROCESS_FLOW.md).

---

## Quickstart

This is a **git-checkout tool** (not published to PyPI). Clone it, install the
dependencies, and run via `make` or `python -m tools.pk_fixture_cli` **from the
repository root**.

```bash
python3 -m pip install -r requirements-dev.txt   # core (PyYAML) + pytest
make harness-check
```

```bash
python3 -m tools.pk_fixture_cli doctor
python3 -m tools.pk_fixture_cli run harness_examples/demo_set.yml
```

The core runtime is PyYAML only. Optional tool groups install via extras:
`pip install .[harvest]` (web harvesting: DailyMed/PubMed) and
`pip install .[jobs]` (job/excluded CSV utilities).

> The published wheel/sdist ships `tools/` code only — **not** the drug library
> (`drugs/`, `pk_library.yml`, `templates/`, ...). A plain `pip install` therefore
> has no data to run against. An editable install (`pip install -e .`) works
> because the data lives in the checkout; run from the repository root.

If you have an external mrgsolve run, post-process an existing `sim_full.csv`:

```bash
python3 tools/run_workflow.py \
  --sim-full outputs/<run>/raw/sim_full.csv \
  --drug <slug> \
  --times 0,0.5,1,2,4,8,12,24 \
  --out-dir outputs/<run>/workflow
```

`run_workflow.py` also accepts `--schedule-csv` for existing sampling times and
`--dm-csv/--vs-csv/--lb-csv/--pc-csv` to reuse existing DM/LB/VS/PC skeletons.

---

## Output shape

```text
outputs/<run>/workflow/
  MANIFEST.yml
  trace.log
  raw/clinical_samples.csv
  reports/simulation_validation.md
  reports/pk_fixture_report/REPORT.md
  sdtm_like/{DM,VS,LB,EX,PC}.csv
  analysis_inputs/{ADPC,NCA_INPUT,POPPK_INPUT}.csv
  adapters/*.csv
```

### Sample: small molecule (hours scale)

`examples/minimal_aciclovir/workflow/analysis_inputs/ADPC.csv`:

```csv
STUDYID,USUBJID,PARAMCD,AVAL,AVALU,TIME_H,MDV,BLQ,EXTRT,DOSE_MG,ROUTE
EXAMPLE,EXAMPLE-001,CONC,0,ng/mL,0,0,0,ACICLOVIR,100,ORAL
EXAMPLE,EXAMPLE-001,CONC,950,ng/mL,1,0,0,ACICLOVIR,100,ORAL
```

### Sample: biologic / mAb (days-to-weeks scale)

`examples/minimal_cda1_mab_iv/` is a long-half-life monoclonal antibody fixture
(CDA1, fixture terminal t½ ≈ 24 days), sampled out to 84 days so the slow
terminal decline is visible:

```csv
STUDYID,USUBJID,PARAMCD,AVAL,AVALU,TIME_H,MDV,BLQ,EXTRT,DOSE_MG,ROUTE
OSP_cda1,OSP_cda1-001,CONC,20408.163265,ng/mL,0,0,0,CDA1,100,INTRAVENOUS
OSP_cda1,OSP_cda1-001,CONC,19828.791167,ng/mL,24,0,0,CDA1,100,INTRAVENOUS
OSP_cda1,OSP_cda1-001,CONC,9111.478396,ng/mL,672,0,0,CDA1,100,INTRAVENOUS
OSP_cda1,OSP_cda1-001,CONC,1816.179249,ng/mL,2016,0,0,CDA1,100,INTRAVENOUS
```

`sdtm_like/` is the source of truth; `analysis_inputs/` is regenerated from it and
checked for drift by `python -m tools.check_examples`.

**Status:** `OK` (within standard checks) / `WARN` (usable, cause noted) /
`FAILED` (stop by default; override with `--allow-validation-failed`).

The run-level `MANIFEST.yml` also records machine-readable target caveats under
`target_metadata`, including whether the AUC target is `dose_over_cl` rather
than an independent literature AUC, and whether `t_half` has a known CL/V
structural mismatch for the 1-compartment fixture.

---

## Scope

This harness is **not** a clinical prediction model. The following belong to a
separate analysis layer:

- Dose selection / dosing design / regulatory model qualification.
- Justifying covariate models (age/weight/sex) or non-linear PK.
- Rigorous reproducibility evaluation with IIV/residual (current focus is fixtures).

`targets.auc.value` is typically `Dose/CL`-derived and should not be equated with
a precise literature AUC. The model is intentionally a 1-compartment analytic
solution; the NCA recalculation is a sanity check, not an NCA engine. Some
fixtures intentionally keep a `t_half` target that cannot be exactly reconciled
with the chosen CL/V pair; those cases are labeled in `targets.yml`, validation
warnings, and workflow manifest `target_metadata`.

Optional `profiles/*_oral_systemic_basis.yml` give exposure consistent with
systemic CL + bioavailability for the systemic-basis oral drugs (still fixture
templates) — see [docs/CALIBRATED_PROFILES.md](docs/CALIBRATED_PROFILES.md).

---

## License & data boundary

- Code and docs are released under the [MIT License](LICENSE).
- External sources (DailyMed, PubMed, OSP PBPK Model Library, ...) are references;
  upstream terms apply to their content.
- External tool binaries, commercial licenses, site SOPs, and real patient data
  are **not** included.
- Generated CSVs/templates are workflow fixtures, not submission-ready SDTM/ADaM,
  clinical inference, dosing design, or regulatory model-qualification evidence.

---

## Docs

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): day-to-day operations
- [docs/QUICKSTART.md](docs/QUICKSTART.md): short first-run order
- [docs/index.md](docs/index.md): GitHub Pages docs entry
- [docs/ACCEPTANCE_TEST.md](docs/ACCEPTANCE_TEST.md): README-only third-party check
- [docs/DOWNSTREAM_E2E.md](docs/DOWNSTREAM_E2E.md): NCA/PopPK downstream smoke
- [docs/EXTERNAL_TOOL_VALIDATION_GUIDE.md](docs/EXTERNAL_TOOL_VALIDATION_GUIDE.md): Phoenix/NONMEM/nlmixr2 runs
- [docs/SITE_ADAPTER_GUIDE.md](docs/SITE_ADAPTER_GUIDE.md): per-site CSV adapters
- [docs/CALIBRATED_PROFILES.md](docs/CALIBRATED_PROFILES.md): F-corrected oral profiles
- [docs/USER_TEST_REPORT_TEMPLATE.md](docs/USER_TEST_REPORT_TEMPLATE.md): user test report template
- [docs/VALIDATION_AND_RELEASE_CHECKLIST.md](docs/VALIDATION_AND_RELEASE_CHECKLIST.md): pre-release checks
- [docs/RELEASE_NOTES_TEMPLATE.md](docs/RELEASE_NOTES_TEMPLATE.md): release-notes template
- [docs/WINDOWS_POWERSHELL.md](docs/WINDOWS_POWERSHELL.md): Windows run steps
- [docs/CODEX_HARNESS.md](docs/CODEX_HARNESS.md): Codex operation notes
- [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) · [CITATION.cff](CITATION.cff) · [CHANGELOG.md](CHANGELOG.md)

---

## Design principles

1. **Never break canonical inputs** — `pk.yml`, `targets.yml`, `spec` are not auto-updated.
2. **Reproducibility first** — seed, manifest, trace, and logs fix every run.
3. **Connectivity first** — downstream NCA/PopPK quirks are absorbed by site adapters; the harness focuses on fixtures and validation.
4. **Separate validation from clinical use** — this repo makes data-shaped fixtures; clinical qualification lives in another layer.

---

## In one line

A tool for building the fast, hard-to-break validation plumbing *first*, so
implementers, statisticians, and clinical pharmacologists can argue from the same
logs while the real analysis model is developed elsewhere.
