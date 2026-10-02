# 全薬剤PK監査 — group C

確認日: 2026-10-02。対象12薬剤、48主要項目。canonicalファイルは変更していない。

qualified_fixtureは出典と仮定を明示した合成workflowに限る。臨床適格、専門家承認、全モデル検証を意味しない。holdは個別の数値・基礎・集団等の未解決矛盾あり。

## 重要所見

- Omeprazole: 624 mL/minの換算は37.44 L/h。保存43.56は数式不一致。
- Sildenafil: 105 LはIV由来Vss。V/Fとの解釈およびF44%の採用は原資料と矛盾。
- Motavizumab-YTE: 43–68 mL/dayの厳密中点は55.5。保存55は中点というprovenanceと不一致。
- Tefibazumab: 引用値の対象はESRD血液透析患者。adult_healthyシナリオと不一致。
- Raltegravir: モデルF=1は相対スケール。absolute Fやsystemic CL/Vとしての換算は不適切。
- Sufentanil: 現在の30 mcg舌下・CL/F108・半減期13.4・F53%・AUC .278 ng*h/mLはラベルと一致。Vと吸収パラメータは合成モデル仮定。

## 薬剤別監査

### moclobemide — qualified_fixture

初回IVのCL/Vss/半減期と初回経口Fは原著抄録と一致。反復投与に依存する薬物動態を単一組へ一般化できない。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | QUALIFIED | source_5の12名の正常男性、初回IV CL=39.4 L/hを直接保存。反復経口投与後のIV CL=29.1 L/hとは別条件。 | 初回IV由来を保持し、反復・疾患群へ外挿しない。原著全文で投与条件・採血・推定法を確認する。 |
| volume | QUALIFIED | source_5の初回IV Vss=84.3 Lを確認。70 kg換算値ではなく研究集団の絶対値。Vssを1区画Vに採用することは追加仮定。 | Vssの定義を明記し、Vz/Vcとの互換性を主張しない。 |
| half_life | VERIFIED_VALUE_ONLY | 初回IV elimination half-life 1.60 hを確認。抄録の15%はCVでありSDではない。targetsのSD=1 hは原著由来ではない。 | CVとfixture SDを分離し、初回IV半減期の経口転用を明示する。 |
| bioavailability | QUALIFIED | 初回経口F=0.56を確認。同研究の1週/2週では0.86/0.90であり恒常値ではない。100 mg t.i.d.反復期間と初回単回を区別する。 | 初回経口条件を明記する。定常状態モデルには独立再評価が必要。 |

