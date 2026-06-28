# pkdummy-harness PK template schema (v0.1–v0.2)

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
- `value_provenance`: warning薬剤の主要fixture値について、値の由来、正規化、変換、review状態を機械可読に記録します

> oral の場合、ラベルにある CL/V は **CL/F, V/F** のことが多いので、`*_abs` は「見かけ値」として扱い、`*_systemic = *_abs * F` を別途持っています。

### `value_provenance`

`value_provenance` はPK真値を主張するものではなく、fixture generator が使う値を監査しやすくするためのメタデータです。Phase 1 scope は、1-compartment attainability warningが出る13薬剤です。まずは次の3フィールドを必須にしています。

- `CL_abs_L_per_h_at_70kg`
- `V_abs_L_at_70kg`
- `t_half_h`

```yaml
value_provenance:
  CL_abs_L_per_h_at_70kg:
    source_id: null
    source_field: pk_parsed.clearance
    value_basis: derived_from_reported
    raw_value: 19.62
    raw_unit: L/h
    normalized_value: 19.62
    normalized_unit: L/h
    conversion:
      method: direct
      formula: pk_parsed.clearance.value
      assumptions: {}
    role: simulation_parameter
    source_review_status: needs_source_review
    fixture_limitation_status: not_applicable
    reviewer_status: needs_source_review
    reviewer_note: >
      Clearance is used as a deterministic fixture model parameter.
```

Enumは `tools/check_value_provenance.py` で検証します。

- `value_basis`: `label_reported`, `literature_reported`, `derived_from_reported`, `fixture_policy`, `unknown_needs_review`
- `conversion.method`: `direct`, `unit_conversion`, `body_weight_scaled`, `derived_formula`, `not_applicable`, `unknown_needs_review`
- `role`: `simulation_parameter`, `check_only`, `consistency_check`, `derived_output`, `metadata_only`
- `source_review_status`: `checked`, `needs_source_review`, `needs_unit_review`, `not_applicable`
- `fixture_limitation_status`: `acknowledged`, `not_applicable`
- `reviewer_status`: `checked`, `acknowledged_fixture_limitation`, `needs_source_review`, `needs_unit_review`, `not_applicable`

`source_id` が `null` でない場合は `sources[].id` に解決できる必要があります。既存source URLから値ごとの直接出典を特定できない場合は、出典を推測せず `source_id: null` として `fields_needing_review` に残します。
公開sourceを確認しても exact value match が取れない場合は、任意の `source_verification` を付けられます。これは `source_id` を解決済みにするための代替ではなく、どのsource/queryを確認し、なぜ未解決として残したかを machine-readable にするための監査メモです。
`source_verification` を付ける場合は、`status`、`blocker`、`next_action`、`reviewed_source_ids` も validator で確認されます。`status: no_exact_public_source_match` の entry は、source を推測接続しないため `source_id: null` のままにする必要があります。
`reviewer_status` は後方互換の legacy summary です。新規レビューでは、値ごとのsource確認は `source_review_status`、1-compartment fixture limitation の確認は `fixture_limitation_status` に分けて記録します。validator や `--report` の集計も、この2つの分離フィールドを優先します。
CLI report の `resolved_entries` は `drug.field -> source_id`、`resolved_source_refs` は `drug.source_id` の一覧です。`unresolved_entries`、`unresolved_entry_details`、`unresolved_reason_counts`、`source_verification_status_counts`、`source_review_blocker_counts`、`unresolved_entries_missing_source_verification`、`source_verification_coverage`、`source_verification_coverage_by_priority`、`source_mapping_coverage`、`source_mapping_coverage_by_field`、`source_mapping_coverage_by_drug`、`next_review_entries`、`next_review_details`、`source_review_queue`、`source_review_action_counts`、`suggested_source_kind_counts`、`fully_mapped_warning_drugs` / `partially_mapped_warning_drugs` / `unmapped_warning_drugs` も併せて出力し、local source id だけでは区別しにくい cross-drug の source mapping と残レビューを監査しやすくします。`source_verification` がある未解決entryでは、`source_verification_status`、`source_review_blocker`、`next_source_review_action` も `unresolved_entry_details` / `next_review_details` に出力します。`source_review_queue` は、薬剤ごとの未解決field、available/used/unused source id、source URL refs、coverage、highest priority、review action をまとめたレビュー作業用のqueueです。source refs には `source_kind` / `source_rank` を付け、`suggested_source_refs` は label, PubMed, journal, DrugBank, PubChem, Wikipedia, secondary の順で確認候補を並べます。

