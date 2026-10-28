---
layout: page
title: トップレベル要約と保留理由
permalink: /top-level-context/
---

# トップレベル要約と保留理由

[パラメータ画面](https://y-fukiya.github.io/pkdummy-harness/parameters/) / [生成成果物の評価情報](https://y-fukiya.github.io/pkdummy-harness/atlas-output-semantics/)

## 最初に開くファイルの臨床文脈

薬剤ごとの生成物に加え、`summary.md`、`summary.csv`、`HARNESS_MANIFEST.yml`、`DEMO_MANIFEST.yml`、`HARNESS_STATUS.json`にも臨床評価と計算用投与設定を引き継ぎます。実行状態の `OK` は処理の成功です。臨床モデルとしての承認を意味しません。

複数薬剤のマニフェストと状態JSONは `fixture_contexts` に薬剤別の文脈を保持します。単一薬剤の処理は既存の `fixture_context` を引き継ぎます。保留と未評価が混在する実行に、単一の臨床評価を割り当てません。

Markdownの要約には `Clinical`、`Clinical use`、`Dose purpose`、`Clinical dose verified` を表示します。CSVには、下位の生成物と同じ6つの評価列を追加します。検証失敗でADPCの生成が止まった場合も、文脈を省略しません。

| Drug | Workflow | Validation | Clinical | Clinical use | Dose purpose |
| --- | --- | --- | --- | --- | --- |
| triazolam | OK | OK | clinical_hold | not_approved | computational_stress_test |
| albuterol | OK | OK | not_assessed | not_approved | computational_stress_test |

上表は2例ずつの計算用fixtureを実行した要約です。臨床用量の確認は両剤とも `false` です。既存の濃度・時刻・用量と件数は保持します。

## トリアゾラムの保留理由

見かけのVは、CL/Fと選択した半減期3.5 hから導出しています。独立した観測値ではなく、ln(2)·V/CLとの一致は循環的です。

採用した経口CL/F 526 mL/minは、[健康な若年男性54例への0.5 mg単回投与試験](https://pubmed.ncbi.nlm.nih.gov/3567010/)に由来します。同試験の平均半減期は2.6 hです。一方、fixtureの3.5 hは[添付文書の1.5–5.5 h](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=5add318e-11b9-42f8-b052-0d8cebb32fcf)の中点です。一組として同時推定した値ではなく、100 mgの計算用fixtureを独立した濃度推移で適格性確認していません。

この制約を `simulation_validity.reasons` に記録し、CSVの `HOLD_REASONS`へ引き継ぎます。代謝・尿中回収の記載を直した履歴は `simulation_validity.correction_notes` に分け、画面の修正欄で表示します。原典修正済み5剤の修正記録を同じフィールドへ分けました。薬剤の評価状態、PK数値、spec、targetsは変更していません。

## 保留理由と修正記録の内容を分ける

前回はトリアゾラム以外の4剤で、欄を分けても同じ文章が残っていました。4剤の文章を再分類しました。`reasons` は現行モデルを保留する制約、`correction_notes` は過去に何を訂正したかを記録します。

| 薬剤 | 保留理由 | 修正記録 |
| --- | --- | --- |
| アピキサバン | Vssの一室モデルへの近似、経口半減期との不一致、汎用KA・IIVなどの未適格性 | CLのsystemic基準への訂正、半減期から逆算したVの置換、F1の訂正 |
| シルデナフィル | Vss・終末半減期の構造的不一致、汎用モデル仮定 | 旧CLの置換、Vの基準、FとF1の訂正 |
| モンテルカスト | 高齢者集団と生成集団の差、終末相の不一致、100 mgへの未検証の外挿 | 高齢者と若年者の平均値を混ぜたFの訂正 |
| オメプラゾール | 異なる要約統計と出典条件の組合せ、半減期の不一致、用量・モデル仮定 | CL換算の訂正、採用Vと旧Vの保存履歴、排泄の説明の訂正 |

シルデナフィルの保存raw欄では `section5.2` を `section 5.2` に補正しました。空白以外の原文文字列、科学的数値、逐語引用、換算式、出典URLは保持しています。ほかの補正は説明文中の空白です。

既存のパラメータ契約検査で、両リストの重複した文章と、説明文中の `CL3.3`、`approximately50%`、`section5.2` などの空白欠落を検出します。`F1`、`CYP3A4`、`CDA1` などの正しい識別子を区別し、保存raw・逐語引用・URL・コードや数式の専用欄は検査対象から除外します。この検査は機械的な重複と表記の検査であり、保留理由の薬理学的な十分性を判定するものではありません。

## 独自CSVとSDTM・XPTの境界

`sdtm_like` のEX・PCは、ワークフロー検査用の拡張CSVです。提出用SDTMやXPT v5ではありません。6つの評価列は独自のCSV契約であり、SDTMIGの標準変数とみなしません。ADPCなども提出用ADaMとして認証していません。

[CDISC公式資料](https://www.cdisc.org/sites/default/files/pdf/COSA-Dataset-JSON-Pilot-2023-10-05.pdf)のスライド4には、XPT v5の変数名8文字、フィールド幅200文字などの制約があります。[FDA技術適合性ガイド](https://www.fda.gov/media/153632/download)の3.1.4項にも変数名の制約があります。現在の長い列名・理由文は、そのままXPT v5へ変換するための形式ではありません。理由を切り詰めたり、短い列名へ変えるだけで準拠したと扱ったりしません。

文脈はデータセット単位の情報ですが、CSV単独で取り出した際にも意味を残すため、各行にも保持しています。理由全文を含むマニフェストを併せて保存します。将来の提出版では、対象のSDTMIG・ADaMとメタデータ仕様を定め、観測単位の追加修飾子とデータセット単位の説明を区別して設計する必要があります。XPT出力とCORE準拠検証は今回の変更に含めません。
