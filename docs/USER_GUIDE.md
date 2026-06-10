# PK-like Synthetic Data Harness 使用マニュアル

このマニュアルは、このリポジトリを **SDTM -> ADaM -> NCA / PopPK ワークフロー検証用のダミーデータ生成ハーネス** として使うための手順書です。

このハーネスは臨床推論や投与設計のためのモデルではありません。文献スケールの CL/V/t1/2/AUC を使い、実データに近い形の synthetic PK data を作って、解析処理を素早く回すことを目的にしています。

初めて実行する場合は、まず [QUICKSTART.md](QUICKSTART.md) の複数薬剤デモを試してください。このUSER_GUIDEは、Quickstart後に個別ツールや既存SDTM-like skeleton利用を詳しく確認するための詳細版です。

生成物の形をすぐ確認したい場合は、Git管理された小さな例 [../examples/minimal_aciclovir](../examples/minimal_aciclovir) と [../examples/minimal_albuterol_iv](../examples/minimal_albuterol_iv) も参照できます。

## 1. 全体像

```mermaid
flowchart LR
    A[文献 / DailyMed / PubMed] --> B[drugs/<slug>/pk.yml]
    B --> C[spec_pk1_oral.yml / spec_pk1_iv.yml]
    B --> D[targets.yml]
    C --> E[Simulation runner]
    E --> F[raw/sim_full.csv]
    F --> W[run_workflow.py]
    D --> W
    W --> G[validation report]
    W --> I[clinical_samples.csv]
    W --> L[DM / VS / LB / EX / PC CSV]
    W --> O[ADPC-like / NCA / PopPK input CSV]
    W --> N[MANIFEST.yml / trace.log]
    O --> M[ADaM / NCA / PopPK workflow smoke test]
    O --> R[descriptive report / ggplot]
```

このリポジトリが直接管理するものは、薬剤テンプレート、検証ツール、文献パラメータ更新ツール、手順書です。mrgsolveなどの実行runnerは、利用環境側のスクリプトに合わせて使います。

## 2. まず確認する

リポジトリ直下で実行します。

```bash
python3 -m pip install -r requirements.txt
make harness-check
```

成功すると、ライブラリ整合性、単体テスト、INDEX再現性、不要ファイル混入のチェックが通ります。

個別に見る場合:

```bash
make validate
make test
make regen-check
make examples-check
make doctor
python3 tools/validate_harness_config.py harness_examples/demo_set.yml
```

## 3. 薬剤を選ぶ

薬剤一覧は `INDEX.csv` です。

```bash
column -s, -t < INDEX.csv | less -S
```

各薬剤ディレクトリは次の構造です。

```text
drugs/<slug>/
  pk.yml              # source/raw/parsed/derived PK summary
  targets.yml         # AUC/t1/2 の最低限チェック用 target
  spec_pk1_oral.yml   # 経口薬の場合
  spec_pk1_iv.yml     # IV薬の場合
```

## 4. 標準ワークフロー

### Step 1: specを実行する

経口薬:

```bash
Rscript <mrgsolve-runner> drugs/<slug>/spec_pk1_oral.yml
```

IV薬:

```bash
Rscript <mrgsolve-runner> drugs/<slug>/spec_pk1_iv.yml
```

`<mrgsolve-runner>` には、利用環境で使っているmrgsolve runnerを指定してください。このリポジトリのspecは、runnerに `spec_pk1_*.yml` を渡す前提の入力テンプレートです。

典型的な出力:

```text
outputs/<run>/
  raw/sim_full.csv
  nonmem/*.csv
  reports/*.md
```

### Step 2: シミュレーション出力を検証する

一括で回す場合は、`run_workflow.py` を使います。これは `sim_full.csv` 生成後の validate、採血時点抽出、SDTM-like CSV生成、run-level manifest/trace作成をまとめて行います。

```bash
python3 tools/run_workflow.py \
  --sim-full outputs/<run>/raw/sim_full.csv \
  --drug <slug> \
  --times 0,0.5,1,2,4,8,12,24 \
  --out-dir outputs/<run>/workflow
```

`validate_simulation.py` が `FAILED` の場合、既定では下流の `clinical_samples.csv` / SDTM-like CSV生成に進みません。stress testとして進めたい場合だけ `--allow-validation-failed` を付けてください。

個別に検証だけ行う場合:

```bash
python3 tools/validate_simulation.py \
  outputs/<run>/raw/sim_full.csv \
  --pk drugs/<slug>/pk.yml \
  --targets drugs/<slug>/targets.yml \
  --out-md outputs/<run>/reports/simulation_validation.md
```

この検証は `sim_full.csv` から `AUC0-inf`, `Cmax`, `Tmax`, terminal `t1/2` を再計算します。現時点で主に判定に使うのは AUC と t1/2 です。
入力CSVに `CP_UNIT`, `DV_UNIT`, `CONC_UNIT`, `PCSTRESU` などの単位列がある場合は、レポート表示とCL由来AUC比較の単位換算に使います。単位列がない場合は、従来どおり `ng/mL` 前提のfixtureとして扱います。
このterminal `t1/2` は末尾の陽性濃度点から計算するfixture-level checkです。正式NCAのlambda-z候補選択、R2/adjusted R2、AUC extrapolation割合、linear-up/log-down台形法を代替するものではありません。