## `drugs/<slug>/spec_pk1_oral.yml` / `spec_pk1_iv.yml`

`mrg-dummy` スキル（`pk1_oral_ode`, `pk1_iv_ode`）に渡すための実行 spec。

- `population`: 体重分布など
  - `subject_source`（任意）: `subjects.csv` のような外部被験者テーブルを使うための参照情報
- `regimen`: 投与経路と用量
  - `arms.<arm>.infusion_h`（任意）: IV infusion duration in hours。`route: iv` または `iv_infusion` かつ `infusion_h > 0` の場合、demo generatorは注入式を使い、PopPK fixtureの投与行 `RATE = dose_mg / infusion_h` を出力します
- `sampling`: 観測スケジュール
- `model.theta`: 主に `CL`/`V`/（oral は `KA`/`F1`/`ALAG1`）
- `model.notes`: demo generatorで独立に採用するパラメータ対や、1-compartment attainability警告の扱いを記録します
- `assay.lloq`（任意）: BLQ/M3-ready fixture用のLower Limit of Quantification。`value` と `unit` を持てます。top-level `lloq` も後方互換の簡略指定として読めます。誤配置しやすい `model.assay.lloq` / `model.lloq` も互換フォールバックとして読みますが、新規specでは `assay.lloq` を推奨します

```yaml
assay:
  lloq:
    value: 10
    unit: ng/mL
```

`iiv` と `residual` は外部mrgsolve等のrunner向けのspec情報です。組み込みdemo generator単体では `model.theta` を主に消費し、薬剤固有のIIV/residual modelとしては消費しません。demo-only variabilityはCLI/config側の軽量オプションで別管理します。

demo generatorの対応経路は `oral`, `po`, `sc`, `im`, `iv`, `iv_bolus`, `iv_infusion`, `intravenous` です。SC/IMは一次吸収式の軽量fixtureとして扱います。その他の未対応経路は吸収相の黙示的bolus化を避けるためエラーにします。

`sample_clinical_timepoints.py` の `method` は `linear`, `log-linear`, `exact`, `nearest` を受け付けます。`log-linear` は陽性濃度列のみlog-linear補間し、濃度以外の数値列は線形補間します。`sampling.predose_mdv1: true` またはCLI `--predose-mdv1` を使うと、名目0時間の観測をPopPK側で `MDV=1` として扱えます。

BLQ行は `PCSTAT=BLQ`, `PCBLFL=Y`, `PCLLOQ` としてSDTM-like PCへ出力され、analysis inputでは `BLQ=1`, `CENS=1`, `LIMIT=LLOQ` としてPopPK fixtureへ伝搬します。これは外部NONMEM/nlmixr2 control streamでM3 likelihoodへ接続するための列契約です。`PCSTAT=BLQ` と `PCBLFL` は提出用標準SDTMへの完全準拠ではなく、workflow fixture向けの簡略表現です。Pinnacle 21等のconformance checkへ直接かける場合は、施設仕様に合わせて `PCORRES="<LLOQ"`、`PCSTRESN` blank、SUPPPC/ADaM側BLQフラグなどへ変換してください。

