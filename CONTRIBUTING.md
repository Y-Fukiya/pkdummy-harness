# Contributing

Thank you for helping improve `pkdummy-harness`.

This repository creates PK-like workflow fixtures for SDTM/ADaM/NCA/PopPK pipeline testing. Generated data are not for clinical inference, dose selection, or regulatory model qualification.

## Ground Rules

- Read `AGENTS.md` before making changes.
- Do not invent, smooth, round, or infer PK values without a traceable source.
- Keep `pk_raw`, `sources`, `pk_parsed`, and `derived` aligned when editing `drugs/<slug>/pk.yml`.
- Treat oral CL/V values as apparent CL/F and V/F unless bioavailability and the conversion basis are documented.
- Do not commit `__pycache__`, `.DS_Store`, `._*`, `.pytest_cache`, `outputs/`, or temporary artifacts.

## Local Checks

Run this before starting substantial work:

```bash
make validate
```

Run this before submitting changes:

```bash
make harness-check
```

If a check fails, include the failure, cause, and remaining work in your change notes.

## Pull Request Scope

Small, reviewable changes are preferred.

- Documentation-only changes should avoid touching PK data files.
- Parser, unit conversion, or generation logic changes should include focused tests.
- Changes to `INDEX.csv`, `EXCLUDED.csv`, `pk_library.yml`, or `drugs/*/*.yml` must summarize exactly what changed.
- Source URLs, raw PK text, existing drug names, and slugs should not be changed unless correcting a clear error.

## Release Checklist

Use `docs/VALIDATION_AND_RELEASE_CHECKLIST.md` for release readiness. Release notes should clearly state that the outputs are workflow fixtures and not clinical or regulatory evidence.