`tools/validate_library.py` は、`CL`, `V`, `t1/2` が1-compartment関係 `t1/2 = ln(2) * V / CL` と大きく矛盾する場合に `1-compartment attainability warnings` を出します。この警告がある薬剤では、`validate_simulation.py` の t1/2 `WARN/FAILED` がシミュレーションのドリフトではなく、canonical target側の構造的不整合を反映している可能性があります。

各薬剤の `targets.yml` と `spec_pk1_*.yml` には、どのパラメータ対を独立に採るかを notes として残しています。現在のdemo generatorでは `CL` と `V` を独立パラメータとして採用し、`t1/2` は下流検証targetとして扱います。AUC targetは多くの薬剤で `Dose/CL` 由来のため、AUC passは積分器・単位・後処理の整合性確認であり、独立した文献AUCとの一致や臨床妥当性の証拠ではありません。文献AUCで検証したい場合は、`targets.auc.value/unit/summary` を差し替え、source/raw/parsed/derived と単位変換式を notes に残してください。

### Step 3: 臨床試験の採血ポイントに合わせる

密な `sim_full.csv` を、名目採血時点だけの疎なデータにします。

```bash
python3 tools/sample_clinical_timepoints.py \
  outputs/<run>/raw/sim_full.csv \
  --times 0,0.5,1,2,4,8,12,24 \
  --out outputs/<run>/raw/clinical_samples.csv
```

出力には元の列に加えて、次の列が追加されます。

| Column | Meaning |
| --- | --- |
| `NOMTIME_H` | 名目採血時刻 |
| `TIME_H` | 実採血時刻 |
| `TPT` | 採血時点名 |
| `TPTNUM` | 採血時点番号 |
| `SAMPLE_METHOD` | `linear`, `log-linear`, `exact`, `nearest` |

### Step 4: SDTM/ADaM/NCA/PopPKへ投入する

下流処理には通常、`raw/sim_full.csv` よりも `clinical_samples.csv` の方が扱いやすいです。SDTM PC/PP、ADPC、NCA、PopPK用データセットに変換する入口として使います。

`run_workflow.py` は、限定版SDTM-like CSVに加えて `analysis_inputs/` も作ります。ここには ADPC-like、NCA、PopPK parser/control-stream smoke test 用のCSVが入ります。

## 5. 採血スケジュールをCSVで指定する

既存試験の採血時点名に合わせたい場合は、schedule CSVを作ります。

```csv
NOMTIME_H,TPT,TPTNUM
0,Pre-dose,1
0.5,30 min,2
1,1 h,3
2,2 h,4
4,4 h,5
8,8 h,6
12,12 h,7
24,24 h,8
```

実行:

```bash
python3 tools/sample_clinical_timepoints.py \
  outputs/<run>/raw/sim_full.csv \
  --schedule-csv schedule.csv \
  --out outputs/<run>/raw/clinical_samples.csv
```

実採血時刻らしさを入れる場合:

```bash
python3 tools/sample_clinical_timepoints.py \
  outputs/<run>/raw/sim_full.csv \
  --schedule-csv schedule.csv \
  --jitter-min 5 \
  --seed 20260217 \
  --out outputs/<run>/raw/clinical_samples.csv
```

`--jitter-min 5` は、名目時刻の前後5分以内で `TIME_H` を揺らします。Pre-doseの0時間は0のままです。

## 6. 採血ポイント抽出方法の選び方

| Method | Use case |
| --- | --- |
| `linear` | 推奨。密な時系列から名目時刻へ線形補間する |
| `log-linear` | 終末相などで陽性濃度列をlog-linear補間したい場合。濃度以外の数値列は線形補間する |
| `exact` | `sim_full.csv` にその時刻が必ず存在する場合 |
| `nearest` | 補間せず、近い時刻の行を使いたい場合 |

`linear` は濃度も線形補間します。`log-linear` は `CP`, `IPRED`, `DV`, `CONC`, `PCSTRESN`, `PCORRES`, `AVAL` のような陽性濃度列だけをlog-linear補間し、体重などの共変量は線形補間します。正式NCA用の補間・lambda-z判断・AUC methodは下流ツール側で明示してください。

例:

```bash
python3 tools/sample_clinical_timepoints.py \
  outputs/<run>/raw/sim_full.csv \
  --times 0,1,2,4 \
  --method nearest \
  --nearest-window-h 0.25 \
  --out outputs/<run>/raw/clinical_samples.csv
```

## 7. 結果の扱い

```mermaid
flowchart TD
    A[validate_simulation.py] --> B{Status}
    B -->|OK| C[通常のworkflow fixture]
    B -->|WARN| D[レビュー付きデモ / 境界条件テスト]
    B -->|FAILED| E[stress test / source review対象]
    D --> F[pk.ymlは自動変更しない]
    E --> F
```

| Status | Recommended handling |
| --- | --- |
| `OK` | 標準的なダミーデータとして使う |
| `WARN` | 難しめのケースとして使う。レポートを残す |
| `FAILED` | stress test、または文献/source/model review対象として扱う |

`WARN` や `FAILED` は、ワークフロー検証では必ずしも悪ではありません。実データ処理では扱いにくいデータも出るため、処理系を鍛える目的では有用です。ただし、臨床的に正しい再現とは説明しないでください。

