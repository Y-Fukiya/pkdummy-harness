---
layout: page
title: 2026-10-28 パラメータ修正記録
permalink: /parameter-corrections/
---

# 2026-10-28 パラメータ修正記録

この記録は、原典を確認できたパラメータの定義、換算、集団、消失経路を修正した範囲を示します。原典と数値が一致することと、臨床用途のモデルが妥当であることは別です。以下の5薬剤は `simulation_validity.status: clinical_hold` を維持します。

## 採用値の変更

比較前の値は、公開アトラスの元になったローカル作業版の値です。古い公開specとの不一致解消と、今回の原典確認による修正を混同しないでください。

| 薬剤 | 項目 | 修正前 | 修正後 | 根拠・変換 |
| --- | --- | --- | --- | --- |
| Omeprazole | systemic CL | 43.56 L/h | 37.44 L/h | 原著抄録の中央値624 mL/minを `624 × 60 ÷ 1000` で換算 |
| Apixaban | CLのbasis | apparent | systemic | ラベルはtotal clearance約3.3 L/hと記載 |
| Apixaban | モデルV | 57.130723619202946 L | 21 L | 半減期から逆算した値を、ラベルのVssに置換。Vssの一室近似であることを明示 |
| Apixaban | F1 | 1 | 0.5 | systemic CLとラベルの絶対バイオアベイラビリティ約50%を併用 |
| Sildenafil | systemic CL | 18.195113489698564 L/hをapparent CL扱い | 41 L/h | Vと半減期からの逆算を廃止。EMA製品情報のtotal body clearanceを採用 |
| Sildenafil | Vのbasis | apparent V/F | systemic Vss | 105 Lという数値は維持。定義を訂正 |
| Sildenafil | FおよびF1 | F=0.44、F1=1 | F=0.41、F1=0.41 | 25–63%の範囲中点ではなく、報告された平均41%を採用 |
| Montelukast | FおよびF1 | 0.615 | 0.61 | 高齢者61%と若年者62%を平均せず、採用CL・V・半減期と対応する高齢者の平均を採用 |
| Triazolam | 消失経路 | 腎排泄 | CYP3A代謝後、主に代謝物が尿中排泄 | 数値パラメータは変更なし |

CL・Vの採用値から `ke = CL/V` を再計算しました。経口systemicのAUCチェック値は `F × Dose × 1000 / CL` に更新し、独立した文献AUCではないことを保持しました。

| 薬剤 | systemic CL（L/h） | モデルV（L） | F1 | モデル暗黙半減期（h、概数） | 保持した出典側半減期（h） |
| --- | ---: | ---: | ---: | ---: | ---: |
| Omeprazole | 37.44 | 16.1 | 0.35 | 0.298 | 0.75、ラベル範囲のfixture中点 |
| Apixaban | 3.3 | 21 | 0.5 | 4.411 | 12、経口投与後の見かけ値 |
| Sildenafil | 41 | 105 | 0.41 | 1.775 | 4、3–5 hのfixture中点 |
| Montelukast | 1.8479999999999999 | 9.7 | 0.61 | 3.638 | 6.7、高齢者IV試験の平均 |

表の概数は説明用です。保存されたパラメータをこの表示桁数に丸め直していません。CLとVssから得た一室モデルの半減期が、原典の終末半減期を再現するとは扱いません。

## Omeprazole

