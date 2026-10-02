---
layout: page
title: シミュレーションに必要なパラメータ
permalink: /simulation-parameters/
---

# シミュレーションに必要なパラメータ

このページは、現在の `spec_pk1_*.yml` と `tools/mrgsolve_runner.R` に基づく、1-compartment PKシミュレーションの入力仕様です。薬剤の科学的根拠は `pk.yml`、実行条件はspec、比較目標は `targets.yml` に分けて管理します。生成データはワークフロー検証用fixtureで、臨床推論・用量選択用モデルとして検証されたものではありません。

## 最初に決めること

1. 投与経路、用量、単回／反復、点滴時間を決める。
2. CL・Vの単位とbasis（systemic／apparent）を確認する。
3. 経口投与ではKA、F1、吸収ラグを決め、出典値とfixture仮定を区別する。
4. 被験者数、観測時間、個体間変動、残差誤差、乱数seedを指定する。
5. 採用値・変換式・出典・未確認事項を記録して検証する。

以下の「必要」は再現可能な実行仕様で明示すべき項目を意味します。runnerが省略時に既定値を補う項目も含みます。

## PKモデルのパラメータ

| specのキー | 意味 | 単位・範囲 | 必要な経路／省略時の挙動 |
| --- | --- | --- | --- |
| `model.template` | モデル構造 | `pk1_oral_ode` / `pk1_iv_ode` | 経路と一致させる |
| `model.theta.CL` | クリアランス | L/h、正数 | 全経路で必須 |
| `model.theta.V` | 分布容積 | L、正数 | 全経路で必須 |
| `model.theta.KA` | 一次吸収速度定数 | 1/h、正数 | 経口で必須、IVでは使用しない |
| `model.theta.F1` | 投与区画からの利用率 | 0–1 | 経口。runnerの省略値は1 |
| `model.theta.ALAG1` | 吸収ラグ時間 | h、0以上 | 経口。runnerの省略値は0 |
| `model.units.conc` | 出力濃度単位 | 例：ng/mL、mg/L | runnerの省略値はng/mL |
| `model.units.mult` | 基礎濃度mg/Lからの倍率 | 正数 | ng/mLなら1000、mg/Lなら1。単位との一致を検証 |

### 経口薬のCL/F・V/FとF1

出典が `CL/F`・`V/F` を報告している場合、これをsystemic CL・Vと取り違えないでください。整合する扱いは次の2通りです。

| 採用basis | theta.CL / theta.V | theta.F1 | 注意点 |
| --- | --- | --- | --- |
| apparent | 報告されたCL/F、V/F | 1 | apparent parameterizationとして記録。F1=1は実際の利用率100%を主張しない |
| systemic | `(CL/F) × F`、`(V/F) × F` | 根拠のあるF | Fの値・出典・変換式を記録し、specとtargetsのbasisを一致させる |

apparent CL/Vに実際のFをさらに適用すると、Fを二重に反映して濃度を過小評価します。出典がsystemic値を直接報告している場合は、その値を使用し、経口Fを別に指定します。値のbasisが不明なら推測変換せずレビュー対象に残します。

1-compartmentの消失速度は `ke = CL/V`、モデル半減期は `ln(2) × V/CL` です。CL・Vを独立入力として採用する場合、文献の半減期は比較目標です。CL・V・半減期の3つを無条件に独立入力として固定できません。不一致は警告として残し、半減期から黙って再校正しないでください。

## 投与・被験者・時間