## 8. SDTM-likeドメインCSVを作る場合

`clinical_samples.csv` から、ワークフロー検証用の限定版 `DM`, `VS`, `LB`, `EX`, `PC` を作れます。

```bash
python3 tools/make_sdtm_like_domains.py \
  --clinical-samples outputs/<run>/raw/clinical_samples.csv \
  --spec drugs/<slug>/spec_pk1_oral.yml \
  --out-dir outputs/<run>/sdtm_like
```

出力:

| File | Scope |
| --- | --- |
| `DM.csv` | 被験者ID、年齢、性別、arm |
| `VS.csv` | `HEIGHT`, `WEIGHT`, `BMI`, `BSA` のみ |
| `LB.csv` | `CREAT` のみ |
| `EX.csv` | spec/subject由来の投与情報 |
| `PC.csv` | `clinical_samples.csv` 由来の濃度時点 |
| `MANIFEST.yml` | 入力ファイル、設定、件数、警告 |

これは submission-ready SDTM/XPT ではありません。SDTM -> ADaM -> NCA / PopPK の処理系を早く回すためのCSV fixtureです。

`--subjects-csv` を使う場合、subjects側とPC側の被験者ID不一致は警告として `MANIFEST.yml` と標準出力に残ります。厳密に止めたい場合は `--strict-subject-match` を追加します。

PC濃度は既定で `DV` を読み、必要に応じて `CP`, `IPRED` をフォールバックします。全行で濃度が読めない場合はエラー、部分的に読めない場合は警告になります。

濃度単位は、`DV_UNIT`, `DVU`, `CONC_UNIT`, `PCSTRESU`, `PCORRESU` などの入力列があれば引き継ぎます。単位を明示したい場合は `--pc-conc-unit` を指定します。

```bash
python3 tools/run_workflow.py \
  --sim-full outputs/<run>/raw/sim_full.csv \
  --drug <slug> \
  --times 0,0.5,1,2,4,8,12,24 \
  --pc-conc-unit ng/mL \
  --out-dir outputs/<run>/workflow
```

単位列も `--pc-conc-unit` もない場合だけ、workflow fixtureの既定として `ng/mL` を使います。
この単位は後続の `ADPC.csv` / `NCA_INPUT.csv` にも引き継がれます。

### 既存DM/LB/VS/PC skeletonがある場合

既存の `DM`, `VS`, `LB` を保持し、濃度なし `PC` skeletonだけにシミュレーション濃度を注入できます。

```bash
python3 tools/run_workflow.py \
  --sim-full outputs/<run>/raw/sim_full.csv \
  --drug <slug> \
  --times 0,0.5,1,2,4,8,12,24 \
  --dm-csv existing/DM.csv \
  --vs-csv existing/VS.csv \
  --lb-csv existing/LB.csv \
  --pc-csv existing/PC_skeleton.csv \
  --out-dir outputs/<run>/workflow
```

`PC` skeletonは `USUBJID + PCTPTNUM` を優先して照合し、次に `USUBJID + PCTPT`、最後に `USUBJID + PCELTM/TIME` を使います。非空欄の既存濃度は上書きしません。上書きしたい場合だけ `--overwrite-existing-pc-conc` を使います。

既存skeletonには最低限の列チェックがあります。

| Domain | Required columns |
| --- | --- |
| `DM` | `USUBJID` |
| `VS` | `USUBJID`, `VSTESTCD`, `VSSTRESN` |
| `LB` | `USUBJID`, `LBTESTCD`, `LBSTRESN` |
| `EX` | `USUBJID`, `EXTRT`, `EXDOSE`, `EXROUTE` |
| `PC` | `USUBJID` plus at least one of `PCTPTNUM`, `PCTPT`, `PCELTM`, `TIME_H`, `TIME`, `time` |

このチェックはsubmission-ready SDTM validationではなく、濃度注入とADPC/NCA/PopPK fixture作成に必要な最低限の入口チェックです。

## 9. ADPC/NCA/PopPK入力を作る場合

`run_workflow.py` を使うと、SDTM-like生成後に自動で次のファイルが作られます。

```text
outputs/<run>/workflow/analysis_inputs/
  ADPC.csv
  NCA_INPUT.csv
  POPPK_INPUT.csv
  MANIFEST.yml
```

| File | Intended use | Important limitation |
| --- | --- | --- |
| `ADPC.csv` | ADPC-likeな濃度解析入力 | submission-ready ADaMではない |
| `NCA_INPUT.csv` | NCA pipeline smoke test | 実NCAツールの列仕様には必要に応じてadapterを足す |
| `POPPK_INPUT.csv` | NONMEM-like parser/control-stream smoke test | モデル固有のcontrol streamを保証しない |
| `MANIFEST.yml` | 件数、警告、入力対応の確認 | 警告がある場合は下流投入前に確認する |

個別にSDTM-likeディレクトリから作る場合:

```bash
python3 tools/make_analysis_inputs.py \
  --sdtm-like-dir outputs/<run>/workflow/sdtm_like \
  --out-dir outputs/<run>/workflow/analysis_inputs
```