PopPK fixtureのBLQ観測は既定で `DV=0`, `MDV=1`, `CENS=1`, `LIMIT=LLOQ` として出力します。M3 likelihoodのcontrol streamによっては `DV=LLOQ` など別規約を期待するため、実解析側adapterで調整してください。

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
- `targets.auc.basis`: `dose_over_cl` など、AUC targetの由来を機械可読に示します
- `targets.auc.independent_literature_target`: `false` の場合、AUC targetは独立文献AUCではなくfixture整合性チェックです
- `targets.auc.source_value`: `CL_abs_L_per_h_at_70kg` など、Dose/CL計算に使う入力値の識別子です
- `targets.auc.role`: `consistency_check` など、targetの用途を示します
- `targets.t_half.role`: `check_only` など、t_half targetの用途を示します
- `targets.t_half.used_to_calibrate_cl_v`: `false` の場合、t_halfはCL/Vを自動再較正しません
- `targets.t_half.structural_mismatch.acknowledged`: `true` の場合、CL/Vとt_halfの不一致をfixture limitationとして確認済みです
- `provenance_review`: warning薬剤では、CL/V/t_halfをjoint calibrationしない理由を短く記録します
- `notes` には、人間向けの補足として、AUCが `Dose/CL` 由来で独立文献AUCではないこと、spec側で採用する独立パラメータ対、1-compartment attainability labelを残します

AUCがpassしても臨床妥当性の証拠にはなりません。文献AUCで検証したい場合は、`targets.auc.value/unit/summary` を文献値に差し替え、source/raw/parsed/derived の対応と単位変換式を notes に残してください。

## workflow `MANIFEST.yml`

`run_workflow.py` が出す run-level `MANIFEST.yml` は、入力・出力・件数に加えて、
ターゲットの由来と1-compartment上の制約を機械可読に残します。

```yaml
target_metadata:
  parameter_pair_policy: spec_theta_uses_pk_yml_derived_cl_v_abs
  clearance_basis: systemic
  volume_basis: systemic
  auc:
    basis: dose_over_cl
    target_basis: dose_over_cl_not_literature_auc
    independent_literature_target: false
    value: 5096.83995922528
    unit: ng*h/mL
    summary: geometric_mean
  t_half:
    basis: literature_target_retained_as_check
    value: 2.5
    unit: h
    summary: arithmetic_mean
    pk_parsed_half_life_h: 2.5
    target_half_life_h: 2.5
    cl_v_implied_half_life_h: 1.4838
    relative_error: 0.406
    warning_threshold: 0.25
    attainability_status: WARN
    detected_structural_mismatch: true
    acknowledged_structural_mismatch: true
    structural_mismatch_reason: one_compartment_fixture_approximation
```

- `target_metadata.auc.basis: dose_over_cl` は、AUC target が積分整合性チェックであり、独立した文献AUC検証ではないことを示します。
- `target_metadata.t_half.detected_structural_mismatch: true` は、採用したCL/Vペアと `t_half` を1-compartmentで同時達成できないことを計算上検出した状態です。
- `target_metadata.t_half.acknowledged_structural_mismatch: true` は、その不一致をfixture limitationとして人間が確認済みであることを示します。
- これらは実行artifactの監査情報であり、`pk.yml`、`targets.yml`、`spec_pk1_*.yml` を自動更新しません。

run-level manifestには full provenance ではなく summary だけを出します。

```yaml
value_provenance_summary:
  scope: value_provenance_present
  provenance_required: true
  required_fields:
    - CL_abs_L_per_h_at_70kg
    - V_abs_L_at_70kg
    - t_half_h
  checked_fields:
    - CL_abs_L_per_h_at_70kg
    - V_abs_L_at_70kg
    - t_half_h
  fields_needing_review:
    - CL_abs_L_per_h_at_70kg
  source_ids: []
  mismatch_acknowledged_fields:
    - t_half_h
```

非warning薬剤など、現段階で value-level provenance を必須対象にしていない薬剤では、summary は次のように空の対象範囲を明示します。

```yaml
value_provenance_summary:
  scope: warning_drugs_only
  provenance_required: false
  required_fields: []
  checked_fields: []
  fields_needing_review: []
  source_ids: []
  mismatch_acknowledged_fields: []
```

