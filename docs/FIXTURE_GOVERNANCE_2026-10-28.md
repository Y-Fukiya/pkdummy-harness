---
layout: page
title: モデル評価・計算用投与設定・値の選択方針
permalink: /fixture-governance/
---

# モデル評価・計算用投与設定・値の選択方針

全37剤を対象に、原典照合と臨床モデル評価を分離しました。今回の変更ではCL、V、F、半減期、実行用量、AUCターゲットを変更していません。出典付きの制約と選択記録を追加し、実行用量を画面とダウンロードへ表示しています。

[パラメータ画面](https://y-fukiya.github.io/pkdummy-harness/parameters/) / [全37剤の評価・投与設定CSV](https://y-fukiya.github.io/pkdummy-harness/parameters/FIXTURE_GOVERNANCE.csv) / [選択ルールCSV](https://y-fukiya.github.io/pkdummy-harness/parameters/PARAMETER_SELECTIONS.csv)

## 1. 全剤で評価状態を必須にする

`pk.yml.simulation_validity.status` は全剤必須です。新規生成時の既定値は `not_assessed` です。既存データから状態を消した場合は検査エラーになります。

| 状態 | 意味 |
| --- | --- |
| `not_assessed` | 臨床モデルとして未評価。問題なし・使用可という意味ではない |
| `clinical_hold` | 記録された理由により臨床採用を保留。理由を必須にする |

前回修正の5剤の保留を維持し、血液／血漿基準が未整合のフェロジピンを保留にしました。残り31剤は未評価です。原典修正済み表示は修正記録がある5剤だけに付け、保留状態から推定しません。2026-10-02の監査は過去のsnapshotとして区別します。

### 半減期の自動スクリーニング

採用CL、Vから `implied = ln(2) × V / CL` を計算し、`ratio = implied / recorded_half_life` とします。`abs(ln(ratio)) > ln(1.5)` の場合を **保留候補** と表示します。ちょうど1.5倍および1/1.5倍の境界は候補に含めません。欠落・非正値・非有限値は評価不能です。

現在の候補は10剤です。アブシキシマブ、アシクロビル、アピキサバン、シメチジン、クラリスロマイシン、ダパグリフロジン、フェロジピン、モンテルカスト、オメプラゾール、シルデナフィルです。

候補判定は人の評価状態を書き換えません。閾値内でも臨床妥当性は未判定です。半減期からCLまたはVを作った場合や、CL/Vから半減期を作った場合は、比が1でも独立した一致確認にならないことを併記します。既存の25%相対誤差チェックは変更せず、新しい対称1.5倍チェックと区別します。

## 2. 実行用量を計算用設定として表示する

全37剤の `targets.scenario` に `purpose: computational_stress_test` と `clinical_dose_verified: false` を明示します。実行用量の正本は引き続きspecです。画面・CSVはspecの各armから投与量と点滴時間を取得し、ターゲット側の投与量との一致を検査します。

28剤に100 mgの設定が残っています。これは計算用ストレス用量であり、添付文書の常用量・推奨用量として照合した値ではありません。100 mg以外の設定も、今回臨床用量として承認していません。各薬剤に実際の量、経路、該当する点滴時間を表示します。mg/kgやμg単位の臨床推奨を推測して追加していません。

`adult_healthy`、`elderly_healthy` などは保存された集団コンテキストです。その名称だけで、設定用量を用いた同集団の臨床試験が再現されるとは扱いません。特に非線形PKでは固定値の用量比例外挿を臨床曝露として解釈できません。

## 3. 非線形・時間依存とモデル構造の制約

以下は今回原典を開いて確認した範囲です。制約の確認は、モデルを補正したことや、残る全薬剤の臨床妥当性を確認したことを意味しません。

| 薬剤 | 確認した内容とfixtureの制約 | 原典・箇所 |
| --- | --- | --- |
| カルバマゼピン | 固定投与での自己誘導は3–5週。初期半減期25–65 hから反復投与12–17 hへ短縮する。採用CLと半減期14.5 hは反復投与側の情報であり、未治療者の初回投与PKを表さない | [DailyMed](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=1fc170d7-db1a-486d-8c10-faa6e3da3b1e)、Clinical Pharmacology / Pharmacokinetics。既存URLにアクセスできなかったため、別ラベルを追加出典として記録 |
| クラリスロマイシン | 250 mg q12hで半減期3–4 h、500 mg q8–12hで5–7 h。ラベルは軽度の非線形PKを記載する。固定CL/Vは用量依存性や14-OH代謝物を再現しない。腎CLは比較的用量非依存である | [DailyMed](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=b1bdf526-4f16-4130-b614-4cb678f060d7)、Clinical Pharmacology / Pharmacokinetics |
| フルボキサミン | 100、200、300 mg/dayを10日投与した30例で濃度が用量比例以上に増加。非線形性は確認できるが、CYP2D6飽和が原因とはこの記載だけでは断定しない | [DailyMed](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=35b377d9-5b7a-4d8e-b6c1-4291d02f5dae)、12.3 Absorption / 7.1 |
| アシクロビル | 増量で経口Fが低下し、200、400、800 mgの比較で濃度上昇が用量比例未満。固定F1は用量依存性を表さない。特定の飽和機序までは断定しない | [DailyMed](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=e8a0f9f8-294f-4dd6-bd55-10a6253f1aa8)、Clinical Pharmacology / Pharmacokinetics、Tables 1–2 |
| エファビレンツ | 自己代謝誘導。単回半減期52–76 hと反復40–55 hを区別する。CL/F 13.9 L/hの原著は600 mg QD治療中のHIV患者89例であり、単回側の58 hと組み合わせたV/Fは集団・投与段階を混ぜたfixtureである | [DailyMed](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=13ca3456-e5bf-4bb1-af95-b1378658a358)、12.3 Metabolism / Elimination。[PMID 40851704](https://pubmed.ncbi.nlm.nih.gov/40851704/)、Abstract |
| ベラパミル | 強い初回通過、用量と濃度の非線形関係、反復投与での半減期延長をラベルで確認。ヒト原著では立体選択的な初回通過を確認。単一CL/V/FはR/S異性体や反復投与変化を分離しない | [DailyMed](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c9d71191-b32a-44f9-bc5a-283a06884c82)、Clinical Pharmacology / Pharmacokinetics and metabolism。[PMID 6508982](https://pubmed.ncbi.nlm.nih.gov/6508982/)、Abstract |

## 4. 値の選択方針を全剤で記録する

全37剤の既存 `value_provenance` 各項目へ、選択ルールと理由を記録しました。統一するのは選択の記録・審査手順です。上下限・中点を全剤で同じ数値処理に置換していません。その操作だけでは、集団・用量・製剤・投与段階の異なる値を臨床的に整合させられないためです。

1. 同じ対象集団・投与条件に対応する報告点推定を優先し、報告された平均・中央値を他の統計量と区別する。
2. 範囲しかない場合は、選択した境界・中点・範囲内の旧fixture値と理由を明記する。既存の上下限選択を後から「代表値」と承認しない。
3. 導出値は報告値と分離し、式と入力の由来を残す。CL、V、半減期が独立した観測値であるかを確認する。
4. 現行値を変更するには、原典の条件と採用理由の再確認を要する。情報が足りなければ未評価・保留を維持する。

`recorded_point_value` は、現在の値単位記録にある点の保持を意味します。原典の平均値や中央値という主張ではありません。既存のconversion式・assumptions・rawを併読してください。選択記録の欠落や不明なルールは公開前検査で拒否します。

| 注意する既存選択 | 今回の扱い |
| --- | --- |
| アルプラゾラムのCL・V | 上限、半減期は別の中点。共同推定セットとは扱わず、旧fixture選択として記録 |
| フェロジピンのCL | 1–1.5 L/minの上限。24.5 hは旧ローカルまとめの値で、原典は約25 hと記載 |
| クラリスロマイシンのCL | 捕捉された29.2–58.1 L/hの上限。半減期5 hは別の中点で、用量依存の違いも残る |
| エファビレンツ58 h | 52–76 hの範囲内の旧fixture値。中点64 hとは異なる |
| イトラコナゾールV | `>700 L` の下限を700 Lとして置いた計算用選択。点推定と呼ばない |

## 5. フェロジピンの血液／血漿基準

[既存source_2、PMID 3327676](https://pubmed.ncbi.nlm.nih.gov/3327676/)の総説抄録は、血液からの総CL 1–1.5 L/min、血漿濃度の三相性、約25 hの消失半減期を記載します。採用90 L/hは上限の血液CLです。血漿濃度モデルへそのまま対応させる妥当性は未確認です。

今回、血液／血漿比を確定できていないため数値換算は行わず、血液CLと血漿濃度の基準差を明記して `clinical_hold` としました。約25 hを徐放製剤の吸収律速による値とは断定していません。