このステップの役割は、臨床薬理的な正しさの証明ではなく、**SDTM-likeからADaM/NCA/PopPK側へ最低限つながるか** の確認です。PC濃度が全て欠損している場合は停止し、部分欠損は `MANIFEST.yml` の警告とPopPK側の `MDV=1` として残します。

PopPK fixtureの `CMT` は既定で投与行 `1`、観測行 `2` ですが、実NONMEM/nlmixr2モデルのcompartment定義とは限りません。施設やcontrol streamに合わせる場合は明示します。

```bash
python3 tools/make_analysis_inputs.py \
  --sdtm-like-dir outputs/<run>/workflow/sdtm_like \
  --out-dir outputs/<run>/workflow/analysis_inputs \
  --dose-cmt 1 \
  --observation-cmt 2
```

`run_workflow.py` から一括実行する場合も、同じ `--dose-cmt` と `--observation-cmt` を指定できます。

### 記述統計レポートを作る場合

`analysis_inputs/ADPC.csv` から、被験者背景の要約統計、時点別濃度統計、ggplot2による濃度推移図を作れます。

```bash
Rscript tools/report_pk_fixture.R \
  --analysis-dir outputs/<run>/workflow/analysis_inputs \
  --out-dir outputs/<run>/workflow/reports/pk_fixture_report \
  --title "<slug> PK fixture report"
```

出力:

| File | Content |
| --- | --- |
| `REPORT.md` | Markdown形式の記述統計レポート |
| `subject_numeric_summary.csv` | `AGE`, `WT`, `HEIGHT_CM`, `BMI`, `BSA`, `CREAT_MG_DL`, `DOSE_MG` の要約 |
| `subject_categorical_summary.csv` | `SEX`, `ARM`, `ACTARM`, `ROUTE` の度数 |
| `concentration_summary.csv` | `TIME_H` ごとの n/mean/SD/CV/geometric mean/medianなど |
| `concentration_profile_linear.png` | そのままの濃度スケールのggplot |
| `concentration_profile_log.png` | log10濃度スケールのggplot。非陽性濃度は除外 |
| `REPORT_MANIFEST.yml` | 入力、出力、件数、安全策 |

このレポートはfixture確認用です。submission-ready ADaMレポート、VPC/GOF、臨床薬理モデル妥当化の代替ではありません。

Word共有用のdocxが必要な場合は、Quarto wrapperを使います。これは上記の軽量レポートを置き換えるものではなく、同じ内容をWordで配布しやすくする任意ステップです。

```bash
Rscript tools/render_pk_fixture_quarto.R \
  --analysis-dir outputs/<run>/workflow/analysis_inputs \
  --out-dir outputs/<run>/workflow/reports/pk_fixture_quarto \
  --title "<slug> PK fixture report"
```

出力:

| File | Content |
| --- | --- |
| `pk_fixture_report.qmd` | 生成済みMarkdown/PNGを埋め込んだQuarto source |
| `pk_fixture_report.docx` | Word共有用レポート |
| `QUARTO_REPORT_MANIFEST.yml` | Quarto template、入力、出力、render状態 |

Wordのスタイルを合わせたい場合は、任意で `--reference-doc reference.docx` を指定できます。Quartoの `reference-doc` は見た目のスタイル参照であり、統計ロジックは `.qmd` やCSV側で管理します。
同梱のたたき台は `templates/pk_fixture_reference.docx` です。

### NCA/PopPK tool別adapterを作る場合

`analysis_inputs/` から、NCA/PopPKツール別の軽量CSV adapterを作れます。

```bash
python3 tools/make_downstream_adapters.py \
  --analysis-dir outputs/<run>/workflow/analysis_inputs \
  --out-dir outputs/<run>/workflow/adapters
```

| File | Intended use |
| --- | --- |
| `nca_r.csv` | R系NCA parser smoke test |
| `nca_phoenix.csv` | Phoenix風NCA取り込み確認 |
| `poppk_nonmem.csv` | NONMEM風control-stream parser確認 |
| `poppk_nlmixr2.csv` | nlmixr2風parser確認 |
| `MANIFEST.yml` | adapter出力、件数、注意事項 |

これは列名や最小列セットを合わせるadapterです。各ツール固有の正式な解析datasetやcontrol streamを保証するものではありません。

### 下流E2E smoke checkを行う場合

adapter生成、簡易NCA、PopPK parser template作成までまとめて確認できます。

```bash
python3 tools/run_downstream_smoke.py \
  --analysis-dir outputs/<run>/workflow/analysis_inputs \
  --out-dir outputs/<run>/workflow/downstream_smoke
```

出力:

| File | Content |
| --- | --- |
| `DOWNSTREAM_SMOKE_MANIFEST.yml` | status, counts, warnings, limitations |
| `nca_smoke/NCA_SUMMARY.csv` | simple linear-trapezoidal `CMAX`, `TMAX_H`, `AUCLAST` |
| `poppk_smoke/POPPK_PARSE_SUMMARY.yml` | dose/observation row counts |
| `poppk_smoke/nonmem_parser_template.ctl` | NONMEM parser smoke template |
| `poppk_smoke/nlmixr2_parser_template.R` | nlmixr2 parser smoke template |

これは正式なPhoenix/NONMEM/nlmixr2実行ではありません。下流parserやcontrol templateへつながるかのfixture-level E2E確認です。