参照資料:
- [retrieved](https://pubmed.ncbi.nlm.nih.gov/3665338/) — PubMed通常HTMLはchallenge。NCBI公式efetch XMLから同一PMIDの抄録を実取得。本文未取得。
- P2: spec.meta.sourcesにcanonical採用source_5がなく、旧PK要約が残る。 対応: meta出典・要約とcanonical provenanceを対応させる。

### montelukast — qualified_fixture

保存CL/Vss/半減期は高齢健常者7 mg IV由来。F=.615は高齢/若年の異なる平均61%/62%を折半したfixtureであり実測平均ではない。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | QUALIFIED | 30.8 mL/min×60/1000=1.848 L/hは正しい。source_1の高齢健常者N=12、7 mg/5分IVのsystemic CL。 | 高齢者/IV/7 mgを記録しadult_healthy 100 mg経口と同条件扱いしない。 |
| volume | QUALIFIED | 9.7 Lはsource_1の高齢者IV Vss。CLと同条件の値だが1区画Vではない。 | Vss型を明記し終末相半減期との単純対応を採用根拠にしない。 |
| half_life | VERIFIED_VALUE_ONLY | 高齢健常者IVの平均終末半減期6.7 hは一致。保存CL/Vssの1区画半減期は約3.64 hであり、数値の誤記ではなく区画構造の不一致。 | 終末相を再現するなら原著の多区画性を評価する。 |
| bioavailability | FIXTURE_ASSUMPTION | 10 mg経口で高齢者平均61%、既報若年者62%。.615は別群平均の中点で、統合推定値でも同一個体のFでもない。抄録は高齢者Fを7日反復後とは明示しない。 | .615を実測値と扱わず、対象群に対応するFと時点を全文で確定する。 |

参照資料:
- [retrieved](https://pubmed.ncbi.nlm.nih.gov/9429741/) — PubMed通常HTMLはchallenge。NCBI公式efetch XMLでAbstractを取得。
- P2: F provenanceの「10 mg経口、7日投与後」は抄録からは確定できない。若年者反復PKと高齢者F比較を混同する余地がある。 対応: 原著の試験別条件を分離して記録する。
- P2: 1区画fixtureの100 mg経口シナリオは引用研究10 mg経口/7 mg IVと異なる。 対応: 100 mgを臨床検証済み条件としない。

### motavizumab_medi_524 — qualified_fixture

原著本文・Table 2を再取得。親抗体motavizumabの成人IV用量群範囲から中点を生成しており小児RSV予防の値ではない。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | FIXTURE_ASSUMPTION | 本文165–326 mL/dayの中点245.5÷1000÷24=.0102291667 L/hは算術一致。0.3/3/15/30 mg/kgの各用量群を横断する中点で単一研究推定平均ではない。 | 用量群別の値を保持し、範囲中点を実測・PopPK代表値としない。 |
| volume | FIXTURE_ASSUMPTION | 本文の親抗体Vss 5.2–9.5 Lの中点7.35 Lは一致。原著のVssであり分布容積の型を曖昧にしない。 | Vssと一室Vの相違および群横断中点を明示。 |
| half_life | FIXTURE_ASSUMPTION | 本文の19–34日を中点26.5日×24=636 hに変換。Table 2には各群18.9/22.3/20.4/34.4日があり、中点は観測平均ではない。 | rounded range由来のfixtureであることを保持し平均/SDとして再解釈しない。 |
| bioavailability | FIXTURE_ASSUMPTION | F=1は静脈投与経路のモデル定義。原著は成人単回IVであり、吸収率を測ったF=100%の結果ではない。 | bioavailability measuredではなくIV route definitionとして扱う。 |

参照資料:
- [retrieved](https://pmc.ncbi.nlm.nih.gov/articles/PMC3837853/) — Web openはchallenge。curlでPMC HTML本文159038 bytesを取得しMethods/Results/Table 2を確認。
- P2: 原著は健常成人31名中親抗体15名、開発中の抗体比較。100 mg固定用量や小児・IM投与のパラメータとは一致しない。 対応: 候補抗体・成人・単回IV・用量群を必須メタデータにする。

### motavizumab_yte — hold

Fc変異体と親抗体を区別して一次本文確認。CLの「43–68の中点」記録と保存55 mL/dayが不一致。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | CONTRADICTION | 本文の43–68 mL/dayを確認。保存.0022916667 L/hは55 mL/dayだが、記載された中点式なら55.5 mL/day=.0023125 L/h。丸めまたは値選択の根拠がない。 | 55を選んだfixture方針か厳密中点かを決め、raw/式/normalizedを一致させる。監査では値を変更しない。 |
| volume | DERIVED | 保存6.744599 Lは選択CL55 mL/day×85日/ln2。原著Vss 4.6–8.3 Lの報告値ではなく、終末半減期とCLから作った一室V。 | CL選択矛盾を解決後、derived VをVssと混同しない。 |
| half_life | FIXTURE_ASSUMPTION | 本文70–100日の中点85日×24=2040 hは一致。Table 2の群別69.5/100.4/84.3/73.2日を要約したfixture。 | 85日を実測平均とせず、Vの導出入力に使用した事実を記録する。 |
| bioavailability | FIXTURE_ASSUMPTION | F=1は成人静脈投与のモデル定義。YTE変異体の成人IVデータを親抗体、他YTE抗体、小児へ転用しない。 | 製品同一性をM252Y/S254T/T256E変異体まで識別する。 |

参照資料:
- [retrieved](https://pmc.ncbi.nlm.nih.gov/articles/PMC3837853/) — curlでPMC本文を取得。31名の健常成人、YTE16名/親抗体15名、0.3/3/15/30 mg/kg単回IV。
- P1: CL式の厳密中点55.5と採用55が食い違う。 対応: 数式provenanceを修復して下流CL/V/AUCへの影響を再評価。
- P2: Vは半減期から導出しているのに、t_halfはCL/V再調整に使っていないと記載。 対応: 校正に使った半減期と独立検証ターゲットを区別する。

### omeprazole — hold

原著抄録624 mL/minに対し保存43.56 L/hは換算誤り。Vss 0.23 L/kgは確認できるがraw0.4 L/kgや旧注記が矛盾する。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | CONTRADICTION | source_4抄録は8名の若年健常者、10 mg IV/20 mg緩衝経口液、systemic CL中央値624 mL/min。式624×60/1000=37.44 L/hであり保存43.56 L/hとは一致しない。 | 監査差分として37.44との算術不一致を修正候補化し、関連derived/theta/AUCを再計算・検証する。 |
| volume | QUALIFIED | source_4の平均IV Vss 0.23±0.04 L/kg、70 kg仮定で16.1 Lは一致。pk_rawは0.4 L/kg、basis_noteはunresolvedのままで保存値と説明が不一致。 | rawの旧値と新採用値の系譜を明確にする。70 kgは標準化仮定で原集団平均体重とはしない。 |
| half_life | FIXTURE_ASSUMPTION | source_2の健常者ラベル0.5–1 hに.75 hは含まれるが中点は観測平均ではない。source_4のIV中央値35分/経口39分とは別の要約。 | ラベル範囲と原著中央値を別扱いにし、.75 hをarithmetic_mean実測値としない。 |
| bioavailability | FIXTURE_ASSUMPTION | ラベル遅延放出20–40 mgのF約30–40%から.35を作ったfixture。40 mgを超えると初回通過飽和によりAUCが非線形で、100 mgへ一定Fとしての外挿は非検証。 | 100 mgシナリオを採用条件から外すか用量/製剤に合った独立一次データを取得する。 |

参照資料:
- [retrieved](https://pubmed.ncbi.nlm.nih.gov/2315973/) — PubMed抄録本文をWeb openで取得。全文未取得。
- [retrieved](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=d8b466e0-a35e-4fba-9d43-4e6c0122e7ad) — DailyMed全ラベルを取得。repackaged label、2011-01-12更新、遅延放出カプセル。
- P1: CLの単位換算が原値・式と一致せず、下流theta/AUCにも影響する。 対応: 43.56がどこから来たかを追跡して修復する。
- P1: 100 mg経口へ30–40% Fを適用しているが、ラベルは40 mg超で非線形性を記載。 対応: 濃度やAUCを臨床予測値としない。対象条件に合った入力が必要。

### raltegravir — hold

CL/F60.2は二室PopPK原著Table 2に一致。F=1は相対スケールなのにsystemic値を生成しており、Vは別研究半減期との混成導出。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | QUALIFIED | source_1 Table 2のCL/F=60.2 L/h（SE44.3%）を確認。HIV陽性/健常混合二室モデル。provenanceのexact_quoteは半減期の文章でCLを裏付けない。 | CL引用・locatorをTable 2へ対応させる。CL/Fとsystemic CLを分離。 |
| volume | DERIVED | 677.431883 L=60.2×7.8/ln2は算術一致だが二室原著V1/F223 L、V2/F113 Lとは異なる合成V/F。7.8 hは別の健常者試験由来。 | derived one-compartment V/Fとして隔離し、観測Vss/Vz/Vcとはしない。 |
| half_life | QUALIFIED | source_2同一論文PMC3165315は男性健常者6名、400 mg単回経口、血漿GM半減期7.8 h、95%CI5.5–11.3を確認。保存targetsのarithmetic_meanとは統計量が違う。 | GM/95%CIを保持し、CIを患者範囲やSDに変換しない。 |
| bioavailability | CONTRADICTION | source_1 Table 2の健常群F=1は固定した相対Fスケール。実測absolute F=1ではない。保存bioavailability_frac=1からsystemic CL/Vへ変換する根拠はない。 | absolute Fは未確定として分離し、apparent用F1=1のみをモデル規約として保持する。 |

参照資料:
- [retrieved](https://pmc.ncbi.nlm.nih.gov/articles/PMC3370715/) — Web openはchallengeだったがcurlでPMC全HTML取得。Methods/Results/Tableを直接確認。
- [retrieved](https://pmc.ncbi.nlm.nih.gov/articles/PMC3165315/) — Web openはchallengeだったがcurlでPMC全HTML取得。Methods/Results/Tableを直接確認。
- P1: 相対F=1をabsolute Fと解釈したsystemic値は根拠がない。 対応: systemic派生値を採用保留にし、relative/model Fとabsolute Fを別項目にする。
- P2: 半減期GMをarithmetic_meanにしている。CL exact_quoteも誤対応。 対応: 統計型とsource locator/quoteを訂正する。

### sildenafil — hold

V105 LをV/Fとした基礎の誤り、および平均F41%に対する保存44%を確認。既存source_2はED作用発現試験でPKパラメータの直接推定論文ではない。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | CONTRADICTION | 18.1951 L/hは105×ln2/4の一室導出。105 LをV/Fとする前提が誤りで、追加一次論文Table1のIV CLは40.8 L/h。前者を観測CL/Fまたはsystemic CLとして採用できない。 | systemic CL/Vssと終末半減期の関係を再設計し、原著の観測CL/Fと混同しない。 |
| volume | CONTRADICTION | FDA source_3はVss105 Lと記載しV/Fとは書かない。追加一次PMC1874258 Methods/Table1はIV後算出と明示。本文のapparentという語だけからV/Fへ読み替えた現在basisは誤り。 | 105 Lをsystemic IV Vssとして再分類し、F補正・theta・派生値を影響評価する。 |
| half_life | QUALIFIED | 4 h自体はDailyMed source_1の終末半減期約4 hに一致。source_2は効力持続の論文で、そこでの既報PK要約を新たなPK推定値とは扱わない。 | ラベル由来約4 hと原著の調和平均等を区別し、VssからCLを算出する独立根拠にしない。 |
| bioavailability | CONTRADICTION | source_1ラベルは平均absolute F41%（範囲25–63%）。保存.44は範囲の中点に相当するが、rawの41%にも原著Table1の41%にも一致せず導出説明もない。 | 平均41%と範囲を保持し、44%を実測平均とする記録を是正する。 |

参照資料:
- [retrieved](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=7086e222-0f2b-4c02-84c0-4f8635c90993) — DailyMedラベルおよび2007 FDA添付文書PDF本文をWeb取得。FDA文書はclinical reviewではなくlabel。
- [retrieved](https://www.accessdata.fda.gov/drugsatfda_docs/label/2007/020895s027lbl.pdf) — DailyMedラベルおよび2007 FDA添付文書PDF本文をWeb取得。FDA文書はclinical reviewではなくlabel。
- [retrieved](https://pmc.ncbi.nlm.nih.gov/articles/PMC1874258/) — curlでPMC全HTML取得。追加一次PMC1874258は健常男性50 mg IV/経口クロスオーバーN=12; 100 mg食事試験N=34も報告。
- [retrieved](https://pmc.ncbi.nlm.nih.gov/articles/PMC1874251/) — curlでPMC全HTML取得。追加一次PMC1874258は健常男性50 mg IV/経口クロスオーバーN=12; 100 mg食事試験N=34も報告。
- [failed](https://labeling.pfizer.com/ShowLabeling.aspx?id=14610) — Pfizer Error.htmへリダイレクト。採用根拠に未使用。
- P1: systemic IV Vss105 Lをapparent V/Fと誤解釈し、さらにFを乗じてsystemic V46.2 Lを生成している。 対応: V basis/CL導出/theta/F適用を一括再評価する。
- P1: 原資料平均F=.41に対し保存.44で、provenanceがない。 対応: 平均と範囲中点を混同しない入力へ修復する。
- P2: source_3の種類をFDA clinical reviewと記載し、存在しないexact_quoteを付けている。 対応: 文書種別labelと正確なlocatorへ訂正する。

### sufentanil — qualified_fixture

現ファイルは30 mcg舌下投与と正しく区別。CL/F108 L/h、13.4 h、F53%、AUC0-inf .278 ng*h/mLをDSUVIAラベルで再確認。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | VERIFIED_VALUE_ONLY | DSUVIA単回舌下投与後の平均apparent plasma CL108 L/hを確認。F1=1によるCL/Fモデル規約は整合。経口嚥下CLとして転用できない。 | source populationの詳細は原PK試験へ遡る。ラベル平均から個体分布を作らない。 |
| volume | DERIVED | 2087.868 L=108×13.4/ln2は算術一致。ラベルにこの観測Vdはなく、一室終末相を合わせる見かけVのfixture。 | 導出Vとして扱い、半減期一致を独立モデル検証と数えない。 |
| half_life | VERIFIED_VALUE_ONLY | ラベル単回平均terminal half-life13.4 hは一致。反復投与、IV半減期や作用時間とは区別する。 | targets.used_to_calibrate_cl_v=falseの説明を、V導出に使った事実と整合させる。 |
| bioavailability | QUALIFIED | 30 mcg舌下のabsolute F約53%、比較基準は30 mcg/1分IV。嚥下した経口製剤の9%とは明確に異なる。 | SLとGI oralを明示し続ける。F1=1は絶対F100%の意味ではない。 |

参照資料:
- [retrieved](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=8b580f3d-e3b5-4086-b093-87a980631147) — DailyMed全ラベルをWeb取得。改訂12/2025、§12.3を確認。
- P2: targets.aucはラベル値なのに後段notesがDose/CLから計算した非独立targetと説明している。 対応: source記載とnotesを統一する。
- P2: ファイル名spec_pk1_oralとtemplate名はgeneric外血管モデルで、現regimenはsublingual。吸収KA/ALAGはDSUVIA検証済み値ではない。 対応: 舌下というrouteを出力でも維持し、吸収fixture仮定を明記。

### tefibazumab — hold

数値は原著のESRD血液透析患者8名10/20 mg/kg IV要約と一致。adult_healthy 100 mg単回シナリオへの一般化を採用保留。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | QUALIFIED | source_1 Abstractの平均12 mL/h→.012 L/hは一致。実際はESRD透析2群各4名で、Table1の群別12.65/11.80 mL/hの概数要約。健常者値ではない。 | ESRD/hemodialysis/10–20 mg/kg/30分IV条件を保持する。 |
| volume | QUALIFIED | Abstractの平均7.3 Lは一致。Table1の7.43/7.11 Lを概括した数値。本文はNCAでVと表記し、Vssと断定する記載は確認できない。 | 容積種別の定義を原解析手順で確認する。Vss/Vcとは記載しない。 |
| half_life | FIXTURE_ASSUMPTION | Abstract17–18日の中点17.5×24=420 h。Table1は439.35 h/416.69 hであり420 h自体は研究の観測群平均ではない。 | range midpointを平均値やSD付き実測targetにしない。 |
| bioavailability | FIXTURE_ASSUMPTION | F=1はIV経路定義。非IVバイオアベイラビリティを測定した結果ではない。 | IV route definitionとして記録。 |

参照資料:
- [retrieved](https://pmc.ncbi.nlm.nih.gov/articles/PMC1610062/) — curlでPMC本文119044 bytes取得。Methods/Abstract/Table 1を確認。
- P1: 原著はESRD血液透析患者なのにtargetsはadult_healthy。healthyの別研究との類似性の論述は同一条件の証明ではない。 対応: 対象集団を正しくラベル付けし、健常者モデルなら別の原著から完全なパラメータ組を採用する。
- P2: 100 mg固定量は原著10/20 mg/kg、30分点滴に一致せず、抗体一般の典型値と扱えない。 対応: 開発品名、研究集団、投与量・点滴時間を明示する。

### tizanidine — qualified_fixture

ラベルのVss/F/半減期は確認。CL46.5795 L/hはIV Vssと経口半減期を混ぜたfixture導出であり臨床CLとして未検証。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | DERIVED | 2.4 L/kg×70 kg×ln2/2.5 h=46.57949 L/hは算術一致。IV Vssと経口終末半減期からsystemic CLを特定する科学的根拠はなく、ラベルの直接報告値ではない。 | 臨床CLに採用せず、同一条件の原著CLを取得する。 |
| volume | QUALIFIED | 健常成人IV Vss平均2.4 L/kg（CV21%）を確認。70 kg基準168 Lは計算一致、V/Fではない。 | Vssとterminal volumeの相違を維持する。 |
| half_life | VERIFIED_VALUE_ONLY | Metabolism and Excretionの約2.5 h（CV33%）に一致。別の空腹時8 mg製剤比較では約2 hも記載され、製剤/食事条件を固定する必要。 | targets SD1 hは原著推定としない。半減期をCL導出に使った事実を表示する。 |
| bioavailability | QUALIFIED | absolute oral F約40%（CV24%）は一致。ただし錠剤/カプセルは空腹時のみ生物学的同等、食事や内容物散布で吸収が異なる。 | 製剤/食事状態を必須にする。100 mgは記載された線形性検証1–20 mgの外である。 |

参照資料:
- [retrieved](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=043d9e51-bfa2-4add-9058-5ece332f7e99) — DailyMed全ラベル取得、updated2025-05-05/revised12-2020。
- P2: CLと半減期の一致はVssと半減期からCLを作ったためで、モデル妥当性の独立根拠ではない。 対応: CLをfixture_derivedに限定し臨床推定から隔離する。
- P2: 100 mgはラベルのPK線形性検証1–20 mgの範囲外。 対応: 用量妥当性を未確認と明示し臨床用途から除外する。

### triazolam — qualified_fixture

CL/F31.56 L/hの原著値とF44%の別一次抄録を確認。ただしVは別出典半減期中点との合成で、100 mgへの臨床外挿は支持されない。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | QUALIFIED | source_3同一論文PMID3567010は54名の健常若年男性、0.5 mg経口、oral CL526±38 mL/min（平均±SEM）。×60/1000=31.56 L/hは正しいCL/F。 | SEMとSDを区別する。70 kg補正ではなく平均体重77 kgの研究の絶対CL/F値。 |
| volume | DERIVED | 159.3601 L=31.56×3.5/ln2。ラベル半減期中点と別研究CL/Fを合わせた一室V/Fで、原著の観測容積ではない。 | 異なる研究の導出値と明示し、t_halfの独立検証性を主張しない。 |
| half_life | FIXTURE_ASSUMPTION | ラベル1.5–5.5 h中点3.5 hは算術一致。CLの原著は平均2.6 hであり、3.5 hは同一集団の観測平均ではない。 | 中点のsummaryをarithmetic_mean実測値としない。 |
| bioavailability | QUALIFIED | 保存.44は既存value_provenanceに項目欠落。追加一次PMID7593708抄録で12男性、0.25 mg市販経口錠/IV比較の実測平均F44%を確認。CL研究0.5 mgとは別の研究。 | source_id/条件を追加して根拠を明示。F1=1のCL/Fモデル規約と区別する。 |

参照資料:
- [retrieved](https://pubmed.ncbi.nlm.nih.gov/3567010/) — PubMed抄録およびDailyMed本文をWeb取得。PMC source_3の通常Web openはchallenge。
- [retrieved](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=ce6ddb53-89ca-4edf-a519-553d34ce7938) — PubMed抄録およびDailyMed本文をWeb取得。PMC source_3の通常Web openはchallenge。
- [retrieved](https://pubmed.ncbi.nlm.nih.gov/7593708/) — NCBI公式efetch XMLで追加原著抄録を取得。
- P2: F44%のsource mappingがなく、systemic値は別研究Fを掛けて作っている。 対応: Fの新規一次出典をレビューし、交差研究によるsystemic換算を限定する。
- P2: 100 mg fixtureはCL研究0.5 mgの200倍。原著による裏付けはない。 対応: 合成用テスト条件とし、用量の臨床適合は別途是正する。

### verapamil — qualified_fixture

6名のIV/経口原著でCL、Vd(area)、Fを確認。半減期5.1 hは別ラベル範囲中点で、二室研究の終末相4.21 hとは異なる。

| 項目 | 判定 | 根拠・制約 | 必要な対応 |
|---|---|---|---|
| clearance | QUALIFIED | source_3の10 mg IV、6健常者平均body CL500.64 mL/min×60/1000=30.0384 L/hは一致。二室モデルのsystemic CL。 | 非対称体別反復投与CLと混合しない。 |
| volume | QUALIFIED | IV Vd(area)2.51 L/kg×70 kg=175.7 Lは一致。原著のapparent volumeはarea法の容積でありoral V/Fの意味ではない。 | Vd(area)/Vzとして型を保持し、Vss/Vcと混同しない。 |
| half_life | FIXTURE_ASSUMPTION | ラベルの単回研究平均半減期2.8–7.4 hから中点5.1 hを選択。source_3のIV終末相平均は4.21 hであり異なる出典・要約。 | 5.1を実測平均ではなくfixture midpointと記録する。 |
| bioavailability | QUALIFIED | 6名で120 mg経口/10 mg IV比較、平均22.47%=.2247は一致。単回条件であり反復、徐放製剤へ外挿できない。 | 原著全文で経口製剤を確認する。抄録だけではimmediate_releaseと断定しない。 |

参照資料:
- [retrieved](https://pubmed.ncbi.nlm.nih.gov/432439/) — PubMed通常HTMLはchallenge。NCBI公式efetch XMLでAbstractを取得。
- [retrieved](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c9d71191-b32a-44f9-bc5a-283a06884c82) — DailyMed全ラベルをWeb取得。
- P2: F provenanceのimmediate_release_oralは取得した抄録に製剤明記がなく未確認。spec.meta.sourcesから原著source_3も欠落。 対応: 製剤根拠を全文で確定しmeta出典に採用原著を反映する。

## 取得方法と制限

DailyMed/FDAはラベル本文、PMCはcurlによる公開HTML本文、PubMedで通常ページのchallengeが生じたものはNCBI公式efetch XMLから同じPMIDの抄録を取得した。検索結果だけの数値は確定根拠にしていない。moclobemide、montelukast、verapamil、omeprazoleの採用原著およびtriazolamの追加F原著はabstract-only。製剤・推定法など抄録にない情報は未確認。

全薬共通の架空IIV/残差/SD、未検証のKA/ALAG、用量や採血期間の臨床適合は統合報告で別途扱う。算術整合はモデルの臨床妥当性を意味しない。
