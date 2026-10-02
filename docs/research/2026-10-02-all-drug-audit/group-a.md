# 全薬剤監査 Group A

監査日: 2026-10-02。対象13薬剤、CL・V・半減期・Fの52項目。原データ変更なし。`hold`は臨床パラメータセットとして採用保留であり、転記された個々の数値をすべて誤りとする判定ではない。

## 重要所見

- apixaban: total CL 3.3 L/hをCL/Fと解釈する根拠はなく、一次IV研究と不整合。systemic派生CL1.65 L/hと経口AUCを優先再審査。
- carbamazepine: 反復ER投与CL/半減期を200 mg単回fixtureへ流用。自己誘導・吸収条件を落としている。
- CDA1: CLとVを別用量群から合成。数式警告が出なくても同一パラメータセットとはいえない。
- buprenorphine: 原著V806.4 Lに対して保存806 L。原著終末半減期25 hとfixture逆算10.35 hを区別する必要。原著表のV単位表記にも確認事項あり。
- abciximab: Vssの一次学会抄録は403で再検証できず。短いfree plasma相を終末相と同定できない。
- 全薬剤で、fixtureの投与・吸収・変動・残差・独立性は数値の存在確認と別判定。専門家レビュー完了、臨床承認、投薬推奨ではない。

## abciximab — hold

CLの転記・換算は確認。Vssの一次学会抄録を再取得できず、短い血漿相をterminal targetに用いる点と異研究CL/Vの組合せは採用保留。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | VERIFIED_VALUE_ONLY | 一次研究抄録の健康成人30例の定常状態CL 183±72 mL/min（平均±SD）と一致。183×60/1000=10.98 L/h。血管形成患者32例の単回CL 405±240とは区別が必要。 |
| volume | UNVERIFIED | 保存1.44 L/kg×70=100.8 Lは算術上正しい。source_6は403で一次学会抄録を再読できず、Vssの数値・対象・測定法を今回確認済みにはできない。二次検索転載は採用しない。 |
| half_life | CONTRADICTION | 総説抄録の血漿20–30分は確認できるが、25分という中点は観測平均ではない。FDA原文はfree plasmaの初期<10分・第2相約30分と、その後の遅い減衰を区別するため、targets.phase=terminal/summary=arithmetic_meanは支持されない。 |
| bioavailability | FIXTURE_ASSUMPTION | IVのF=1は全投与量を全身入力とする経路定義。実測経口バイオアベイラビリティではない。 |

必要な対応:
- P1: 健康成人定常状態CLと出典未再取得Vssの合成。CL/Vからの1-comp半減期は約6.36hで短い血漿相とは異なる。 数値を調整して一致させず、同研究・同対象・同相を選び直す。
- P1: 100mg IV bolus fixtureはFDAの0.25mg/kg bolus＋infusionという収集資料の条件に対応しない。 デモ投与と臨床条件の適用範囲を明示し、臨床モデルへ採用しない。