Phoenix / NONMEM / nlmixr2 の実行環境がある場合は、同じリポジトリ内の external validation profile から呼べます。

```bash
python3 tools/run_external_tool_validation.py \
  --downstream-dir outputs/<run>/workflow/downstream_smoke \
  --out-dir outputs/<run>/workflow/external_tool_validation \
  --tools nonmem,nlmixr2 \
  --execute
```

`--execute` を付けない場合は実行せず、コマンド存在確認だけを行います。profileは [../external_validation/tool_profiles.yml](../external_validation/tool_profiles.yml) を各施設の環境に合わせて調整してください。

### 施設ごとのCSV仕様に合わせる場合

NCA/PopPK側の列名や必須列が施設ごとに決まっている場合は、site adapterを使います。標準の `make_downstream_adapters.py` は一般的なsmoke test用、`make_site_adapters.py` は施設ごとのCSV mapping用です。

```bash
python3 tools/make_site_adapters.py \
  --analysis-dir outputs/<run>/workflow/analysis_inputs \
  --spec-yml external_validation/site_adapter_template.yml \
  --out-dir outputs/<run>/workflow/site_adapters
```

`external_validation/site_adapter_template.yml` をコピーし、列名、入力source、固定値、必須非空欄を施設仕様に合わせて編集してください。

```yaml
adapters:
  site_nca:
    source: ADPC
    output: site_nca.csv
    columns:
      - name: SUBJECT
        source: USUBJID
      - name: TIME
        source: TIME_H
      - name: CONC
        source: AVAL
      - name: DATASET_PURPOSE
        value: workflow_fixture_not_submission_ready
    required_nonblank: [SUBJECT, TIME, CONC]
```

出力:

| File | Content |
| --- | --- |
| `site_nca_example.csv` | site adapter specで定義したNCA向けCSV |
| `site_poppk_example.csv` | site adapter specで定義したPopPK向けCSV |
| `SITE_ADAPTER_MANIFEST.yml` | 入力、spec、出力、件数、警告 |

これは施設ごとの取り込み確認をしやすくするための変換層です。submission-ready ADaM、正式Phoenix dataset、正式NONMEM datasetを保証するものではありません。

## 10. 複数薬剤デモを作る場合

Milestone 7では、3-5薬剤程度をまとめて流し、成功例、WARN例、限界例を確認します。

```bash
python3 tools/run_harness.py harness_examples/demo_set.yml
```

正式CLI入口から実行する場合:

```bash
python3 -m tools.pk_fixture_cli run harness_examples/demo_set.yml
```

出力:

```text
outputs/demo_set_milestone7/
  DEMO_MANIFEST.yml
  summary.csv
  summary.md
  <drug>/
    raw/sim_full.csv
    workflow/
      reports/simulation_validation.md
      raw/clinical_samples.csv
      sdtm_like/
      analysis_inputs/
```

`summary.csv` には、各薬剤の `workflow_status`, `validation_status`, `analysis_adpc_rows`, `analysis_nca_rows`, `analysis_poppk_rows`, `warnings_n` が入ります。

重要な注意点:

- `tools/pk_fixture_cli.py` / `pk-fixture` は既存ツールを束ねる正式CLI入口です。
- `run_harness.py` はYAML configから既存ツールを呼ぶ共通入口です。Shiny CloudやTauriから呼ぶ場合も、この入口または `pk-fixture run` を使う想定です。
- `run_demo_set.py` はデモ専用の解析式generatorで `sim_full.csv` を作ります。
- 既存の `spec_pk1_*.yml` のthetaを読みますが、`pk.yml`, `targets.yml`, specは更新しません。
- demo generatorが消費する薬剤固有PKは主に `model.theta` です。`iiv` と `residual` は外部mrgsolve runner向けのspec情報で、demo単体では薬剤固有のIIV/residual errorとしては消費しません。将来配線する場合は、`iiv.eta` を分散（omega squared）として扱うのかCVとして扱うのかを明示してから変換してください。
- 経口predoseの既定は `DV=0/MDV=0` です。`run_workflow.py` または `sample_clinical_timepoints.py` で `--predose-mdv1` を指定すると、名目0時間の観測を残したままPopPK側で `MDV=1` にできます。
- `assay.lloq` または top-level `lloq` をspecへ追加すると、限定版PCに `PCLLOQ`, `PCSTAT=BLQ`, `PCBLFL=Y` が出ます。`model.assay.lloq` / `model.lloq` も互換フォールバックとして読みますが、新規specでは `assay.lloq` を使ってください。PopPK smoke inputではBLQ観測に `BLQ=1`, `MDV=1`, `CENS=1`, `LIMIT=LLOQ` を付けます。NONMEM/nlmixr2 adapterにも `CENS/LIMIT` が流れるため、外部control stream側でM3 likelihoodへ接続できます。
- BLQのSDTM-like表現は提出用標準SDTMへの完全準拠ではありません。`PCSTAT=BLQ` と `PCBLFL=Y` はfixtureの簡略フラグです。Pinnacle 21等に通す用途では、施設仕様に合わせて `PCORRES="<LLOQ"`、`PCSTRESN` blank、SUPPPCまたはADaM側BLQフラグへ変換してください。PopPK側も既定は `DV=0`, `CENS=1`, `LIMIT=LLOQ` なので、M3 control streamが `DV=LLOQ` など別規約を期待する場合はadapter側で調整してください。
- demo generatorは `oral/po/sc/im/iv/iv_bolus/iv_infusion` に対応します。SC/IMは経口と同じ一次吸収式を使う軽量fixtureです。その他の未対応経路は、吸収相なしbolusへ黙って落とさずエラーにします。
- mrgsolve runnerの代替ではありません。実運用に近いシミュレーションデモでは、外部runnerで作った `sim_full.csv` を `run_workflow.py` に渡してください。
- WARN/FAILEDは「臨床的に悪い」と同義ではなく、workflow fixtureとして扱うべき境界条件のラベルです。

