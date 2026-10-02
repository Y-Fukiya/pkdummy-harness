# 全37薬剤のPKパラメーター監査

監査日: 2026-10-02（Asia/Tokyo）。対象: この作業開始時の `drugs/*/pk.yml` 全37薬剤と、対応する `targets.yml`・`spec_pk1_*.yml`。

**全37薬剤を監査した。全パラメーターが正しいという結論ではない。臨床判断用モデルとしての採用は全37薬剤で保留する。** 一次資料の数値と一致していても、対象集団・投与条件・パラメーターの定義・モデル構造・変動の根拠を満たすとは限らない。今回の成果物は不整合と未確認事項を明示する監査結果であり、臨床モデルの認証ではない。

監査対象の111 YAMLファイルのSHA-256は開始時と一致。原データの数値を推測で置換していない。既存の未コミット変更は監査開始時の状態として扱った。`INDEX.csv` / `EXCLUDED.csv` / `pk_library.yml` の編集も本監査では行っていない。

**GitHub掲載時の対象区別:** この監査は、未コミット変更を含むローカル作業ツリーを対象にしている。監査対象そのものは `input-manifest.json` の111ファイルのhashで特定する。監査結果のみをGitHubへ追加しており、未コミットの薬剤データ・実装・テスト一式は同時に公開していない。したがって、掲載先commitのcanonicalデータ全体を監査済み、又は掲載先commitで1002テストを実行済み、とは解釈しない。

## 範囲と判定方法

- CL、V、半減期、Fの **37×4=148項目** を薬剤別に判定。原著・公的ラベル/審査資料の取得範囲（本文/抄録/未取得）を記録し、元の `checked` は再確認済みの証拠として流用しなかった。総説しか確認できない部分は、その限界を各行に記載した。データの `full_label` はFDA審査資料全文も含み、資料の種別はsource_checksに記した。
- ソース値→単位・体重/BSA換算→保存値→モデルtheta→AUC/半減期ターゲットを追跡。投与経路、用量、輸注時間、対象集団、KA/lag、IIV、残差誤差、要約統計、観測時間も確認した。
- 既存生成器の由来台帳720行は内部網羅性の補助であり、720行すべての外部根拠を新規に検証したという意味ではない。モデル・ターゲットの全スカラー値2,193行も別CSVへ保存した。
- 既存83ソース登録の全URLを最新版まで取得した監査ではない。各値に必要な出典を読み直し、補完資料・取得失敗を `source-access.csv` に記録した。DailyMedの同一setidは更新され得る。未記載の版、分析法、試験集団詳細などを推定補完しない。
- 個票濃度データに対する再推定、原PopPKモデルの完全再現、測定法/BLQ処理の全試験監査は今回実施していない。

|判定|意味|件数|
|---|---|---:|
|数値照合 (`VERIFIED_VALUE_ONLY`)|出典の値・換算を照合できた。セット全体や現シナリオへの適合は未承認。|24|
|条件付き (`QUALIFIED`)|値は追えるが、集団・製剤・定義・本文取得範囲等の条件が残る。|46|
|不整合 (`CONTRADICTION`)|出典、換算、定義、統計量又は保存メタデータに具体的不整合がある。|14|
|未確認 (`UNVERIFIED`)|今回の取得資料では根拠又は定義を確認できない。|5|
|仮定 (`FIXTURE_ASSUMPTION`)|範囲の中点/端点、便宜的な代表値、IV入力のF=1等。実測平均ではない。|42|
|派生 (`DERIVED`)|他のパラメーターから計算した値。独立の実測・検証値ではない。|17|

同じ項目に問題が重なる場合は主判定を1つ付け、詳細な制約を理由・必要な対応欄に残した。`不整合` はすべてが薬物の数値誤りという意味ではなく、丸めの未記載や出典の誤帰属も含む。

## 優先して解消する所見