取得した根拠・取得失敗:
- [1](https://pubmed.ncbi.nlm.nih.gov/11907493/) — failed; web openはcaptcha。下記Europe PMC公式抄録APIで補完。
- [2](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:11907493&format=json&resultType=core) — retrieved; 原著抄録JSONをcurlで取得。
- [3](https://ascpt.onlinelibrary.wiley.com/doi/abs/10.1016/j.clpt.2003.11.342) — failed; web/curlとも403。
- [4](https://pubmed.ncbi.nlm.nih.gov/14618072/) — retrieved; 総説抄録。原著研究ではない。
- [5](https://www.accessdata.fda.gov/drugsatfda_docs/label/2013/103575s5126lbl.pdf) — retrieved; 2013 FDA label全文。最新製品承認状況の確認ではない。

## aciclovir — hold

CL/Fの二重補正はないが、BSA基準CL、別総説Vss、経口F下限の混成。数値出典の存在と単回100mgモデル妥当性は別。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | QUALIFIED | 注射label Table2のCrCl>80mL/min/1.73m²でCL327mL/min/1.73m²を確認。19.62L/h/1.73m²への単位換算は正しいが、70kgの個人CLに換算した値ではない。 |
| volume | QUALIFIED | 総説抄録はVssが体重のおよそ2/3と記載し、2-comp動態も明記。46.666…Lは近似2/3L/kg×70kgであり、測定精度や1-comp Vzを意味しない。原著試験は未特定。 |
| half_life | FIXTURE_ASSUMPTION | 経口labelは2.5–3.3hの範囲。2.5hはその下限で観測算術平均ではない。注射Table2の正常腎機能2.5hとも数値は一致するが、出典条件を置換しない。 |
| bioavailability | FIXTURE_ASSUMPTION | 経口labelの平均経口F範囲10–20%、用量増加とともに低下を確認。保存F=.1は範囲下限の選択で単回100mgの実測値ではない。 |

必要な対応:
- P1: CLは1.73m²基準、Vは70kg基準、Fは経口範囲下限で同一成人の推定セットではない。 同研究・同集団に揃え、BSAと体重の扱いを明示。
- P2: Vssを1-comp Vにしたため半減期は約1.65h。半減期2.5hとの差だけで原文数値を誤りとは判定できない。 構造上の限界を保ち、2-comp原著を選定する。

取得した根拠・取得失敗:
- [1](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=e8a0f9f8-294f-4dd6-bd55-10a6253f1aa8) — retrieved; 経口錠label全文、2026-04-29更新。
- [2](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=69a98000-adef-4323-89a7-09e035a257d4) — retrieved; 注射label全文。
- [3](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:7048912&format=json&resultType=core) — retrieved; 総説抄録API取得、一次原著ではない。
- [4](https://pubmed.ncbi.nlm.nih.gov/7048912/) — failed; web open本文空。公式APIで抄録を補完。

## albuterol — hold

健康成人IV研究のCLと半減期を再確認。Vは観測値ではなく逆算であり、半減期チェックの独立性を否定するメタデータ修正が必要。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | VERIFIED_VALUE_ONLY | 健康被験者10例IVでtotal plasma CL480±123mL/minを原著抄録で確認。×60/1000=28.8L/hは正しい。 |
| volume | DERIVED | 28.8×3.86/ln2=160.3815Lという1-comp逆算。直接報告Vではない。抄録のV表示には単位の文字連結があり、それを生の定量値として再解釈しない。 |
| half_life | VERIFIED_VALUE_ONLY | 原著抄録のIV半減期3.86±0.83hと保存3.86hは一致。保存targetsのSD1.0hは原著SDではない。Vの導出入力でもあり独立検証用ではない。 |
| bioavailability | FIXTURE_ASSUMPTION | IVのF=1は全投与量を全身入力とする経路定義。実測経口バイオアベイラビリティではない。 |

必要な対応:
- P1: Vを半減期で逆算しながらhalf-life targetを独立チェック風に扱いused_to_calibrate_cl_v=falseとする。 半減期整合は設計上の恒等式であることを明示。臨床妥当性の証拠にしない。

取得した根拠・取得失敗:
- [1](https://pubmed.ncbi.nlm.nih.gov/3790406/) — retrieved; 原著抄録取得。本文の投与手順は未検証。

## alfentanil — hold

注射labelのCL・V範囲・半減期範囲は再確認。3-comp由来の代表値を1-compへまとめ、V上限と半減期中点を組むため臨床採用は保留。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | VERIFIED_VALUE_ONLY | label平均血漿CL5mL/kg/minを確認。×70×60/1000=21L/h。成人/肝機能/併用麻酔薬等を条件として保持する必要。 |
| volume | FIXTURE_ASSUMPTION | labelのapparent V0.4–1L/kgはIVなのでV/Fを意味しない。保存70Lは上限1×70kgで、測定された平均VではなくVss/Vzの別もlabelだけでは確定できない。 |
| half_life | FIXTURE_ASSUMPTION | labelは3-compで分布相1分/14分、終末90–111分。1.675hは(90+111)/2/60の中点で観測平均でない。 |
| bioavailability | FIXTURE_ASSUMPTION | IVのF=1は全投与量を全身入力とする経路定義。実測経口バイオアベイラビリティではない。 |

必要な対応:
- P1: 100mg IV bolus/healthy adult fixtureはlabelで述べる麻酔下・μg/kg単位の条件と対応せず、1-compのCL/Vは半減期約2.31hを生む。 デモ条件を臨床値セットと扱わない。原著集団とregimenを揃える。

取得した根拠・取得失敗:
- [1](https://dailymed.nlm.nih.gov/dailymed/downloadpdffile.cfm?setId=c965d63f-933b-4a83-88f6-c8c74159530b) — retrieved; DailyMed PDF15ページ全文のClinical Pharmacology確認。

## alprazolam — hold

総説の範囲は再取得できたがCL/V上限と半減期中点は一組の被験者推定値ではない。一次1mg試験と100mg fixtureは対応しない。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | QUALIFIED | 総説抄録は1mg経口後CL0.7–1.5mL/min/kg。上限×70×60/1000=6.3L/hは算術上正しいが、CL/Fの定義と上限の研究集団は抄録だけで未確定。別の一次IV/経口試験は経口0.89を報告。 |
| volume | QUALIFIED | 総説の0.8–1.3L/kgの上限1.3×70=91L。抄録のみでV/F、Vss/Vzを確認できない。一次1mg crossoverでは経口0.84L/kgであり、異試験の上限を一律成人に置けない。 |
| half_life | FIXTURE_ASSUMPTION | 総説9–16hから12.5hを中点化。一次crossoverの経口11.8hという実測平均とは異なり、保存値を観測平均と扱わない。 |
| bioavailability | FIXTURE_ASSUMPTION | 総説の80–100%から0.9を選んだもの。一次1mg crossoverは平均0.92、ER labelは約0.9を記載するが、ERと現specの製剤未指定・KA1.2の同一性はない。 |

必要な対応:
- P1: 100mg経口fixtureは今回根拠の1mg試験およびER labelのPK直線性確認範囲≤10mgから外れる。 単回製剤・用量・母集団をソースと一致させるまで臨床モデル採用保留。

取得した根拠・取得失敗:
- [1](https://pubmed.ncbi.nlm.nih.gov/8513649/) — failed; web open空。Europe PMC抄録APIで補完。
- [2](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:8513649&format=json&resultType=core) — retrieved; 前者は総説、後者は1mg IV/経口6男性の原著抄録。
- [3](https://pubmed.ncbi.nlm.nih.gov/6152055/) — failed; web open空。Europe PMC抄録APIで補完。
- [4](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:6152055&format=json&resultType=core) — retrieved; 前者は総説、後者は1mg IV/経口6男性の原著抄録。
- [5](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=29477df1-68aa-44b3-bf9e-80ecff6ce879) — retrieved; ER label全文確認。別製剤の比較根拠。

## amikacin — hold

CL約100mL/min・V24Lはlabelどおり。半減期の「2時間をやや超える」を厳密な2.0hへ変えた点、IV bolus条件は修正審査が必要。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | VERIFIED_VALUE_ONLY | 正常腎機能成人の平均血清CL約100mL/minと一致。×60/1000=6L/h。約値であり腎CL94mL/minとは区別。 |
| volume | VERIFIED_VALUE_ONLY | 正常成人のmean total apparent V24Lは一致。IV文脈のapparentはV/Fではない。併記28%体重を70kgへ換算した値ではなく、24Lは原文絶対値。Vss/Vzの定義は未確定。 |
| half_life | CONTRADICTION | 原文は2時間をやや超えると記述する。保存2.0hおよび範囲[2,2]は厳密な原文転記ではなく、定性的な近似を確定値へ変えている。 |
| bioavailability | FIXTURE_ASSUMPTION | IVのF=1は全投与量を全身入力とする経路定義。実測経口バイオアベイラビリティではない。 |

必要な対応:
- P1: labelは成人IVを30–60分で投与する条件を記載するがspecはiv_bolus。血中初期濃度は同じ条件ではない。 投与時間・採血計画と根拠を揃え、bolus fixtureでCmaxの臨床妥当性を主張しない。
- P2: CL/Vの半減期約2.77hは「少し2h超」の原文と比較すべきで、2.0hとの機械閾値だけでは転記誤りと決められない。 原文の精度・V定義を残して構造差を評価。

取得した根拠・取得失敗:
- [1](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=0b56f6df-a05d-4520-8bf0-d7cefe20f6ad) — retrieved; DailyMed注射label全文。

## apixaban — hold

total CLをCL/Fと解釈したbasisが一次IV研究と不整合。現10mg経口fixtureはFを二重に誤解し得るため優先修正審査。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | CONTRADICTION | label3.3L/hの数値は一致するがtotal CLをCL/Fへ読み替える根拠はない。一次IV研究はtotal plasma CL3.2–3.5L/hを報告。保存systemic=3.3×.5=1.65L/hはこのbasisと不整合。 |
| volume | DERIVED | 57.1307Lは3.3×12/ln2からの1-comp逆算でlabelの実測Vではない。labelはVss約21L、IV原著はVss17–26L。Vssと逆算Vz相当を混同しないが、保存V/FというbasisはCL誤分類を継承。 |
| half_life | VERIFIED_VALUE_ONLY | labelの経口後apparent半減期約12hと一致。Vの導出入力なのでhalf-life一致は独立した臨床検証ではない。 |
| bioavailability | QUALIFIED | label F約50%は≤10mg条件で確認。現spec10mgはその範囲内。ただしCL3.3をsystemicと見ると、F1=1/CL3.3によるAUCはF=.5/CL3.3の約2倍となる。IV原著F66.2%は別試験値で自動置換しない。 |

必要な対応:
- P1: pk_parsed.clearance_basis=apparentとderived.systemic=1.65L/hがtotal systemic CL資料と不整合。 CL/Fの誤分類を最優先で修正審査し、AUC3030.30ng*h/mLの妥当性も再評価。
- P1: Vをhalf-lifeから逆算するので半減期の検証が循環する。 文献独立AUC/濃度系列で検証する。

取得した根拠・取得失敗:
- [1](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=095a08ac-cf0e-497e-a682-ddef38d6b29c) — retrieved; DailyMed全文、2021-06-15更新。
- [2](https://pubmed.ncbi.nlm.nih.gov/34342172/) — failed; web open空。公式APIで補完。
- [3](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:34342172&format=json&resultType=core) — retrieved; 原著IV0.5–5mg/経口5mg抄録。

## atazanavir — hold

CL/FとV/Fの数値・定義は原著Table3と一致するが、HIV定常状態・RTV条件をhealthy単回100mgへ流用。吸収パラメータも原モデルと異なる。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | VERIFIED_VALUE_ONLY | 原著Table3 CL/F12.9L/hを確認。HIV患者214例・定常状態・RTV非併用を基準とし、RTVはCLを46%減らすモデル。無条件健康成人のCLではない。 |
| volume | VERIFIED_VALUE_ONLY | Table3 V/F88.3Lと一致。原著は1-comp oral population modelであり、絶対Vへの換算には未知Fが必要。 |
| half_life | QUALIFIED | 原著はRTVなし4.6h、あり8.8h。4.6hを保持したことは確認できるがunboosted条件を落とせない。CL/Vの丸められた点推定からは約4.74hとなり、転記矛盾とは限らない。 |
| bioavailability | UNVERIFIED | 絶対Fはnullで、これは未測定・未特定として妥当。原著F_sparse=.81とF_rich=1は相対F/服薬状況のモデルで絶対吸収率ではない。spec F1=1はCL/F表現上の規約。 |

必要な対応:
- P1: scenario adult_healthy/100mg単回はHIV患者定常状態300mg+RTVまたは400mg単独を含む原研究と不一致。 対象・regimen・boosting条件を固定して採用範囲を再設定。
- P1: 原著KA=.405/h・lag=.88hに対しspec KA1.2/h・lag.5h。CL/Vだけ転記しても原著モデルの濃度推移は再現しない。 absorptionと変動モデルの出典またはfixture仮定を明示。

取得した根拠・取得失敗:
- [1](https://pmc.ncbi.nlm.nih.gov/articles/PMC1635184/) — retrieved; web openはcaptcha、curlでNCBI PMC全文HTML取得しTable3確認。
- [2](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1635184/fullTextXML) — failed; API500。PMC HTMLで補完。

## buprenorphine — hold

CLは原著と一致。V806は原著806.4の丸めで、terminal半減期25hの代わりに10.35hを逆算したfixture。原著Table1のV単位も内部確認が必要。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | QUALIFIED | 原著5名の健康男性・非依存IV opioid使用者、2–16mg IV（1分）で全用量平均±SE54.0±1.7L/hを確認。現0.3mg/1h・healthy一般成人とは異なる。 |
| volume | CONTRADICTION | 本文/表は806.4±38.2L、保存raw_value806は丸めでexact source値でない。表はVz(predicted)/Fかつ単位欄L/hとあり、本文Lとの原著内部表記差もある。Vss/Vcとはみなせない。 |
| half_life | DERIVED | 10.3459h=ln2×806/54は計算上正しいが原著terminal平均±SE25.0±1.3hではない。保存provenanceは導出と記載する一方、targets.phase=terminal/summary=arithmetic_meanは実測との誤認を招く。 |
| bioavailability | FIXTURE_ASSUMPTION | IVのF=1は全投与量を全身入力とする経路定義。実測経口バイオアベイラビリティではない。 |

必要な対応:
- P1: 原著terminal25hとfixture10.35hの差は単なる転記修正で解決できず、原著V定義/表記差も残る。 原著確認を伴うモデル採用判断を行い、機械的half-life一致を臨床妥当性としない。
- P2: 原著2–16mg/1分、塩酸塩として用量表示、男性opioid使用者を現0.3mg/1hへ外挿。 低用量・使用歴・dose moietyに適合した資料を追加。

取得した根拠・取得失敗:
- [1](https://pmc.ncbi.nlm.nih.gov/articles/PMC3663890/) — retrieved; web openはcaptcha、curlでNCBI PMC全文HTML取得。
- [2](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC3663890/fullTextXML) — failed; API500。PMC HTMLで補完。

## carbamazepine — hold

元label URLは再取得失敗。別公式ER labelが反復投与CL80mL/minと12–17hを支持するが、現200mg単回への適用は未支持。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | QUALIFIED | 別公式ER labelは単回CL/F25±5、反復80±30mL/minを明示。保存4.8L/h=80×60/1000は反復値として正しいが、現single scenarioへは自動適用できない。 |
| volume | DERIVED | 4.8×14.5/ln2=100.4116Lは1-comp V/F逆算で観測Vでない。反復CLと半減期中点を入力としているため独立に検証されたVではない。 |
| half_life | FIXTURE_ASSUMPTION | 別ER labelは単回35–40h、反復12–17h。保存14.5hは後者の中点。単回初回200mgの観測平均としては支持されない。 |
| bioavailability | UNVERIFIED | pk_parsed F=1の絶対バイオアベイラビリティ根拠がない。モデルF1=1はCL/FとV/Fを使用するための正規化値で、完全吸収の証拠ではない。 |

必要な対応:
- P1: 反復ERパラメータをsingle200mg/KA1.2/lag.5に流用。単回と反復で自己誘導によるCL/half-life差をlabelが明示。 投与履歴・製剤・吸収をsourceと整合させる。
- P1: V逆算にhalf-lifeを使いながらused_to_calibrate_cl_v=false。 導出依存を記録し、独立検証としない。

取得した根拠・取得失敗:
- [1](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=52f0f753-a70c-4572-a85c-97ea7a2601a9) — failed; web toolで元URL inaccessible。
- [2](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c1876184-0323-4b06-b459-603b40c0c002) — retrieved; 別ANDAのER capsules label全文、2026版。元製品との同一性を主張しない。

## cda1 — hold

原著本文まで取得し数値所在を確認したが、CLとVは異なる用量群、半減期は幾何平均範囲の中点。単一集団のパラメータセットとして採用不可。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | VERIFIED_VALUE_ONLY | Table2の1mg/kg群median CL.0014mL/min/kgを確認（他群にも同値あり）。.0014×60/1000×70=.00588L/hは正しい。群中央値でpopulation arithmetic meanではない。 |
| volume | VERIFIED_VALUE_ONLY | Table2 Vd.070L/kgは0.3mg/kg群中央値、×70=4.9L。CL選択1mg/kg群のVdは.081L/kgであり、現CL/Vは同群ではない。 |
| half_life | FIXTURE_ASSUMPTION | 抄録の群別geometric mean25.3–31.8日を確認。保存685.2h=(25.3+31.8)/2×24は群間範囲の中点。Table2中央値550–728hとは要約統計が異なる。 |
| bioavailability | FIXTURE_ASSUMPTION | IVのF=1は全投与量を全身入力とする経路定義。実測経口バイオアベイラビリティではない。 |

必要な対応:
- P1: CL1mg/kg群とV.3mg/kg群を合成し、異なる幾何平均範囲中点をhalf-lifeにする。モデル警告が出ないことは同一性の根拠でない。 群・投与・統計を揃えた採用表を作る。
- P2: 原著はinfusion、fixtureは100mg bolus。現specの観測終点は3938.4hであり、72hではない。投与形態と初期濃度の条件は原著と異なる。 infusion時間と用量群をsourceに合わせ、モデル生成値と独立した実測値で検証する。

取得した根拠・取得失敗:
- [1](https://pmc.ncbi.nlm.nih.gov/articles/PMC2628753/) — retrieved; web openはcaptcha、curlでNCBI PMC全文HTMLとTable2確認。
- [2](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:18502001&format=json&resultType=core) — retrieved; 原著抄録API取得。
- [3](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC2628753/fullTextXML) — failed; API500。PMC HTMLで補完。

## cimetidine — hold

200mg IV/経口の潰瘍患者研究でCL495、Vss.8、F約.6を確認。healthy100mgへの適用とVssを1-comp Vへ置く妥当性は別途必要。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | VERIFIED_VALUE_ONLY | 胃潰瘍6名/十二指腸潰瘍6名、28–64歳の200mg IV/経口試験でplasma CL495mL/minを確認。×60/1000=29.7L/h。pk_raw500は旧丸め値で解析値と異なる。 |
| volume | QUALIFIED | 原著抄録はVssが体重約80%。.8L/kg×70=56Lの近似は追跡可能だが、terminal VzでもV/Fでもない。 |
| half_life | VERIFIED_VALUE_ONLY | 原著抄録と経口labelが約2hを支持。高齢ほど延長という原著条件があり、固定SD1hは文献値ではない。 |
| bioavailability | QUALIFIED | 原著200mg IV/経口の潰瘍患者12名でF約60%を確認。健康成人100mgの固定Fとしては未検証。systemic CL/VとF1=.6の代数的組合せは整合する。 |

必要な対応:
- P1: 潰瘍患者由来CL/V/Fをscenario adult_healthyへ流用。 populationと用量をsourceに結び付けるか健康成人の一次根拠を追加。
- P2: Vss/CLからは約1.31h、label約2hと違うがV定義・分布相の差と数値転記を分ける必要。 単純な半減期整合を理由にCL/Vを改変しない。

取得した根拠・取得失敗:
- [1](https://pubmed.ncbi.nlm.nih.gov/7363531/) — retrieved; 原著抄録取得。本文は未取得。
- [2](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=496e258d-a5fd-42da-9a86-73afc8be359b) — retrieved; 経口label全文のPharmacokinetics確認。

## clarithromycin — hold

CL範囲の総説と自己阻害モデルのV/Fを混成。58.1のCL/F分類は総説抄録から確定できず、用量依存半減期とFの中点化も未承認。

| 項目 | 判定 | 根拠と制限 |
|---|---|---|
| clearance | UNVERIFIED | 総説抄録にadult total body CL29.2–58.1L/hは存在するが、上限58.1をCL/Fとする一次研究・定義は未特定。V出典の原著Table1はapparent base CL60L/hで自己阻害により時間変化する。 |
| volume | QUALIFIED | 健康成人12例・絶食・懸濁液500mg q12h計7回の自己阻害モデルTable1でapparent V172L（95%CI145–198）を確認。これは同モデルの時間依存CLと組み合わせた推定で、別総説CL上限との互換性は示されていない。 |
| half_life | FIXTURE_ASSUMPTION | 即放錠labelは250mg q12hで3–4h、500mg q8–12hで5–7h。保存5hは異なる投与条件を合わせた3–7hの中点で、単回100mgの平均ではない。 |
| bioavailability | FIXTURE_ASSUMPTION | labelは250mg錠absolute F約.50、総説は52–55%。保存.525は混成範囲50–55%の中点で、特定試験の実測値・平均ではなくvalue_provenanceも未記載。 |

必要な対応:
- P1: apparent CL basis未確定と異研究CL/V合成によりderived systemic CL30.5025/V90.3も未検証。 一次CL定義とFの出典を確定するまでsystemic値を採用しない。
- P1: 原著の自己阻害による時間依存CLを定数化し、用量依存半減期を平均化している。 相互作用・反復条件を含む原モデルか、限定用途fixtureかを明示。

取得した根拠・取得失敗:
- [1](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=b1bdf526-4f16-4130-b614-4cb678f060d7) — retrieved; 即放錠label全文、2021版。
- [2](https://pubmed.ncbi.nlm.nih.gov/10589373/) — failed; web open空、公式APIで総説抄録補完。
- [3](https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:10589373&format=json&resultType=core) — retrieved; 総説抄録JSON。一次試験でない。
- [4](https://journals.asm.org/doi/10.1128/aac.01193-08) — retrieved; ASM原著全文・Table1取得。

## 読み方と限界

`VERIFIED_VALUE_ONLY`はソース中の値と単位換算だけの確認。`QUALIFIED`は出典が存在するが条件・定義・集団・近似の留保あり。`DERIVED`は計算値、`FIXTURE_ASSUMPTION`は代表値選択やモデル規約、`CONTRADICTION`は数値/定義/記録の不整合、`UNVERIFIED`は今回の資料で確定できない。

既存targetsのAUCはDose/CL等の内部整合チェックであり独立文献AUCではない。半減期からVを逆算した薬剤では、同じ半減期との一致を独立検証に用いない。全群に共通するIIV/残差/KA/lag等のfixture仮定は別途総合監査で扱う。
