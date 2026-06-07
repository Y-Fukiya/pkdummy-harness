# Validation And Release Checklist

このチェックリストは、現状の残り5%をrepo内で詰めるための運用メモです。

対象は CLI/config-driven synthetic PK fixture harness です。Generated data are not for clinical inference, dose selection, or regulatory model qualification.

## 1. README-only user test

第三者にREADMEだけを見て実行してもらう場合、次を記録します。
記録用テンプレートは [USER_TEST_REPORT_TEMPLATE.md](USER_TEST_REPORT_TEMPLATE.md) です。

| Item | Expected evidence |
| --- | --- |
| Setup | Python version, OS, shell, install command |
| Preflight | `python -m tools.pk_fixture_cli doctor` output |
| Core run | `python -m tools.pk_fixture_cli run harness_examples/demo_set.yml` |
| Harness check | `make harness-check` or `.\scripts\harness-check.ps1 -SkipExternalProbe` |
| Output review | `summary.md`, `MANIFEST.yml`, `ADPC.csv`, `NCA_INPUT.csv`, `POPPK_INPUT.csv` |
| Confusion points | README line or command that caused hesitation |

Passの目安は、ユーザーが質問なしでdemo setを作成し、fixture用途と臨床推論不可の境界を説明できることです。

## 2. External Phoenix / NONMEM / nlmixr2 validation

外部ツール本体やライセンスはrepoに同梱しません。施設環境で `external_validation/tool_profiles.yml` を編集し、`EXTERNAL_TOOL_VALIDATION.yml` を証跡として残します。
詳細手順は [EXTERNAL_TOOL_VALIDATION_GUIDE.md](EXTERNAL_TOOL_VALIDATION_GUIDE.md) です。
Windowsのprofile記入例は `external_validation/tool_profiles.windows.example.yml` です。

| Tool | What to confirm | Notes |
| --- | --- | --- |
| Phoenix | adapter CSVの取り込み、NCA project templateへの列対応 | GUI操作は施設SOP側で管理 |
| NONMEM | `nmfe75` などの実command名、control stream、`.lst` 生成 | Windowsではpathやlicense server設定を明示 |
| nlmixr2 | package import、parser/estimation scriptの実行 | R package compileが必要な場合はRtoolsが関係 |

Probeのみ:

```bash
python tools/run_external_tool_validation.py \
  --downstream-dir outputs/downstream_smoke_check/minimal_aciclovir \
  --out-dir outputs/external_validation_probe/minimal_aciclovir
```

実行あり:

```bash
python tools/run_external_tool_validation.py \
  --downstream-dir outputs/downstream_smoke_check/minimal_aciclovir \
  --out-dir outputs/external_validation_probe/minimal_aciclovir \
  --tools nonmem,nlmixr2 \
  --execute
```

## 3. Site-specific dataset mapping

施設ごとのADaM/NCA/PopPK dataset仕様は `external_validation/site_adapter_template.yml` をコピーして管理します。
見直し手順は [SITE_ADAPTER_GUIDE.md](SITE_ADAPTER_GUIDE.md) にまとめています。

確認すること:

- source dataset: `ADPC.csv`, `NCA_INPUT.csv`, `POPPK_INPUT.csv`
- required columns: site側で必須非欠損にする列
- constants: study-specific fixed values
- rename: site-specific column names
- output evidence: `SITE_ADAPTER_MANIFEST.yml`

このadapterはsubmission-ready ADaMや正式Phoenix/NONMEM datasetを保証するものではありません。施設仕様への最後の列調整をrepo内で見える化する層です。

## 4. Windows / PowerShell / Rtools

Windowsでは `make` 前提にせず、PowerShell scriptを使います。

```powershell
.\scripts\harness-check.ps1 -SkipExternalProbe
.\scripts\acceptance-check.ps1 -SkipExternalProbe
```

R, Quarto, simPopは任意機能です。simPopや一部R packageの導入時にC/C++/Fortran compileが必要な場合はRtoolsが必要になることがあります。

Windowsで最初に保証したいのは、RtoolsなしでもPython CLIとCSV fixture生成が動くことです。

## 5. Private release / tag

private GitHub repoで共有する場合は、release tagの前に次を確認します。
release noteのひな形は [RELEASE_NOTES_TEMPLATE.md](RELEASE_NOTES_TEMPLATE.md) です。

1. `make harness-check` on macOS/Linux
2. `.\scripts\harness-check.ps1 -SkipExternalProbe` on Windows PowerShell
3. GitHub Actions green on Ubuntu and Windows smoke
4. README-only user test result
5. Known limitations are unchanged and visible

tag例:

```bash
git tag -a v0.10.2 -m "Release v0.10.2 PK fixture harness"
git push origin v0.10.2
```

release noteには「workflow fixture用であり、clinical inferenceやdose selectionには使わない」ことを明記します。