## 11. アプリ化の判断

現時点では、Shinyなどのフルアプリ化は行わず、CLI + Quickstart + USER_GUIDEで運用する判断です。理由と将来UIを作る場合の範囲は [APP_DECISION.md](APP_DECISION.md) にまとめています。

作る場合も、最初は `run_harness.py` を呼び出して `summary`, `MANIFEST`, validation reportを表示する thin launcher / manifest viewer に限定します。`pk.yml` の直接編集やcalibration結果の自動反映はUIでも行いません。

UI/launcherが読むべき入出力契約は [LAUNCHER_CONTRACT.md](LAUNCHER_CONTRACT.md) にまとめています。UIは `HARNESS_STATUS.json` を読み、必要に応じて `HARNESS_MANIFEST.yml`, `summary.md`, validation report, CSVを表示します。

## 12. 被験者属性CSVを使う場合

任意で `simPop` を使って被験者属性CSVを作れます。

```bash
Rscript -e 'install.packages("simPop", repos="https://cloud.r-project.org")'
Rscript tools/make_simpop_subjects.R \
  --out subjects/subjects.csv \
  --n 100 \
  --dose-mg 100 \
  --seed 20260217

python3 tools/validate_subjects_csv.py subjects/subjects.csv \
  --expected-n 100 \
  --allowed-arm A
```

`simPop` は年齢、性別、体重などの属性生成に限定します。PK個人差、`CL`, `V`, `KA`, `ETA` の根拠にはしません。

`make_simpop_subjects.R` は任意列 `HEIGHT_CM` も出力します。`make_sdtm_like_domains.py` に `--subjects-csv` を渡すと、VSの身長、BMI、BSA作成に使われます。

demo generatorの固定被験者は軽量確認用です。共変量モデルや吸収多様性の検証には使わず、現実的な人口統計が必要な場合は `subjects_csv` / `simPop` 経路で被験者属性だけを差し替えてください。WT/AGE/SEX/CREATはSDTM-like/analysis inputには流れますが、現行の解析式ではCL/V/KA/Fへは接続していません。

```bash
python3 tools/make_sdtm_like_domains.py \
  --clinical-samples outputs/<run>/raw/clinical_samples.csv \
  --spec drugs/<slug>/spec_pk1_oral.yml \
  --subjects-csv subjects/subjects.csv \
  --out-dir outputs/<run>/sdtm_like
```

## 13. 文献情報からパラメータを更新する

文献情報を探してパラメータを更新する経路は残しています。詳細は [HARVEST.md](HARVEST.md) を参照してください。

```mermaid
flowchart LR
    A[Literature / Label sources] --> B[harvest_and_generate.py]
    B --> C{PK update candidate}
    C -->|source/raw/unit/formula review| D[drugs/<slug>/pk.yml]
    D --> E[spec_pk1_*.yml / targets.yml]
    E --> F[Simulation runner]
    F --> G[raw/sim_full.csv]
    G --> H[run_workflow.py]
    H --> I[validation report / MANIFEST / trace]
    H --> J[clinical_samples.csv / SDTM-like CSV]
    H --> L[ADPC-like / NCA / PopPK input CSV]
    I --> K[calibration or review artifact]
    K -. not merged automatically .-> D
```

| Component | Role | Guardrail |
| --- | --- | --- |
| `run_workflow.py` | 検証、採血点抽出、SDTM-like生成、ADPC-like/NCA/PopPK入力生成 | `pk.yml` は更新しない |
| `validate_simulation.py` | `OK/WARN/FAILED` を出す | WARN/FAILEDを理由に自動最適化しない |
| `harvest_and_generate.py` | 文献からPK更新候補を作る | source/raw/parsed/derivedの対応を残す |
| `pk.yml` | canonical PK summary | 根拠不明の推測値やcalibration値を混ぜない |
| calibration artifact | デモ・補正・review結果 | canonical `pk.yml` とは別管理 |

実行例:

```bash
uv run --with requests --with lxml --with pyyaml python tools/harvest_and_generate.py \
  --jobs jobs.yml \
  --repo . \
  --default-dose-mg 100

python tools/rebuild_index.py .
make harness-check
```

更新時のルール:

- source URL と raw text を残す
- `pk_raw`, `pk_parsed`, `derived` の関係を壊さない
- 単位変換と導出式を説明できるようにする
- 経口薬の CL/V は原則 CL/F, V/F として扱う
- calibration artifact を canonical な `pk.yml` に混ぜない

## 14. よく使うコマンド

