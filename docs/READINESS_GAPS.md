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

## Local Evidence Already Available

- `make harness-check` covers library integrity, pytest, regeneration checks, example checks, downstream smoke, site adapter generation, and external validation probe.
- GitHub Actions runs Ubuntu harness checks and Windows PowerShell smoke checks.
- Release notes should record which of the external items above were completed for each release.
