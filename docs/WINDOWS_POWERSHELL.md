# Windows PowerShell Guide

この手順は、Windowsで `make` を使わずにPK fixture harnessを動かすための最短ガイドです。

このハーネスが作るデータは SDTM/ADaM/NCA/PopPK workflow fixture 用です。Generated data are not for clinical inference, dose selection, or regulatory model qualification.

## 1. Python環境

PowerShellを開き、リポジトリ直下で実行します。

```powershell
py -3.11 --version
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Python launcherを使わない環境では、同じ意味で次のように作成しても構いません。

```powershell
python -m venv .venv
```

もしPowerShellの実行ポリシーでactivateやscript実行が止まる場合、そのセッション内だけ許可します。

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## 2. CLI確認

まず軽い確認だけ行います。

```powershell
python -m tools.pk_fixture_cli --help
python -m tools.pk_fixture_cli doctor
python -m tools.pk_fixture_cli run harness_examples/demo_set.yml
```

editable install後は次の形でも呼べます。

```powershell
python -m pip install -e .
python -m tools.pk_fixture_cli doctor
python -m tools.pk_fixture_cli run harness_examples/demo_set.yml
```

## 3. Makeなしの検証

Unix/macOSでは `make harness-check` を使います。Windowsでは同等のPowerShell wrapperを使えます。

```powershell
.\scripts\harness-check.ps1
```

外部Phoenix/NONMEM/nlmixr2 probeを飛ばして、Windows上の基本動作だけ確認する場合:

```powershell
.\scripts\harness-check.ps1 -SkipExternalProbe
```

README-only受け入れ確認に近い形で、harness check後にdoctorも実行する場合:

```powershell
.\scripts\acceptance-check.ps1 -SkipExternalProbe
```

Python launcherを明示したい場合:

```powershell
.\scripts\harness-check.ps1 -Python py -PythonArgs "-3.11" -SkipExternalProbe
```

## 4. R / Quarto / simPop

中核CLIとCSV fixture生成にRは必須ではありません。`doctor` で `simPop` がWARNでも、既存fallback subject fixtureを使って `DM/VS/LB/EX/PC` は作れます。

Rを使うのは主に次の任意機能です。

| Optional feature | Requirement |
| --- | --- |
| ggplot report | R, ggplot2 |
| Quarto DOCX report | R, ggplot2, Quarto |
| simPop subject CSV | R, simPop |

WindowsでR packageにC/C++/Fortranコンパイルが必要な場合、Rtoolsが必要になることがあります。simPopは任意依存なので、RtoolsやsimPopの導入で詰まる場合でも、まずは `python -m tools.pk_fixture_cli run ...` と `.\scripts\harness-check.ps1 -SkipExternalProbe` で中核workflowを確認してください。

## 5. External tools on Windows

Phoenix, NONMEM, nlmixr2本体やライセンスはこのrepoに含めません。施設環境で検証する場合は `external_validation/tool_profiles.yml` をコピーまたは編集し、Windows上の実コマンド名や絶対パスに合わせます。

例:

```powershell
python tools/run_external_tool_validation.py `
  --downstream-dir outputs/downstream_smoke_check/minimal_aciclovir `
  --out-dir outputs/external_validation_probe/minimal_aciclovir `
  --tools nonmem,nlmixr2
```

実行まで行う場合だけ `--execute` を付けます。

```powershell
python tools/run_external_tool_validation.py `
  --downstream-dir outputs/downstream_smoke_check/minimal_aciclovir `
  --out-dir outputs/external_validation_probe/minimal_aciclovir `
  --tools nonmem,nlmixr2 `
  --execute
```

`SKIPPED` は実行ファイルが見つからないという意味です。repoのfixture harnessが壊れているとは限りません。

## 6. 推奨するWindows確認順

1. `python -m tools.pk_fixture_cli --help`
2. `python -m tools.pk_fixture_cli doctor`
3. `python -m tools.pk_fixture_cli run harness_examples/demo_set.yml`
4. `.\scripts\harness-check.ps1 -SkipExternalProbe`
5. 施設ツールがある場合だけ `run_external_tool_validation.py --execute`

この順であれば、Python/CSV fixtureの問題と、R/Quarto/simPop/外部商用ツールの問題を切り分けやすくなります。