| Purpose | Command |
| --- | --- |
| 全体チェック | `make harness-check` |
| 軽い整合性チェック | `make validate` |
| 単体テスト | `make test` |
| INDEX再現性確認 | `make regen-check` |
| example再生成チェック | `make examples-check` |
| 環境preflight | `make doctor` |
| standalone CLI確認 | `python3 -m tools.pk_fixture_cli --help` |
| manifest構造確認 | `python3 tools/validate_manifest.py outputs/<run>/workflow/MANIFEST.yml` |
| config一括ハーネス | `python3 tools/run_harness.py harness_examples/demo_set.yml` |
| 一括workflow | `python3 tools/run_workflow.py --sim-full outputs/<run>/raw/sim_full.csv --drug <slug> --times 0,0.5,1,2,4,8,12,24 --out-dir outputs/<run>/workflow` |
| 濃度単位を明示 | `python3 tools/run_workflow.py --sim-full outputs/<run>/raw/sim_full.csv --drug <slug> --times 0,0.5,1,2,4,8,12,24 --pc-conc-unit ng/mL --out-dir outputs/<run>/workflow` |
| 複数薬剤デモ | `python3 tools/run_harness.py harness_examples/demo_set.yml` |
| 既存SDTM skeleton利用 | `python3 tools/run_workflow.py --sim-full outputs/<run>/raw/sim_full.csv --drug <slug> --times 0,0.5,1,2,4,8,12,24 --dm-csv existing/DM.csv --vs-csv existing/VS.csv --lb-csv existing/LB.csv --pc-csv existing/PC_skeleton.csv --out-dir outputs/<run>/workflow` |
| シミュレーション検証 | `python3 tools/validate_simulation.py outputs/<run>/raw/sim_full.csv --pk drugs/<slug>/pk.yml --targets drugs/<slug>/targets.yml --out-md outputs/<run>/reports/simulation_validation.md` |
| 採血時点抽出 | `python3 tools/sample_clinical_timepoints.py outputs/<run>/raw/sim_full.csv --times 0,0.5,1,2,4,8,12,24 --out outputs/<run>/raw/clinical_samples.csv` |
| SDTM-like CSV生成 | `python3 tools/make_sdtm_like_domains.py --clinical-samples outputs/<run>/raw/clinical_samples.csv --spec drugs/<slug>/spec_pk1_oral.yml --out-dir outputs/<run>/sdtm_like` |
| ADPC/NCA/PopPK入力生成 | `python3 tools/make_analysis_inputs.py --sdtm-like-dir outputs/<run>/workflow/sdtm_like --out-dir outputs/<run>/workflow/analysis_inputs` |
| PopPK CMT convention指定 | `python3 tools/make_analysis_inputs.py --sdtm-like-dir outputs/<run>/workflow/sdtm_like --out-dir outputs/<run>/workflow/analysis_inputs --dose-cmt 1 --observation-cmt 2` |
| NCA/PopPK adapter生成 | `python3 tools/make_downstream_adapters.py --analysis-dir outputs/<run>/workflow/analysis_inputs --out-dir outputs/<run>/workflow/adapters` |
| 下流E2E smoke check | `python3 tools/run_downstream_smoke.py --analysis-dir outputs/<run>/workflow/analysis_inputs --out-dir outputs/<run>/workflow/downstream_smoke` |
| 外部tool validation probe | `python3 tools/run_external_tool_validation.py --downstream-dir outputs/<run>/workflow/downstream_smoke --out-dir outputs/<run>/workflow/external_tool_validation` |
| 施設別CSV adapter生成 | `python3 tools/make_site_adapters.py --analysis-dir outputs/<run>/workflow/analysis_inputs --spec-yml external_validation/site_adapter_template.yml --out-dir outputs/<run>/workflow/site_adapters` |
| adapter contract確認 | `python3 tools/validate_downstream_adapters.py outputs/<run>/workflow/downstream_smoke/adapters` |
| manifest viewer生成 | `python3 tools/render_manifest_viewer.py outputs/<run>/workflow/MANIFEST.yml --out-html outputs/<run>/workflow/manifest_viewer.html` |
| 記述統計レポート生成 | `Rscript tools/report_pk_fixture.R --analysis-dir outputs/<run>/workflow/analysis_inputs --out-dir outputs/<run>/workflow/reports/pk_fixture_report --title "<slug> PK fixture report"` |
| Quarto docxレポート生成 | `Rscript tools/render_pk_fixture_quarto.R --analysis-dir outputs/<run>/workflow/analysis_inputs --out-dir outputs/<run>/workflow/reports/pk_fixture_quarto --title "<slug> PK fixture report"` |
| 被験者CSV検証 | `python3 tools/validate_subjects_csv.py subjects/subjects.csv --expected-n 100 --allowed-arm A` |

