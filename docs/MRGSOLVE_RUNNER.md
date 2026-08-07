# mrgsolve runner

`tools/mrgsolve_runner.R` は、`drugs/<slug>/spec_pk1_*.yml` を読み込み、
Pythonの `analytical_demo` とは独立に `mrgsolve` で1-compartment ODEを積分する
fixture runnerです。単回投与の出力は既存の `run_workflow.py` が受け取れる
`sim_full.csv` 形式です。

これはモデル二重実装の比較・ワークフロースモークテスト用であり、申請用PopPK
モデル、臨床推論、推定済みモデルの代替ではありません。

## 対応範囲

- `oral` / `po`: `GUT -> CENT`、一次吸収、`KA`、`ALAG1`、`F1`
- `iv` / `iv_bolus`: `CENT` ボーラス
- `iv` + armの `infusion_h`、または `iv_infusion`: `CENT` 点滴
- `iiv.eta`: YAML契約どおり対角OMEGAの分散として使用
- `residual.prop/add`: 単位分散のSIGMA/EPSをスケールしてDVへ適用
- `population.covariates.wt_kg`: median/CV/min/maxの切り捨て対数正規分布
- `--dose-count` と `--interval-h` による反復投与
- 絶対投与量は `regimen.units.dose: mg` のみ（mg/kg・BSA換算は未対応）
- `model.units.conc` は質量/容量単位（ng/mL, ug/mL, mg/mL, mg/L, ug/L, ng/L, g/L）に限定し、`model.units.mult`との組み合わせを検証

`WT` は現在モデルのCL/V共変量には使わず、被験者属性・出力監査用に生成します。
canonicalな `pk.yml`、`targets.yml`、specは変更しません。

## 依存関係

```r
install.packages(c("yaml", "mrgsolve"))
```

`dplyr` は不要です。runnerはbase R、`yaml`、`mrgsolve`だけで動作します。

## 単回経口50例

```bash
mkdir -p outputs/mrgsolve_demo/apixaban/raw

Rscript tools/mrgsolve_runner.R \
  --spec drugs/apixaban/spec_pk1_oral.yml \
  --out outputs/mrgsolve_demo/apixaban/raw/sim_full.csv \
  --n-subjects 50 \
  --seed 20260217 \
  --model-code outputs/mrgsolve_demo/apixaban/raw/mrgsolve_model.cpp

python3 tools/run_workflow.py \
  --sim-full outputs/mrgsolve_demo/apixaban/raw/sim_full.csv \
  --drug apixaban \
  --times 0,1,2,3,4,8,12,24 \
  --out-dir outputs/mrgsolve_demo/apixaban/workflow \
  --allow-validation-failed

Rscript tools/make_adnca.R \
  --analysis-dir outputs/mrgsolve_demo/apixaban/workflow/analysis_inputs \
  --out-dir outputs/mrgsolve_demo/apixaban/workflow/adnca \
  --mode single
```

`--allow-validation-failed` は、fixtureのvalidation warningを残して後処理を続ける
ための指定です。臨床的な適合を意味しません。

## IV点滴

```bash
Rscript tools/mrgsolve_runner.R \
  --spec drugs/albuterol/spec_pk1_iv.yml \
  --out outputs/mrgsolve_demo/albuterol_sim_full.csv \
  --n-subjects 50 \
  --seed 20260217
```

`spec_pk1_iv.yml` の `regimen.arms.A.infusion_h: 1.0` を検出し、EX相当の投与行に
`RATE = DOSE_MG / infusion_h` を出力します。

## 反復投与

```bash
Rscript tools/mrgsolve_runner.R \
  --spec drugs/apixaban/spec_pk1_oral.yml \
  --out outputs/mrgsolve_demo/apixaban_repeat_sim_full.csv \
  --n-subjects 50 \
  --t-end-h 156 \
  --dt-h 0.5 \
  --dose-count 13 \
  --interval-h 12 \
  --seed 20260217
```

同時刻の観測行と投与行は、観測行を先、投与行を後に並べます。出力の
`ROW_ORDER`、`EVID`、`AMT`、`RATE`を使って、既存のPC/EX/PopPK adapterへ渡せます。
反復投与のraw CSVを単回用 `run_workflow.py` に直接渡してはいけません。同ツールの
validationとEX生成は単回投与前提で、反復イベントを1回投与として扱います。反復経路では
`dosing_events.csv`を投与イベントの正本として、`make_repeated_nca.py`または施設側の
反復投与adapterへ渡してください。

### 反復投与ハーネスから実行する

`harness_examples/demo_repeated_oral_trough_ss_50_mrgsolve.yml` の
`simulation.engine` を `mrgsolve` にすると、Pythonの反復投与fixtureではなく、このR
runnerをサブプロセスで呼び出してから同じDM/EX/PC、トラフ、定常状態NCAの後段を実行します。

```bash
python3 tools/run_harness.py \
  --config harness_examples/demo_repeated_oral_trough_ss_50.yml
```

この経路では、mrgsolveの `EVID=1` 行を `raw/dosing_events.csv` に抽出し、EXとPopPKの
投与行の正本にします。`raw/sim_full.csv` はイベント行を含みますが、採血抽出は
`EVID=0` の観測行だけを使うため、トラフと最終投与間隔のNCA定義は分析式経路と共通です。
subject-specificな `CL_I` も出力し、反復モデルQCのDose/CL由来targetとの比較に使います。

## 出力契約

主な列は次のとおりです。

`STUDYID`, `USUBJID`, `ID`, `time`, `TIME_H`, `CMT`, `EVID`, `MDV`, `AMT`, `RATE`, `CP`,
`IPRED`, `DV`, `CP_UNIT`, `IPRED_UNIT`, `DV_UNIT`, `CONC_UNIT`, `WT`, `AGE`, `SEX`,
`ARM`, `DOSE_MG`, `DOSE_UNIT`, `ROUTE`, `ROW_ORDER`

- `CP` / `IPRED`: 残差誤差なしのモデル予測
- `DV`: `$SIGMA` のEPSを使った観測fixture
- `CMT=1`: 投与先（経口はGUT、IVはCENT）。観測先は経口では`CMT=2`（CENT）、
  IV 1-compartmentでは`CMT=1`（CENT）
- `EVID=1`: 投与行。`DV`は空欄
- `EVID=0`: 観測行
- `*_UNIT` / `CONC_UNIT`: `spec.model.units.conc` 由来。`DOSE_UNIT` は `regimen.units.dose` 由来。
  既知の濃度単位では、mg/Lを基準に `model.units.mult` との整合性も検証する。
- `<out>.manifest.yml`: package version、seed、theta/IIV/residual、件数、入力spec、生成モデルコードのパス

同一spec・同一seed・同一設定でCSVは再現します。`created_at`を含むmanifestは再実行時に変わります。

## Python経路との比較

同じspecから `run_demo_set.py` が作る `analytical_demo` と、ここで作るmrgsolve出力を
別ディレクトリに保存し、単回投与なら `run_workflow.py`、反復投与なら反復投与adapterと
`make_adnca.R`へ流すことで、解析式とODE積分の差を確認できます。差が出た場合でも、
canonical PK値を自動更新せず、`simulation_validation.md` と各manifestで原因を確認してください。