## ツール

- `python tools/validate_library.py <root>`: 整合性チェック。`CL/V` から暗黙に決まる半減期と `pk_parsed.half_life_h` が大きく矛盾する場合は `1-compartment attainability warnings` を表示する。これは `pk.yml` の自動修正ではなく、1-compartment fixtureとして同時達成できないtargetを見える化する警告
- `python tools/rebuild_index.py <root>`: INDEX.csv 再生成
- `python tools/validate_subjects_csv.py subjects.csv`: 外部被験者CSVの列・行数・基本値を検証
- `python -m tools.pk_fixture_cli --help`: standalone CLI入口。`doctor`, `run`, `workflow` などから既存ツールへdispatchする
- `python tools/run_harness.py harness_examples/demo_set.yml`: YAML configから複数薬剤デモまたはpost-simulation workflowを起動する共通入口。Shiny Cloud/Tauri/CLIから同じconfigを使うための薄いdispatcher
- `python tools/run_workflow.py --sim-full outputs/<run>/raw/sim_full.csv --drug <slug> --times 0,0.5,1,2,4,8,12,24 --out-dir outputs/<run>/workflow`: 生成済み `sim_full.csv` から検証、採血時点抽出、SDTM-like CSV生成、ADPC-like/NCA/PopPK入力生成、run-level manifest/trace作成を一括実行する。必要に応じて `--pc-conc-unit`, `--dose-cmt`, `--observation-cmt` で濃度単位とPopPK CMT conventionを明示できる
- `python tools/run_demo_set.py --drugs albuterol,alprazolam,aciclovir,abciximab,felodipine --out-dir outputs/demo_set_milestone7`: 複数薬剤のデモ用 `sim_full.csv` を既存spec thetaから解析式で作成し、各薬剤に `run_workflow.py` を適用する。これはworkflow smoke demo用で、mrgsolve runnerの代替ではない
- `python tools/validate_simulation.py outputs/<run>/raw/sim_full.csv --pk drugs/<slug>/pk.yml --targets drugs/<slug>/targets.yml`: 生成済み濃度データから AUC/Cmax/Tmax/t1/2 を単回で再計算して比較する。入力CSVに単位列があればレポートとCL由来AUC換算に使う。検証は決定論的な1回の計算であり、最適化やcalibrationは行わない
- `python tools/sample_clinical_timepoints.py outputs/<run>/raw/sim_full.csv --times 0,0.5,1,2,4,8,12,24 --out outputs/<run>/raw/clinical_samples.csv`: 密なシミュレーション出力を臨床試験の名目採血時点に合わせて疎化する
- `python tools/make_sdtm_like_domains.py --clinical-samples outputs/<run>/raw/clinical_samples.csv --spec drugs/<slug>/spec_pk1_oral.yml --out-dir outputs/<run>/sdtm_like`: 限定版の `DM.csv`, `VS.csv`, `LB.csv`, `EX.csv`, `PC.csv`, `MANIFEST.yml` を生成する。濃度単位は入力単位列から引き継ぎ、必要なら `--pc-conc-unit` で明示する。`--strict-subject-match` を付けると `subjects.csv` とPC側の被験者ID不一致で停止する
- 既存ドメインを使う場合は `--dm-csv`, `--vs-csv`, `--lb-csv`, `--ex-csv`, `--pc-csv` を指定できる。`--pc-csv` は濃度なしPC skeletonとして扱い、`USUBJID + PCTPTNUM/PCTPT/PCELTM` で `clinical_samples.csv` と照合して `PCORRES/PCSTRESN` を埋める
- `python tools/make_analysis_inputs.py --sdtm-like-dir outputs/<run>/workflow/sdtm_like --out-dir outputs/<run>/workflow/analysis_inputs`: 限定版SDTM-like `DM/VS/LB/EX/PC` から `ADPC.csv`, `NCA_INPUT.csv`, `POPPK_INPUT.csv`, `MANIFEST.yml` を生成する。`--dose-cmt`, `--observation-cmt` でPopPK fixtureのCMT conventionを明示できる。これらは下流workflow smoke test用で、submission-ready ADaMやモデル固有NONMEM datasetではない
- `python tools/make_downstream_adapters.py --analysis-dir outputs/<run>/workflow/analysis_inputs --out-dir outputs/<run>/workflow/adapters`: `ADPC.csv` と `POPPK_INPUT.csv` から `nca_r.csv`, `nca_phoenix.csv`, `poppk_nonmem.csv`, `poppk_nlmixr2.csv` を生成する。これはparser/control-stream smoke test用adapterで、各ツールの正式dataset仕様を保証しない
- `python tools/make_site_adapters.py --analysis-dir outputs/<run>/workflow/analysis_inputs --spec-yml external_validation/site_adapter_template.yml --out-dir outputs/<run>/workflow/site_adapters`: 施設ごとの列名、固定値、必須非空欄をYAMLで定義し、site-specific CSV adapterと `SITE_ADAPTER_MANIFEST.yml` を生成する
- `python tools/validate_downstream_adapters.py outputs/<run>/workflow/adapters`: adapter CSVのrepository-owned contractを検証する。外部ツール公式仕様の認証ではない
- `python tools/run_downstream_smoke.py --analysis-dir outputs/<run>/workflow/analysis_inputs --out-dir outputs/<run>/workflow/downstream_smoke`: adapter生成、簡易NCA、PopPK parser template作成をまとめて行うfixture-level E2E smoke check
- `python tools/run_external_tool_validation.py --downstream-dir outputs/<run>/workflow/downstream_smoke --out-dir outputs/<run>/workflow/external_tool_validation --tools nonmem,nlmixr2 --execute`: 同じrepo内のprofileから外部Phoenix/NONMEM/nlmixr2環境を任意実行する。外部ツール本体やライセンスは同梱しない
- `python tools/validate_harness_config.py harness_examples/demo_set.yml`: `run_harness.py` 用configの必須項目、mode、sampling、validation、demo variability設定を検証する
- `python tools/check_examples.py examples`: Git管理された `examples/minimal_*` を一時ディレクトリで再生成し、CSVとmanifestの安定項目が期待出力からずれていないか確認する
- `python tools/doctor.py`: Python/R/Quarto/simPopなどのローカル環境をpreflight確認する。必須依存不足はFAILED、任意依存不足はWARN
- `python tools/validate_manifest.py outputs/<run>/workflow/MANIFEST.yml`: run-levelまたはtool-level `MANIFEST.yml` の必須field、status、mapping/list型を確認する
- `python tools/render_manifest_viewer.py outputs/<run>/workflow/MANIFEST.yml --out-html outputs/<run>/workflow/manifest_viewer.html`: `MANIFEST.yml` を薄い静的HTML viewerに変換する。UI/cloud runnerの代替ではなく、manifest閲覧用
- `Rscript tools/report_pk_fixture.R --analysis-dir outputs/<run>/workflow/analysis_inputs --out-dir outputs/<run>/workflow/reports/pk_fixture_report --title "<slug> PK fixture report"`: `ADPC.csv` から被験者背景の要約統計、時点別濃度統計、ggplot2のlinear/log濃度プロット、Markdownレポートを生成する。これはfixture確認用の記述統計で、臨床薬理モデル妥当化ではない
- `Rscript tools/render_pk_fixture_quarto.R --analysis-dir outputs/<run>/workflow/analysis_inputs --out-dir outputs/<run>/workflow/reports/pk_fixture_quarto --title "<slug> PK fixture report"`: `templates/pk_fixture_report.qmd` を使って、軽量レポートの内容をQuarto docxへ変換する任意ステップ。Word style referenceを使う場合は `--reference-doc reference.docx` を指定する
- `Rscript tools/make_simpop_subjects.R --out subjects.csv --n 100 --dose-mg 100`: 任意の `simPop` ベース被験者CSV生成
