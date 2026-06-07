# Release notes template

## Version

`vX.Y.Z`

## Date

`YYYY-MM-DD`

## Commit

`<git sha>`

## Scope

This release is for a CLI/config-driven synthetic PK workflow fixture harness. Generated data are not for clinical inference, dose selection, or regulatory model qualification.

## Changes

- 

## Verification matrix

| Check | Environment | Result | Evidence |
| --- | --- | --- | --- |
| `make validate` | macOS/Linux |  |  |
| `make harness-check` | macOS/Linux |  |  |
| `make acceptance-check` | macOS/Linux |  |  |
| Windows PowerShell smoke | Windows |  | `.\scripts\harness-check.ps1 -SkipExternalProbe` |
| GitHub Actions Ubuntu | CI |  | run id |
| GitHub Actions Windows | CI |  | run id |
| README-only user test | tester environment |  | `USER_TEST_REPORT_TEMPLATE.md` |

## External tool validation

| Tool | Status | Evidence |
| --- | --- | --- |
| Phoenix | Not run / Probe / Execute | `EXTERNAL_TOOL_VALIDATION.yml` |
| NONMEM | Not run / Probe / Execute | `EXTERNAL_TOOL_VALIDATION.yml` |
| nlmixr2 | Not run / Probe / Execute | `EXTERNAL_TOOL_VALIDATION.yml` |

## Known limitations

- The harness creates workflow fixtures, not clinically validated PK predictions.
- Phoenix / NONMEM / nlmixr2 licenses and production projects are not bundled.
- Site-specific ADaM/NCA/PopPK dataset conventions may require adapter edits.
- simPop is optional; missing simPop does not block core CSV fixture generation.

## Tag command

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z PK fixture harness"
git push origin vX.Y.Z
```