## 15. トラブルシューティング

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `validate_simulation.py` が WARN | t1/2やAUCがtargetから少し外れている | workflow fixtureとして使うならレポートを残す |
| `validate_simulation.py` が FAILED | 1-compartment限界、CL/V basis、文献値不整合 | `validate_library.py` のattainability warningも確認し、stress test扱い、またはsource review |
| `sample_clinical_timepoints.py` が範囲外エラー | 指定した採血時刻が `sim_full.csv` の時間範囲外 | `sampling.t_end_h` を延ばして再実行、または採血時刻を短くする |
| `--method exact` でエラー | 指定時刻がCSVに存在しない | `linear`, `log-linear`, `nearest` のいずれかを使う |
| `make_sdtm_like_domains.py` が濃度列を読めない | `clinical_samples.csv` に `DV` がない | `--pc-conc-col CP` など実列名を指定する |
| 濃度単位が期待と違う | 入力CSVに単位列がない、または施設単位と異なる | `--pc-conc-unit` を指定する。入力列では `DV_UNIT`, `DVU`, `CONC_UNIT`, `PCSTRESU` などを利用できる |
| 既存PC skeletonに濃度が入らない | `USUBJID` と `PCTPTNUM/PCTPT/PCELTM` が合わない | skeleton側の時点キーを確認する |
| `make_analysis_inputs.py` が停止する | PC濃度が全て欠損している | `PCSTRESN`, `PCORRES`, `DV`, `CP`, `IPRED` のいずれかが入っているか確認する |
| PopPKのCMTがcontrol streamと合わない | 既定CMTはparser smoke用の convention | `--dose-cmt`, `--observation-cmt` で施設側モデル定義に合わせる |
| `report_pk_fixture.R` が `ggplot2` 不足で停止する | R package未導入 | `install.packages("ggplot2")` を実行する。ハーネス本体はこのレポートなしでも実行可能 |
| `render_pk_fixture_quarto.R` がQuarto不足で停止する | Quarto CLI未導入または実行制約 | Quartoを導入する。docx不要なら `report_pk_fixture.R` のMarkdown/PNG/CSVで運用する |
| 既存skeletonで列不足エラー | fixture生成に必要な最小列がない | `DM/VS/LB/EX/PC` のrequired columnsを確認する |
| MANIFEST構造をまとめて確認したい | 出力artifactのschemaを確認したい | `python3 tools/validate_manifest.py --recursive outputs/<run>` を使う |
| `run_demo_set.py` の結果がWARNになる | 既存spec thetaとtargets/pk.ymlのズレ、1-comp限界、デモ解析式とmrgsolve runner差 | `summary.md` と各薬剤の `simulation_validation.md` を確認する。canonical PK値は自動変更しない |
| site adapterでsource column not found | 施設別mapping specの `source` が `ADPC/NCA_INPUT/POPPK_INPUT` に存在しない | `analysis_inputs/*.csv` の列名を確認して `external_validation/site_adapter_template.yml` を修正する |
| subjectsとPCの被験者が合わない | `--subjects-csv` と `clinical_samples.csv` のID差 | `MANIFEST.yml` の警告を確認し、厳密に止めるなら `--strict-subject-match` を使う |
| `simPop` が動かない | R package未導入または環境依存 | `simPop` なしで既定のpopulation設定を使う |

## 16. 専門家に説明するときの表現

そのまま使える説明文:

> This harness generates literature-scale PK-like synthetic data for SDTM/ADaM/NCA/PopPK workflow testing. It is not intended for clinical inference, dose selection, or regulatory model qualification.

共有するとよいもの:

- `docs/USER_GUIDE.md`
- 対象薬剤の `drugs/<slug>/pk.yml`
- 対象薬剤の `targets.yml`
- 実行した `spec_pk1_*.yml`
- `outputs/<run>/reports/simulation_validation.md`
- 採血時点抽出後の `clinical_samples.csv`
- 必要に応じて `outputs/<run>/sdtm_like/*.csv`
- SDTM-like生成時の `outputs/<run>/sdtm_like/MANIFEST.yml`
- `outputs/<run>/workflow/analysis_inputs/*.csv`
- `outputs/<run>/workflow/analysis_inputs/MANIFEST.yml`
- 必要に応じて `outputs/<run>/workflow/site_adapters/SITE_ADAPTER_MANIFEST.yml`
- 必要に応じて `outputs/<run>/workflow/reports/pk_fixture_report/REPORT.md`
- Word共有が必要なら `outputs/<run>/workflow/reports/pk_fixture_quarto/pk_fixture_report.docx`
- 複数薬剤デモでは `outputs/demo_set_milestone7/summary.csv` と `summary.md`
- アプリ化判断では `docs/APP_DECISION.md`
- UI/launcher連携では `docs/LAUNCHER_CONTRACT.md`

## 17. 最小チェックリスト

```text
[ ] INDEX.csv から薬剤を選ぶ
[ ] spec_pk1_*.yml をrunnerで実行する
[ ] raw/sim_full.csv が出ている
[ ] run_workflow.py で validation report / clinical_samples.csv / SDTM-like CSV / analysis_inputs / MANIFEST / trace.log を作る
[ ] 濃度単位とPopPK CMT conventionが施設側仕様と合うか確認する
[ ] OK/WARN/FAILED の扱いを記録する
[ ] ADPC.csv / NCA_INPUT.csv / POPPK_INPUT.csv を下流workflowに投入する
[ ] 必要なら make_downstream_adapters.py でツール別adapterを作る
[ ] 施設仕様があるなら make_site_adapters.py で列名・必須列を合わせる
[ ] 必要なら report_pk_fixture.R で被験者背景と濃度の記述統計レポートを出す
[ ] Word共有が必要なら render_pk_fixture_quarto.R でdocxを出す
[ ] 複数薬剤デモでは summary.csv / summary.md で薬剤間の成功/WARN/限界例を確認する
```