[Regårdhらの原著抄録、PMID 2315973](https://pubmed.ncbi.nlm.nih.gov/2315973/)は、若い健康成人8例に10 mgを静注し、20 mgを経口緩衝液として投与した研究です。systemic CL中央値624 mL/minとIV Vss平均0.23 L/kgを報告しています。CLの換算は37.44 L/h、70 kgでのVss換算は16.1 Lです。中央値CLと平均Vssは同じ種類の要約統計ではありません。

原著のF中央値39%を、ラベルの健康成人20–40 mgにおける30–40%と混ぜていません。今回のfixtureでは従来のラベル範囲中点F=0.35と半減期0.75 hを保持し、それらを原著の一組の推定値とは表示しません。100 mgの投与群は計算用のストレス試験であり、この原著の20 mg経口条件を再現する臨床モデルではありません。

`pk_raw` の旧V記録0.4 L/kgは履歴として保持し、採用Vが原著の0.23 L/kgであることを明示しました。[DailyMedラベル](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=d8b466e0-a35e-4fba-9d43-4e6c0122e7ad)の尿中約77%は代謝物です。未変化体の腎排泄率として読まれないよう記載を訂正しました。

## Apixaban

[DailyMedラベルの12.3項](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=095a08ac-cf0e-497e-a682-ddef38d6b29c)は、総CL約3.3 L/h、Vss約21 L、10 mg以下の経口投与で絶対F約50%、経口投与後の見かけの半減期約12 hを報告しています。総CLをCL/Fとして扱う旧解釈を訂正しました。

V=57.130723619202946 LはCLと12 hから作った値で、独立した分布容積の報告値ではありません。今回は報告されたVss=21 Lを一室Vとして近似的に使います。CL=3.3、V=21の一室モデルが経口12 hを再現しない点を、構造上の制約として残しました。12 hを吸収律速と断定したり、IV半減期5 hを新たな採用値として追加したりしていません。

元の `pk_raw.text` に含まれるapparentという解釈は、旧fixture作成時の記録として保持し、現在のbasis設定を支持する記載とは扱いません。

## Sildenafil

[EMA製品情報の5.2項](https://www.ema.europa.eu/en/documents/product-information/viagra-epar-product-information_en.pdf)は、総CL41 L/h、Vss105 L、絶対F平均41%、終末半減期3–5 hを報告しています。systemic CLとVssにF1=0.41を組み合わせます。`CL/F = 41 / 0.41 = 100 L/h` ですが、今回のspecはsystemic CL=41 L/hを使用するので、さらにCL/Fへ置換しません。

終末半減期範囲の中点4 hはcheck-onlyのfixture値です。これからCLを逆算しません。Vssを一室Vに対応させる近似、汎用KA・ラグ・IIV・残差は引き続きモデルの制約です。

## Montelukast

[原著抄録、PMID 9429741](https://pubmed.ncbi.nlm.nih.gov/9429741/)では、健康高齢者12例の7 mg・5分間静注後にCL平均30.8 mL/min、Vss平均9.7 L、終末半減期平均6.7 hを報告しています。これらの値は保持しました。一般的な健康若年成人のラベル値45 mL/minと2.7–5.5 hを、同じ集団の値として上書きしていません。

同抄録の10 mg経口投与後の高齢者F平均61%を採用しました。若年者の既報62%との中点0.615は廃止しました。高齢者の単回バイオアベイラビリティ比較を、若年者の10 mg・7日反復投与試験と混同していません。

パラメータの由来集団を `elderly_healthy` としました。100 mg経口群は元論文の10 mg経口・7 mg静注条件と異なる計算用fixtureです。生成される体重分布から高齢者の生理や薬物動態が再現されたとは解釈しません。

## Triazolam

[DailyMedラベルの12.3項](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=5add318e-11b9-42f8-b052-0d8cebb32fcf)に従い、CYP3Aによる水酸化、その後のグルクロン酸抱合、主に代謝物としての尿中排泄を区別しました。未変化体の尿中排泄は少量です。CL、V、F、半減期の値は変更していません。

## 変更していないこと

既存のKA、吸収ラグ、IIV、残差誤差、投与量、観測グリッドを原著モデルの推定値へ自動的に置き換えていません。これらの汎用設定は明示的なfixture仮定です。今回の修正でモデル全体の臨床妥当性を認証していません。

2026-10-02の監査はそのときの入力snapshotに対する記録です。今回の修正値を新たに監査済みと宣言するために、過去の監査記録を上書きしていません。

## 評価状態・用量表示の追加修正

全37剤の明示的評価、計算用投与量、対称1.5倍スクリーニング、非線形制約と値の選択方針は[追加修正記録](https://y-fukiya.github.io/pkdummy-harness/fixture-governance/)を参照してください。
