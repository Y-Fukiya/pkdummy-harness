# README-only user test report

このテンプレートは、第三者がREADMEだけを見て迷わず動かせるかを記録するためのものです。

Generated data are workflow fixtures, not for clinical inference, dose selection, or regulatory model qualification.

## Tester

| Item | Value |
| --- | --- |
| Tester | |
| Date | |
| OS | Windows PowerShell / macOS/Linux |
| Shell | |
| Python | |
| R / Quarto | |
| simPop | Installed / Missing / Not checked |

## Commands run

### Preflight

```bash
python -m tools.pk_fixture_cli doctor
```

Observed result:

```text
paste output here
```

### Core run

```bash
python -m tools.pk_fixture_cli run harness_examples/demo_set.yml
```

Observed result:

```text
paste output here
```

### Full acceptance check

macOS/Linux:

```bash
make acceptance-check
```

Windows PowerShell:

```powershell
.\scripts\acceptance-check.ps1 -SkipExternalProbe
```

Observed result:

```text
paste output here
```

## Output review

| Artifact | Checked | Notes |
| --- | --- | --- |
| `outputs/demo_set_config/summary.md` |  |  |
| `HARNESS_MANIFEST.yml` |  |  |
| `MANIFEST.yml` |  |  |
| `ADPC.csv` |  |  |
| `NCA_INPUT.csv` |  |  |
| `POPPK_INPUT.csv` |  |  |
| `simulation_validation.md` |  |  |

## Questions asked by tester

| Question | README/doc location that should answer it | Follow-up needed |
| --- | --- | --- |
|  |  |  |

## Pass criteria

- Tester can run demo set without live support.
- Tester can explain that the output is a workflow fixture and not for clinical inference.
- Tester can find Windows PowerShell instructions when `make` is unavailable.
- Tester can identify where external Phoenix/NONMEM/nlmixr2 validation would be configured.
- Any confusion is recorded above with a doc improvement action.
