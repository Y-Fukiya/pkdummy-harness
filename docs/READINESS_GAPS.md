# Readiness Gaps

This file tracks high-value validation steps that need external people, operating systems, or licensed tools.

Generated data are workflow fixtures only. They are not for clinical inference, dose selection, or regulatory model qualification.

## Current Status

| Item | Status | Why it remains open | Evidence or next action |
| --- | --- | --- | --- |
| README-only user test | Needs independent tester | Codex can run commands, but cannot substitute for a third-party first-use read-through | Ask a tester to use only `README.md` and fill `docs/USER_TEST_REPORT_TEMPLATE.md` |
| Windows real-machine PowerShell smoke | Covered by CI, needs real user environment | GitHub Actions checks Windows behavior, but not a local Windows shell with user-installed tools | Run `.\scripts\harness-check.ps1 -SkipExternalProbe` and `.\scripts\acceptance-check.ps1 -SkipExternalProbe` on Windows |
| Phoenix execute validation | Needs licensed Phoenix environment | The repository intentionally does not bundle external tools or licenses | Configure `external_validation/tool_profiles.yml` and run `tools/run_external_tool_validation.py --execute` |
| NONMEM execute validation | Needs licensed NONMEM environment | Probe-only checks cannot confirm a production `nmfe` run | Configure the NONMEM command and run the external validation profile with `--execute` |
| nlmixr2 execute validation | Needs R/nlmixr2 environment suitable for package compilation and execution | Repository smoke checks can verify parser fixtures, not full estimation workflows | Run external validation with `--tools nlmixr2 --execute` |
| Value-level source review | Machine-readable provenance exists, exact value-to-source mapping still needs human review | Existing source URL lists do not always identify which source supplied each CL/V/t_half value; a small number of t_half fields now resolve to source IDs | Run `python tools/check_value_provenance.py . --report`, review warning-drug `source_id: null` entries, and replace only when the exact source can be verified |

## Local Evidence Already Available

- `make harness-check` covers library integrity, pytest, regeneration checks, example checks, downstream smoke, site adapter generation, and external validation probe.
- `python tools/check_value_provenance.py .` verifies warning-drug CL/V/t_half provenance schema, canonical normalized values, source-id resolution for non-null IDs, and acknowledged t_half fixture limitations.
- GitHub Actions runs Ubuntu harness checks and Windows PowerShell smoke checks.
- Release notes should record which of the external items above were completed for each release.
