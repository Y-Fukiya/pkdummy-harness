# pkdummy-harness

[![CI](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/codeql.yml/badge.svg)](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

臨床試験の実データ風PKデータは「正確な患者生体内動態」ではなく、**SDTM→ADaM→NCA/PopPK ワークフローを検証するための配管テスト用データ**として必要になります。`pkdummy-harness` はそのための**CLIツール群**です。

---

## 1分でわかるこのハーネスの価値

- SDTM/ADaM風の中間データを、入力データ1セットから再現性高く作れる
- 生成データに対して AUC/Cmax/Tmax/t1/2 の再計算チェックを自動実行できる
- NCA / PopPK につなぐための薄い adapter CSV をまとめて作れる
- `pk.yml` や `targets.yml` は**勝手に書き換えず**、検証ログと結果を残して監査しやすい
- 既存の研究施設のデータ形式（DM/LB/VS/PC）を使ったスキームにも対応できる

**アピールポイント**
- パイプラインを短いコマンドで通せる（デモ→検証→下流adapter→レポート）
- 研究現場でよく困る「見出し不足」「欠損時刻」「検証ログの不整合」を、manifest と trace で固定できる
- 外部ツール依存を分離し、mrgsolve実行と後処理を切り分けて安全に運用できる

---

## どういうデータを作る？

- 薬剤のPKパラメータ: `drugs/<slug>/pk.yml`
- 目標値(AUC/t1/2など): `drugs/<slug>/targets.yml`
- 1-compartmentの簡易シミュレーション仕様: `drugs/<slug>/spec_pk1_*.yml`
- 実行定義: `harness_examples/*.yml`

### フローの全体像（draw.io）

- 処理本体: [docs/assets/pk-harness-process.drawio](docs/assets/pk-harness-process.drawio)
- 末端まで含めた全体: [docs/assets/pk-fixture-end-to-end-workflow.drawio](docs/assets/pk-fixture-end-to-end-workflow.drawio)
- 図の読み方: [docs/PROCESS_FLOW.md](docs/PROCESS_FLOW.md)

---

## まず実行してみる（最短）

このツールは **git チェックアウト前提**で使います（PyPI 配布はしていません）。クローンして依存を入れ、`make` か `python -m tools.pk_fixture_cli` で実行します。

まず環境整合を確認:

```bash
python3 -m pip install -r requirements-dev.txt   # コア(PyYAML)+pytest
make harness-check
```

CLI 入口として使う場合（リポジトリのルートで実行）:

```bash
python3 -m tools.pk_fixture_cli doctor
python3 -m tools.pk_fixture_cli run harness_examples/demo_set.yml
```

> 補足: 配布 wheel/sdist には `tools/` のコードのみが含まれ、薬剤ライブラリ（`drugs/`、`pk_library.yml`、`templates/` ほか）は同梱しません。したがって素の `pip install` 後の実行は想定外です。`pip install -e .` での editable install はチェックアウト内のデータを参照できるため動作しますが、いずれもリポジトリのルートから実行してください。Web採取やジョブ生成など一部ツールを使う場合は追加依存を `pip install .[harvest]` / `.[jobs]` で入れます。

### 典型的な最短デモ

```bash
# 1) 複数薬剤デモを作成（外部runnerがなくてもdemo simを使って進行）
python3 tools/run_harness.py harness_examples/demo_set.yml

# 2) 同じ処理を CLI 入口から実行
python3 -m tools.pk_fixture_cli run harness_examples/demo_set.yml
```

### 外部mrgsolveがある場合

`sim_full.csv` がある前提で後段処理を実行:

```bash
python3 tools/run_workflow.py \
  --sim-full outputs/<run>/raw/sim_full.csv \
  --drug <slug> \
  --times 0,0.5,1,2,4,8,12,24 \
  --out-dir outputs/<run>/workflow
```

既存の採血時点を使う場合:

```bash
python3 tools/run_workflow.py \
  --sim-full outputs/<run>/raw/sim_full.csv \
  --drug <slug> \
  --schedule-csv schedule.csv \
  --out-dir outputs/<run>/workflow
```

既存DM/LB/VS/PCのskeletonを使う場合:

```bash
python3 tools/run_workflow.py \
  --sim-full outputs/<run>/raw/sim_full.csv \
  --drug <slug> \
  --dm-csv existing/DM.csv \
  --vs-csv existing/VS.csv \
  --lb-csv existing/LB.csv \
  --pc-csv existing/PC_skeleton.csv \
  --out-dir outputs/<run>/workflow
```

---

## 出力イメージ

```text
outputs/<run>/workflow/
  MANIFEST.yml
  trace.log
  raw/clinical_samples.csv
  reports/simulation_validation.md
  reports/pk_fixture_report/REPORT.md
  reports/pk_fixture_report/subject_numeric_summary.csv
  reports/pk_fixture_report/concentration_summary.csv
  sdtm_like/DM.csv
  sdtm_like/VS.csv
  sdtm_like/LB.csv
  sdtm_like/EX.csv
  sdtm_like/PC.csv
  analysis_inputs/ADPC.csv
  analysis_inputs/NCA_INPUT.csv
  analysis_inputs/POPPK_INPUT.csv
  adapters/*.csv
```

### 最小サンプル

`examples/minimal_aciclovir/workflow/analysis_inputs/ADPC.csv` は次のようなADPC-like CSVを含みます。

```csv
STUDYID,USUBJID,PARAMCD,AVAL,AVALU,TIME_H,MDV,BLQ,EXTRT,DOSE_MG,ROUTE
EXAMPLE,EXAMPLE-001,CONC,0,ng/mL,0,0,0,ACICLOVIR,100,ORAL
EXAMPLE,EXAMPLE-001,CONC,950,ng/mL,1,0,0,ACICLOVIR,100,ORAL
```

対応する `MANIFEST.yml` には、生成目的、入力、出力、警告を残します。

```yaml
purpose: analysis_input_smoke_test_fixture
status: OK
outputs:
  ADPC: examples/minimal_aciclovir/workflow/analysis_inputs/ADPC.csv
  NCA_INPUT: examples/minimal_aciclovir/workflow/analysis_inputs/NCA_INPUT.csv
  POPPK_INPUT: examples/minimal_aciclovir/workflow/analysis_inputs/POPPK_INPUT.csv
warnings: []
notes:
  - ADPC.csv is ADPC-like and intended for workflow smoke tests, not submission-ready ADaM.
```

### status の見方

- `OK`: 標準チェックが許容範囲
- `WARN`: 想定外でも使えるが、原因をノート化して運用
- `FAILED`: 原則停止（必要に応じて `--allow-validation-failed`）

---

## 使うべきでない用途（重要）

このハーネスは「実臨床の予測モデル」ではありません。以下は別解析で扱います。

- 投与設計・用量推定・規制提出用の妥当化
- 共変量モデル（年齢/体重/性別等）や非線形PKの正当化
- IIV/residual を使った厳密な再現性評価（現在はfixture用途向け）

`targets.auc.value` は通常 `Dose/CL` 由来で、厳密な文献AUCと同一視しないでください。文献AUCを主目的に使う場合は、`targets.yml`更新前提の明示的な差し替えレビューが必要です。

## ライセンスとデータ境界

- このリポジトリのコードとドキュメントは [MIT License](LICENSE) で公開しています。
- DailyMed、PubMed、OSP PBPK Model Library などの外部情報は参照元として扱い、上流ソースの利用条件はそれぞれの提供元に従います。
- 外部ツール本体、商用ライセンス、施設SOP、実患者データはこのリポジトリに含めません。
- 生成CSVやテンプレートは workflow fixture であり、submission-ready SDTM/ADaM、臨床推論、投与設計、規制提出用モデル妥当化の証拠ではありません。
- 配布形態: git チェックアウト前提のツールです。PyPI 配布はしておらず、wheel/sdist には `tools/` のみが含まれます（薬剤ライブラリ等のデータは非同梱）。`make` または `python -m tools.pk_fixture_cli` でリポジトリのルートから実行してください。

---

## 図・ガイド・運用の行き先

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): 日常操作（コマンド解説、エラー時の注意点）
- [docs/QUICKSTART.md](docs/QUICKSTART.md): 初見向けの短い順番
- [docs/index.md](docs/index.md): GitHub Pages向けdocs入口
- [docs/ACCEPTANCE_TEST.md](docs/ACCEPTANCE_TEST.md): README-onlyで第三者が回せる確認手順
- [docs/DOWNSTREAM_E2E.md](docs/DOWNSTREAM_E2E.md): NCA/PopPK下流 smoke 検証
- [docs/EXTERNAL_TOOL_VALIDATION_GUIDE.md](docs/EXTERNAL_TOOL_VALIDATION_GUIDE.md): Phoenix/NONMEM/nlmixr2での実行検証
- [docs/SITE_ADAPTER_GUIDE.md](docs/SITE_ADAPTER_GUIDE.md): 施設別CSV adapterの作り方
- [docs/USER_TEST_REPORT_TEMPLATE.md](docs/USER_TEST_REPORT_TEMPLATE.md): 利用者テスト報告テンプレート
- [docs/VALIDATION_AND_RELEASE_CHECKLIST.md](docs/VALIDATION_AND_RELEASE_CHECKLIST.md): リリース前のチェック
- [docs/RELEASE_NOTES_TEMPLATE.md](docs/RELEASE_NOTES_TEMPLATE.md): リリースノート雛形
- [docs/releases/v0.10.2.md](docs/releases/v0.10.2.md): v0.10.2 リリースノート
- [docs/releases/v0.10.3.md](docs/releases/v0.10.3.md): v0.10.3 リリースノート
- [docs/releases/v0.10.4.md](docs/releases/v0.10.4.md): v0.10.4 リリースノート
- [docs/READINESS_GAPS.md](docs/READINESS_GAPS.md): 外部環境が必要な残タスクの追跡
- [docs/WINDOWS_POWERSHELL.md](docs/WINDOWS_POWERSHELL.md): Windows向け実行手順
- [docs/CODEX_HARNESS.md](docs/CODEX_HARNESS.md): Codex での運用メモ
- [CONTRIBUTING.md](CONTRIBUTING.md): 変更提案時のルール
- [SECURITY.md](SECURITY.md): 脆弱性・安全性問題の報告方針
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md): コミュニティ行動規範
- [CITATION.cff](CITATION.cff): 引用メタデータ

