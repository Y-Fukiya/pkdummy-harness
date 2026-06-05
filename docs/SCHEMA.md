# OSP PK template schema (v0.1–v0.2)

このフォルダは **「薬剤ごとの PopPK サマリ（ラベル/論文）」→「1-compartment mrgsolve テンプレ」** を最短で回すための、軽量スキーマです。

実行手順を先に見たい場合は [QUICKSTART.md](QUICKSTART.md) を参照してください。この文書は、`pk.yml`, `targets.yml`, `spec_pk1_*.yml` の構造とツール対応を確認するためのリファレンスです。

## `drugs/<slug>/pk.yml`

- `id` / `name`
- `route_inferred`: `po` or `iv`
- `sources`: 参照元 URL
- `pk_raw`: 元の文字列（レンジ・単位込み）
- `pk_parsed`: パース済み
  - `half_life_h` (+ optional range)
  - `clearance`: `{value, unit}`（基本 `L/h`）
  - `volume`: `{value, unit}`（`L/kg` or `L`）
  - `bioavailability_frac`: 0–1
- `derived`:
  - `ke_1_per_h = ln(2)/t1/2`
  - `CL_abs_L_per_h_at_70kg`
  - `V_abs_L_at_70kg`
  - `CL_systemic_L_per_h_at_70kg` / `V_systemic_L_at_70kg`

> oral の場合、ラベルにある CL/V は **CL/F, V/F** のことが多いので、`*_abs` は「見かけ値」として扱い、`*_systemic = *_abs * F` を別途持っています。

## `drugs/<slug>/spec_pk1_oral.yml` / `spec_pk1_iv.yml`

`mrg-dummy` スキル（`pk1_oral_ode`, `pk1_iv_ode`）に渡すための実行 spec。

- `population`: 体重分布など
  - `subject_source`（任意）: `subjects.csv` のような外部被験者テーブルを使うための参照情報
- `regimen`: 投与経路と用量
- `sampling`: 観測スケジュール
- `model.theta`: 主に `CL`/`V`/（oral は `KA`/`F1`/`ALAG1`）

### `population.subject_source`（任意）

`simPop` などで作った被験者属性テーブルを、テンプレートから参照するための任意ブロックです。既存の `population.covariates` はフォールバックとして残します。

```yaml
population:
  n: 100
  covariates:
    wt_kg:
      dist: lognormal
      median: 70.0
      cv: 0.25
      min: 40
      max: 120
  subject_source:
    type: external_csv
    path: subjects/aciclovir_subjects.csv
    generator: simPop
    required_columns: [ID, ARM, DOSE_MG, WT, AGE, SEX]
    optional_columns: [USUBJID, STUDYID, HEIGHT_CM]
```

このブロックは **人口属性の入力** だけを表します。`simPop` は `CL`、`V`、`KA`、`F`、`ETA` などのPK個人差を生成しません。PK個人差は `model` / `iiv` 側で定義してください。

`HEIGHT_CM` は任意列です。存在する場合はSDTM-like `VS` の `HEIGHT`, `BMI`, `BSA` 作成に使い、存在しない場合は後処理ツール側でworkflow fixture用の身長を生成します。

## `drugs/<slug>/targets.yml`

`pk-targets`（想定）に渡すためのターゲット定義。

- `targets.auc.value` は v0.1 では **Dose/CL から自動計算**（暫定）

## ツール

- `python tools/validate_library.py <root>`: 整合性チェック
- `python tools/rebuild_index.py <root>`: INDEX.csv 再生成
- `python tools/validate_subjects_csv.py subjects.csv`: 外部被験者CSVの列・行数・基本値を検証
- `python tools/run_harness.py harness_examples/demo_set.yml`: YAML configから複数薬剤デモまたはpost-simulation workflowを起動する共通入口。Shiny Cloud/Tauri/CLIから同じconfigを使うための薄いdispatcher
- `python tools/run_workflow.py --sim-full outputs/<run>/raw/sim_full.csv --drug <slug> --times 0,0.5,1,2,4,8,12,24 --out-dir outputs/<run>/workflow`: 生成済み `sim_full.csv` から検証、採血時点抽出、SDTM-like CSV生成、ADPC-like/NCA/PopPK入力生成、run-level manifest/trace作成を一括実行する
- `python tools/run_demo_set.py --drugs albuterol,alprazolam,aciclovir,abciximab,felodipine --out-dir outputs/demo_set_milestone7`: 複数薬剤のデモ用 `sim_full.csv` を既存spec thetaから解析式で作成し、各薬剤に `run_workflow.py` を適用する。これはworkflow smoke demo用で、mrgsolve runnerの代替ではない
- `python tools/validate_simulation.py outputs/<run>/raw/sim_full.csv --pk drugs/<slug>/pk.yml --targets drugs/<slug>/targets.yml --max-loops 3`: 生成済み濃度データから AUC/Cmax/Tmax/t1/2 を再計算して比較し、警告/失敗時は最大3回まで検証履歴を残す
- `python tools/sample_clinical_timepoints.py outputs/<run>/raw/sim_full.csv --times 0,0.5,1,2,4,8,12,24 --out outputs/<run>/raw/clinical_samples.csv`: 密なシミュレーション出力を臨床試験の名目採血時点に合わせて疎化する
- `python tools/make_sdtm_like_domains.py --clinical-samples outputs/<run>/raw/clinical_samples.csv --spec drugs/<slug>/spec_pk1_oral.yml --out-dir outputs/<run>/sdtm_like`: 限定版の `DM.csv`, `VS.csv`, `LB.csv`, `EX.csv`, `PC.csv`, `MANIFEST.yml` を生成する。`--strict-subject-match` を付けると `subjects.csv` とPC側の被験者ID不一致で停止する
- 既存ドメインを使う場合は `--dm-csv`, `--vs-csv`, `--lb-csv`, `--ex-csv`, `--pc-csv` を指定できる。`--pc-csv` は濃度なしPC skeletonとして扱い、`USUBJID + PCTPTNUM/PCTPT/PCELTM` で `clinical_samples.csv` と照合して `PCORRES/PCSTRESN` を埋める
- `python tools/make_analysis_inputs.py --sdtm-like-dir outputs/<run>/workflow/sdtm_like --out-dir outputs/<run>/workflow/analysis_inputs`: 限定版SDTM-like `DM/VS/LB/EX/PC` から `ADPC.csv`, `NCA_INPUT.csv`, `POPPK_INPUT.csv`, `MANIFEST.yml` を生成する。これらは下流workflow smoke test用で、submission-ready ADaMやモデル固有NONMEM datasetではない
- `Rscript tools/report_pk_fixture.R --analysis-dir outputs/<run>/workflow/analysis_inputs --out-dir outputs/<run>/workflow/reports/pk_fixture_report --title "<slug> PK fixture report"`: `ADPC.csv` から被験者背景の要約統計、時点別濃度統計、ggplot2のlinear/log濃度プロット、Markdownレポートを生成する。これはfixture確認用の記述統計で、臨床薬理モデル妥当化ではない
- `Rscript tools/render_pk_fixture_quarto.R --analysis-dir outputs/<run>/workflow/analysis_inputs --out-dir outputs/<run>/workflow/reports/pk_fixture_quarto --title "<slug> PK fixture report"`: `templates/pk_fixture_report.qmd` を使って、軽量レポートの内容をQuarto docxへ変換する任意ステップ。Word style referenceを使う場合は `--reference-doc reference.docx` を指定する
- `Rscript tools/make_simpop_subjects.R --out subjects.csv --n 100 --dose-mg 100`: 任意の `simPop` ベース被験者CSV生成