| 設定 | 意味 | 契約 |
| --- | --- | --- |
| `study.id` | 試験識別子 | 出力の識別に使用 |
| `regimen.route` | 投与経路 | mrgsolveではoral/po、iv/iv_bolus、iv_infusion。経路ごとの詳細はrunner文書を参照 |
| `regimen.units.dose` | 用量単位 | mrgsolveは絶対量mgのみ。mg/kg・mg/m²は事前に根拠付きでmgへ換算 |
| `regimen.arms.<arm>.dose_mg` | 1回投与量 | mg、正数 |
| `regimen.arms.<arm>.n` | 群ごとの被験者数 | 正整数。`--n-subjects`で上書き可能 |
| `regimen.arms.<arm>.infusion_h` | 点滴時間 | h、点滴では正数。同runnerは各群で同じ点滴時間を要求。RATEはdose_mg/infusion_h |
| `population.covariates.wt_kg` | 体重分布 | runnerはmedian/CV/min/maxを用いた切り捨て対数正規分布。現在WTをCL/Vへ自動反映しない |
| `population.subject_source` | 外部被験者CSVの参照 | 任意。対応ツールと列仕様は[Schema](SCHEMA.md)参照。mrgsolve runnerの外部CSV読込みを意味しない |
| `sampling.t_end_h` | 観測終了 | h、正数。最終投与時刻を含む必要がある |
| `sampling.dt_h` | シミュレーション時間間隔 | h、正数 |
| `sampling.include_t0` | 時刻0の観測 | true/false |
| runner `--dose-count` | 投与回数 | 正整数。単回は1 |
| runner `--interval-h` | 投与間隔 | h、正数。反復投与で使用 |
| runner `--seed` | 乱数seed | 正整数。実行時の値を保存 |

生成グリッドと臨床採血時刻は別の設定です。後処理で採血時刻を抽出する場合、時刻列と補間方式も記録します。同runnerでは同時刻の観測を投与より先に処理します。反復投与の後段では `dosing_events.csv` を投与イベントの正本とします。

## 個体間変動・残差誤差

| specのキー | 意味 | mrgsolveの扱い |
| --- | --- | --- |
| `iiv.eta.CL` / `V` / `KA` | 対数スケール個体間変動 | 対角OMEGAの**分散**、0以上。SDやCVを直接入れない。KAは経口のみ |
| `iiv.corr` | ETA相関 | falseのみ対応 |
| `residual.type` | 残差モデル | prop+add（prop_addも受理） |
| `residual.prop` | 比例誤差のSD係数 | 無次元、0以上 |
| `residual.add` | 加算誤差のSD係数 | 出力濃度と同じ単位、0以上 |

個体値は `CL_i = CL × exp(ETA_CL)`（V・KAも同様）です。残差は `DV = IPRED × (1 + EPS_PROP × prop) + EPS_ADD × add`、EPSは独立標準正規乱数で、負のDVは0へ制限します。OMEGA=0なら当該個体間変動なし、`--no-residual`なら残差誤差なしです。

Pythonの `analytical_demo` はspecのIIV/residualを薬剤固有モデルとして消費せず、CLI/configのdemo用変動オプションを別に使います。使用エンジンを必ず記録し、同じspecでも変動の実装が同一と解釈しないでください。

## 任意の測定・比較条件

`assay.lloq: {value, unit}` は後段のBLQ処理用です。濃度単位と整合させ、BLQ/CENS/LIMITの列規約を記録します。これはmrgsolveのODE入力ではありません。

`targets.yml` の半減期・Cmax・Tmax・AUCは比較／QCの目標です。独立文献値とモデル由来チェック値を区別してください。元データから70 kg換算、per-kg換算、BSA 1.73 m²正規化を行う場合は、元単位、参照体格、変換式を保存します。集団の体重生成とPK値の体格正規化は別の操作です。

## 実行例と値の出典

数値を新たに作らず、既存の[ダパグリフロジンspec](https://github.com/Y-Fukiya/pkdummy-harness/blob/main/drugs/dapagliflozin/spec_pk1_oral.yml)を使用する例です。ローカルの採用specが実行入力の正本です。KA・ALAG1・IIV・残差などについて、specに値があることだけでは文献由来と判断できません。

```bash
Rscript tools/mrgsolve_runner.R \
  --spec drugs/dapagliflozin/spec_pk1_oral.yml \
  --out outputs/simulation_parameters/dapagliflozin/sim_full.csv \
  --seed 20260217

python3 -m tools.pk_fixture_cli parameter-provenance \
  --out-dir outputs/parameter_provenance

make harness-check
```

保存する情報は、採用spec、エンジン、CLI上書き、seed、出力単位、出典・変換・basis、実行manifest、検証結果です。source URLの存在だけでは値単位の確認完了ではありません。`pk_raw → pk_parsed → derived → spec theta` の対応と `value_provenance` のレビュー状態を確認します。

詳しい構造は[Schema](SCHEMA.md)、実行・出力契約は[mrgsolve runner](MRGSOLVE_RUNNER.md)、手順は[Quickstart](QUICKSTART.md)を参照してください。