|薬剤|確認した問題|対応|
|---|---|---|
|[omeprazole](group-c.md)|記録の624 mL/minは37.44 L/h。保存43.56 L/hは記録された換算式と一致しない。raw V0.4 L/kgと採用V0.23 L/kgの履歴も分離が必要。 [資料1](https://pubmed.ncbi.nlm.nih.gov/2315973/) [資料2](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=d8b466e0-a35e-4fba-9d43-4e6c0122e7ad)|元研究のmedian CL、mean Vssとその集団を保持して修正案を作り、theta/派生/AUCを一括再計算する。|
|[apixaban](group-a.md)|total CL3.3 L/hをCL/F扱い。一次IV試験のCL3.2–3.5 L/hと保存systemic CL1.65 L/hが不整合。 [資料1](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=095a08ac-cf0e-497e-a682-ddef38d6b29c) [資料2](https://pubmed.ncbi.nlm.nih.gov/34342172/) [資料3](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:34342172&format=json&resultType=core)|systemic/apparentの定義を修正審査。現在10mg、F1=1のAUCはF≈0.5を用いたsystemic計算の約2倍となる。Vss21Lの単純差替えは行わない。|
|[sildenafil](group-c.md)|V105 LはIV Vss。V/Fとしての扱いを支持しない。保存F0.44は参照ラベルの平均41%と異なる。 [資料1](https://pmc.ncbi.nlm.nih.gov/articles/PMC1874258/) [資料2](https://pmc.ncbi.nlm.nih.gov/articles/PMC1874251/) [資料3](https://www.accessdata.fda.gov/drugsatfda_docs/label/2007/020895s027lbl.pdf)|同一研究のCL・V・F・半減期の定義を揃える。範囲25–63%の中点を観測平均へ読み替えない。|
|[inulin](group-b.md)|保存V13 L/70kgは当該研究の実測Vssではなく、Discussionが引用した従来文献の値。研究のVssは11.00 L/70kg。 [資料1](https://pmc.ncbi.nlm.nih.gov/articles/PMC1873801/)|CLの推定法（93.5と主要推定96.1）とVの由来を揃え、派生半減期も再審査。|
|[ethinylestradiol](group-b.md)|保存16.5–17.6hという範囲が該当表で支持されない。現100mgは出典のEE0.02mgと大幅に異なる。 [資料1](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=142c4b90-c9ab-45ce-9172-f1ea7d366686) [資料2](https://pmc.ncbi.nlm.nih.gov/articles/PMC4285808/)|併用製剤・cycle/day・要約統計を固定。半減期から派生したVと100mgデモ条件を臨床用に流用しない。|
|[cda1](group-a.md)|CL0.0014 mL/min/kgとV0.070 L/kgは異なる用量群から選択。半減期も群別幾何平均範囲の中点。 [資料1](https://pmc.ncbi.nlm.nih.gov/articles/PMC2628753/) [資料2](https://pubmed.ncbi.nlm.nih.gov/18502001/) [資料3](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:18502001&format=json&resultType=core)|同じ群・同じ要約統計のパラメーターセットを採用する。|
|[tefibazumab](group-c.md)|主要出典は血液透析中のESRD患者。現scenarioのadult_healthyとは異なる。 [資料1](https://pmc.ncbi.nlm.nih.gov/articles/PMC1610062/)|患者集団と10/20mg/kgの投与条件を保ち、健康成人値と混同しない。|
|[motavizumab_yte](group-c.md)|43–68 mL/dayの中点は55.5。記録式の結果0.0023125 L/hに対し保存値は55 mL/day相当。 [資料1](https://pmc.ncbi.nlm.nih.gov/articles/PMC3837853/)|無記載の丸め/選択を解消し、依存するV・AUCも再審査。|
|[mexiletine](group-b.md)|出典の分布容積5–7 L/kgは、保存V/Fという定義を直接支持しない。CLもそのVと半減期からの逆算。 [資料1](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=ab73778b-6794-441c-b127-610a6d0733ea) [資料2](https://pubmed.ncbi.nlm.nih.gov/10589372/) [資料3](https://www.medicines.org.uk/emc/product/13305/smpc)|IV/経口とF補正の有無を一次試験で確定するまで派生systemic値を採用しない。|
|[erythromycin](group-b.md)|出典の125mg IVは30分輸注、現specは1時間。 [資料1](https://pmc.ncbi.nlm.nih.gov/articles/PMC3581054/)|用量一致だけでなく入力速度も原条件へ対応づける。|

dapagliflozinの77.8%→0.78は既存注記では丸めと説明されているが、登録式 `77.8/100` の結果は0.778である。これは上記の大きなbasis誤分類と同列の数値誤りではなく、精度・丸め規則の記載不一致として扱う。mefenamic acidはDailyMedとFDA版でCL21.23/21.13の差があり、数値と版の対応を残す必要がある。

## 全薬剤に共通する採用上の制約

1. **CL/Vと半減期の違いを、数値を合わせて消さない。** 1-compモデルなら `t½=ln(2)×V/CL` だが、多compのVss、Vz、Vcは互換ではない。Vss/CLはMRTに関係し、一般に終末半減期を直接再現しない。異なる相・集団の代表値を一組へ混ぜない。
2. **18薬剤はCL・V・半減期のいずれかを他の値から逆算している。** 同じ半減期への一致は独立検証にならない。依存関係は `internal-audit.json` に記録。36薬剤のAUCも同じCLから計算した整合性ターゲットであり、独立の臨床AUCではない。sufentanilの0.278 ng*h/mLはlabelの278 h*pg/mLを換算した独立出典値として確認したが、これだけでモデル全体を検証したことにはならない。
3. **個体間変動と残差誤差は全37薬剤で汎用設定。** IIVはCL0.09、V0.04、吸収モデル25薬剤のKA0.16（実装上OMEGAの分散、CVやSDではない）。残差はprop0.25/add0、相関なし。各薬剤の原PopPK推定値ではない。25薬剤のKA=1.2 /h、ALAG1=0.5hも共通の仮定であり、原著吸収モデルの再現ではない。
4. **ターゲットの統計量を実測と混同しない。** 全37薬剤の半減期summaryはarithmetic_meanだが、元が中央値、幾何平均、範囲、中点、又は派生計算のものを含む。半減期SDは30薬剤が1h、残りも便宜的設定。AUC変動は全37薬剤がGCV35%で、独立出典AUCにもこの仮定が付く。典型値、母集団平均、変動、推定不確実性を区別する。
5. **28薬剤に100mgのデモ用量。** 100mgで統一できる科学的根拠はなく、非線形PK、酵素誘導/阻害、製剤、食事、併用薬などの適用条件を超え得る。用量は監査ファイルに記録した現値であり、投与推奨ではない。70kg換算とBSA1.73m²の値も区別し、人口分布から自動的に個人のPKが検証されたとはみなさない。
6. **長い半減期の観測窓が不足するケース。** motavizumab MEDI-524は168/636h、YTEは72/2040h、tefibazumabは168/420h（観測終了/保存半減期）。これは1半減期未満という記述であり、一律の合否閾値ではない。終末相サンプル・定量下限・AUC外挿率を用途ごとに評価する。

FDAの[Population Pharmacokinetics guidance（2022、V.C–D）](https://www.fda.gov/media/128793/download)も、用途に応じたモデル評価、外挿の不確実性、個体間変動と推定不確実性の区別を求めている。今回の臨床採用保留は、現在のモデルと証拠に対する本監査の判断であり、FDAによる個別薬剤の不適合判定ではない。

## 全37薬剤の判定一覧

数値照合＝出典値の照合のみ。すべて臨床採用は保留。詳細は薬剤名のリンク、148行のCSV/JSONを参照。

|薬剤|CL|V|t½|F|主要所見|
|---|---|---|---|---|---|
|[abciximab](group-a.md)|数値照合|未確認|不整合|仮定|CLの転記・換算は確認。Vssの一次学会抄録を再取得できず、短い血漿相をterminal targetに用いる点と異研究CL/Vの組合せは採用保留。|
|[aciclovir](group-a.md)|条件付き|条件付き|仮定|仮定|CL/Fの二重補正はないが、BSA基準CL、別総説Vss、経口F下限の混成。数値出典の存在と単回100mgモデル妥当性は別。|
|[albuterol](group-a.md)|数値照合|派生|数値照合|仮定|健康成人IV研究のCLと半減期を再確認。Vは観測値ではなく逆算であり、半減期チェックの独立性を否定するメタデータ修正が必要。|
|[alfentanil](group-a.md)|数値照合|仮定|仮定|仮定|注射labelのCL・V範囲・半減期範囲は再確認。3-comp由来の代表値を1-compへまとめ、V上限と半減期中点を組むため臨床採用は保留。|
|[alprazolam](group-a.md)|条件付き|条件付き|仮定|仮定|総説の範囲は再取得できたがCL/V上限と半減期中点は一組の被験者推定値ではない。一次1mg試験と100mg fixtureは対応しない。|
|[amikacin](group-a.md)|数値照合|数値照合|不整合|仮定|CL約100mL/min・V24Lはlabelどおり。半減期の「2時間をやや超える」を厳密な2.0hへ変えた点、IV bolus条件は修正審査が必要。|
|[apixaban](group-a.md)|不整合|派生|数値照合|条件付き|total CLをCL/Fと解釈したbasisが一次IV研究と不整合。現10mg経口fixtureはFを二重に誤解し得るため優先修正審査。|
|[atazanavir](group-a.md)|数値照合|数値照合|条件付き|未確認|CL/FとV/Fの数値・定義は原著Table3と一致するが、HIV定常状態・RTV条件をhealthy単回100mgへ流用。吸収パラメータも原モデルと異なる。|
|[buprenorphine](group-a.md)|条件付き|不整合|派生|仮定|CLは原著と一致。V806は原著806.4の丸めで、terminal半減期25hの代わりに10.35hを逆算したfixture。原著Table1のV単位も内部確認が必要。|
|[carbamazepine](group-a.md)|条件付き|派生|仮定|未確認|元label URLは再取得失敗。別公式ER labelが反復投与CL80mL/minと12–17hを支持するが、現200mg単回への適用は未支持。|
|[cda1](group-a.md)|数値照合|数値照合|仮定|仮定|原著本文まで取得し数値所在を確認したが、CLとVは異なる用量群、半減期は幾何平均範囲の中点。単一集団のパラメータセットとして採用不可。|
|[cimetidine](group-a.md)|数値照合|条件付き|数値照合|条件付き|200mg IV/経口の潰瘍患者研究でCL495、Vss.8、F約.6を確認。healthy100mgへの適用とVssを1-comp Vへ置く妥当性は別途必要。|
|[clarithromycin](group-a.md)|未確認|条件付き|仮定|仮定|CL範囲の総説と自己阻害モデルのV/Fを混成。58.1のCL/F分類は総説抄録から確定できず、用量依存半減期とFの中点化も未承認。|
|[dapagliflozin](group-b.md)|数値照合|条件付き|条件付き|条件付き|静注CLとVssの数値はFDA審査資料で一致。経口終末半減期を再現する一組ではなく、Fの丸め説明が不足。|
|[efavirenz](group-b.md)|条件付き|派生|仮定|仮定|CL/Fの数値は原著で確認したが、HIV反復投与モデルのCLを健常者単回fixtureへ移植し、V/Fとkaも原著と異なる。|
|[erythromycin](group-b.md)|数値照合|派生|数値照合|仮定|健常群のCLと半減期は原著一致。Vは導出で、投与時間が原著30分と現spec1時間で違う。|
|[ethinylestradiol](group-b.md)|条件付き|派生|不整合|仮定|配合錠の周期内PKを単剤100 mgへ移植している。半減期範囲の出典帰属と絶対Fの一次根拠が不十分。|
|[felodipine](group-b.md)|条件付き|条件付き|仮定|条件付き|レビューの血液CL上限とV/終末半減期を合成。公式ラベルでは血漿CL・製剤別半減期が異なり、100 mgへの外挿も未検証。|
|[fluconazole](group-b.md)|条件付き|派生|条件付き|仮定|元setidのラベルは取得不可。別の公式ラベルで数値を再確認したが、Vは導出、静注200 mgの同一試験組としては未検証。|
|[fluvoxamine](group-b.md)|派生|条件付き|仮定|数値照合|F53%とV約25 L/kgは確認。ただしV/Fという定義と9–28 hの単回代表値は未確認で、導出CLに影響する。|
|[inulin](group-b.md)|条件付き|不整合|派生|仮定|13 Lは当該試験Vssの実測値ではなくDiscussionの過去文献一般論。原著の健常者Vssは11.00 L/70kgで、出典帰属の誤りがある。|
|[itraconazole](group-b.md)|数値照合|仮定|仮定|条件付き|CLと経口Fの数値はラベル支持。V>700 Lを700 Lに置くこと、22 hの中点と1comp線形化はfixture仮定に限定。|
|[mefenamic_acid](group-b.md)|不整合|条件付き|仮定|条件付き|21.13 L/hはFDA2024版で支持されるが、引用先DailyMedの現本文は21.23。値と出典版の対応修復が必要。|
|[metoprolol](group-b.md)|数値照合|派生|仮定|未確認|静注CL48 L/hは原著抄録で支持。Vの参照ラベル帰属とFのCmax比からの確定に問題が残る。|
|[mexiletine](group-b.md)|派生|不整合|仮定|条件付き|V範囲と引用source_idが混線。V/Fの定義は確認できず、systemic換算と派生CLも保留。|
|[moclobemide](group-c.md)|条件付き|条件付き|数値照合|条件付き|初回IVのCL/Vss/半減期と初回経口Fは原著抄録と一致。反復投与に依存する薬物動態を単一組へ一般化できない。|
|[montelukast](group-c.md)|条件付き|条件付き|数値照合|仮定|保存CL/Vss/半減期は高齢健常者7 mg IV由来。F=.615は高齢/若年の異なる平均61%/62%を折半したfixtureであり実測平均ではない。|
|[motavizumab_medi_524](group-c.md)|仮定|仮定|仮定|仮定|原著本文・Table 2を再取得。親抗体motavizumabの成人IV用量群範囲から中点を生成しており小児RSV予防の値ではない。|
|[motavizumab_yte](group-c.md)|不整合|派生|仮定|仮定|Fc変異体と親抗体を区別して一次本文確認。CLの「43–68の中点」記録と保存55 mL/dayが不一致。|
|[omeprazole](group-c.md)|不整合|条件付き|仮定|仮定|原著抄録624 mL/minに対し保存43.56 L/hは換算誤り。Vss 0.23 L/kgは確認できるがraw0.4 L/kgや旧注記が矛盾する。|
|[raltegravir](group-c.md)|条件付き|派生|条件付き|不整合|CL/F60.2は二室PopPK原著Table 2に一致。F=1は相対スケールなのにsystemic値を生成しており、Vは別研究半減期との混成導出。|
|[sildenafil](group-c.md)|不整合|不整合|条件付き|不整合|V105 LをV/Fとした基礎の誤り、および平均F41%に対する保存44%を確認。既存source_2はED作用発現試験でPKパラメータの直接推定論文ではない。|
|[sufentanil](group-c.md)|数値照合|派生|数値照合|条件付き|現ファイルは30 mcg舌下投与と正しく区別。CL/F108 L/h、13.4 h、F53%、AUC0-inf .278 ng*h/mLをDSUVIAラベルで再確認。|
|[tefibazumab](group-c.md)|条件付き|条件付き|仮定|仮定|数値は原著のESRD血液透析患者8名10/20 mg/kg IV要約と一致。adult_healthy 100 mg単回シナリオへの一般化を採用保留。|
|[tizanidine](group-c.md)|派生|条件付き|数値照合|条件付き|ラベルのVss/F/半減期は確認。CL46.5795 L/hはIV Vssと経口半減期を混ぜたfixture導出であり臨床CLとして未検証。|
|[triazolam](group-c.md)|条件付き|派生|仮定|条件付き|CL/F31.56 L/hの原著値とF44%の別一次抄録を確認。ただしVは別出典半減期中点との合成で、100 mgへの臨床外挿は支持されない。|
|[verapamil](group-c.md)|条件付き|条件付き|仮定|条件付き|6名のIV/経口原著でCL、Vd(area)、Fを確認。半減期5.1 hは別ラベル範囲中点で、二室研究の終末相4.21 hとは異なる。|

## 既存11警告の再確認

この25%閾値はリポジトリの機械的警告基準であり、臨床的同等性の基準ではない。警告なしの26薬剤を検証済みと扱わない。

|薬剤|保存t½ (h)|ln(2)×V/CL (h)|
|---|---:|---:|
|abciximab|0.41666667|6.3633184|
|aciclovir|2.5|1.6486681|
|alfentanil|1.675|2.3104906|
|amikacin|2|2.7725887|
|cimetidine|2|1.3069442|
|clarithromycin|5|2.052002|
|dapagliflozin|12.9|6.5854563|
|felodipine|24.5|5.3911447|
|itraconazole|22|29.08891|
|montelukast|6.7|3.6382725|
|omeprazole|0.75|0.25619076|

## 機械検証と再現性

- 開始時 `make validate`: 通過、上記11警告あり。
- Python3.12.2の監査用一時venv（PyYAML6.0.3、pytest9.1.1）で `make harness-check`: **終了コード0**。pytestは**1002件中701成功、301スキップ、失敗0**。
- スキップ: SAS299件、PKNCA/rpy2比較1件、Quarto DOCX生成1件。Quartoはsandboxのsysctl/architecture判定で失敗してskip。
- external-validation-probeは `execute=false`。nlmixr2はprobeのみ成功、NONMEM/Phoenix実行ファイルなし。実行・相互一致・臨床予測精度の証拠にはしない。
- 初回Python3.10では3件失敗: 日本/米国の背景分布CSVで浮動小数点末尾のbyte不一致2件、ISO日時小数秒の例外メッセージ不一致1件。3.12で同じ5ケース再確認と全体チェックは通過。3.10互換性の問題は残し、コードを書き換えて隠していない。
- 文書化された換算/派生123項目の再計算: 一致115、式と保存値の差3、自動評価対象外5。対象外は手動レビューに明示し、全式合格とはしていない。
- 内部のtheta/derived/target/F1方針の対応チェックは37薬剤で矛盾なし。ただし、元のbasis自体が誤っていても内部は整合する。これはapixaban等の科学的問題を否定しない。

以下は監査時の実行記録であり、`/private/tmp/...` の環境を公開配布しているものではない。別環境ではPython3.12のvenvにPyYAMLとpytestを導入し、そのpythonへ置き換える必要がある。加えて、`audit_internal.py` は111入力すべてのhash一致を必須とするため、GitHubのfresh cloneだけでは元の未コミットsnapshotを再現できず、意図どおり停止する。保存済み判定の再集計 `consolidate.py` は標準ライブラリだけで実行できる。

```bash
PYTHONDONTWRITEBYTECODE=1 /private/tmp/pk-audit-20261002-py312/bin/python docs/research/2026-10-02-all-drug-audit/audit_internal.py
PYTHONDONTWRITEBYTECODE=1 /private/tmp/pk-audit-20261002-py312/bin/python docs/research/2026-10-02-all-drug-audit/consolidate.py
PYTHONDONTWRITEBYTECODE=1 make harness-check PYTHON=/private/tmp/pk-audit-20261002-py312/bin/python
```

## 収集botに必要な採用条件

収集値をそのまま臨床モデルへ昇格させず、薬剤・analyte・matrix・total/unbound、CL/CL/F、Vss/Vz/Vc/V/F、投与経路・製剤・dose moiety・量・輸注時間・単回/反復/定常状態・食事・併用薬、対象人数/年齢/腎肝機能、要約統計と変動の種類、原典版/表/脚注、原文字列と換算式を1レコードとして保持する。

原典値、派生値、範囲からの選択、仮定を分け、異なる群を結合しない。必須の定義・集団・原典が未確認なら `needs_review` に残す。算術不一致、出典誤帰属、相/統計量の不一致は自動採用を止める。モデルの用途を固定し、独立観測データによる妥当性評価と薬剤別変動の検証後に採用判断を行う。

## 成果物

- [全148パラメーターの監査CSV](core-parameter-audit.csv) / [全37薬剤の構造化JSON](all-drug-audit.json)
- [薬剤別詳細 A](group-a.md) / [B](group-b.md) / [C](group-c.md)
- [指摘・必要な対応](review-findings.csv) / [取得成否と補完経路](source-access.csv)
- [原文取得ファイル27件のURL・SHA-256](source-capture-manifest.json)（shellで保存した分のみ。原文は一時フォルダにあり、永続アーカイブではない。Web取得のみの資料はsource-access参照）
- [全薬剤の内部値・モデル条件](all-drug-internal.csv) / [換算再計算](arithmetic-checks.csv) / [全model・targetsスカラー](model-and-target-scalars.csv)
- [既存由来台帳720行](provenance-inventory/PARAMETER_PROVENANCE.csv)（既存のreview状態は今回の外部確認結果ではない）
- [開始時入力hash](input-manifest.json) / [機械チェックJSON](internal-audit.json)
- [harnessログ](harness-check-py312.log) / [pytest XML](test-results-py312.xml) / [検証要約](test-summary.json) / [初回3.10失敗ログ](initial-tests-py310.log)

前回のHermes caffeine候補1件はこの37薬剤ライブラリには含まれない。別監査のローカル文書は `docs/research/2026-10-02-pk-collector-reverification.md`（今回のGitHub掲載範囲外）。今回の全薬剤監査はその限定監査を37薬剤へ拡張したもので、Hermesの実行状態・公開・自動採用設定を変更したという主張ではない。