---

## メインコマンド

```bash
python3 tools/validate_subjects_csv.py subjects/subjects.csv --expected-n 100
python3 tools/sample_clinical_timepoints.py --help
python3 tools/make_sdtm_like_domains.py --help
python3 tools/make_analysis_inputs.py --help
python3 tools/make_downstream_adapters.py --help
python3 tools/run_downstream_smoke.py --help
python3 tools/run_external_tool_validation.py --help
python3 tools/audit_library_priorities.py . --out-dir outputs/library_audit
```

必要に応じて、同じコマンド群は CLI にも同梱されています:

```bash
python3 -m tools.pk_fixture_cli --help
python3 -m tools.pk_fixture_cli doctor
python3 -m tools.pk_fixture_cli audit-library . --out-dir outputs/library_audit
```

---

## 主要設計思想（なぜこの形にしたか）

1. **canonicalは壊さない**
   - `pk.yml`, `targets.yml`, `spec` は自動更新しない
2. **再現性を優先**
   - seed、manifest、trace、ログを残して実行履歴を固定
3. **接続性を優先**
   - 下流のNCA/PopPKツール仕様は site adapter で吸収し、ハーネスは fixture と検証に集中
4. **検証と実臨床を分離**
   - 本リポジトリは「実データ風 fixture 作成」。臨床妥当化は別レイヤーで行う

---

## Repository Map

```text
docs/
  PROCESS_FLOW.md
  USER_GUIDE.md
  QUICKSTART.md
  VALIDATION_AND_RELEASE_CHECKLIST.md
  SCHEMA.md
  HARVEST.md

tools/
  run_harness.py
  run_workflow.py
  run_demo_set.py
  validate_simulation.py
  sample_clinical_timepoints.py
  make_sdtm_like_domains.py
  make_analysis_inputs.py
  make_downstream_adapters.py
  audit_library_priorities.py
  run_downstream_smoke.py

docs/assets/
  pk-harness-process.drawio
  pk-fixture-end-to-end-workflow.drawio

drugs/<slug>/
  pk.yml / targets.yml / spec_pk1_*.yml
```

---

## 一言で言うと

このハーネスは、

**「本番の解析モデルを作るための、速く壊れにくい検証配管を先に作る」**

ための道具です。

外部でのモデル実装とパラメータ更新を分離し、実装者・統計家・臨床薬理担当が同じログを見ながら同じ議論をできる状態にすることを目的にしています。
