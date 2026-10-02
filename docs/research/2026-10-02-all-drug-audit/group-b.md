# 全薬剤監査 Group B

確認日: 2026-10-02。12薬剤48項目を監査。既存checkedを根拠にせず、取得した公式資料または原著と照合。canonical PKファイルは変更していない。

`qualified_fixture` は制約を表示した工程検証用の状態を指す。臨床的妥当性、用量推奨、専門家署名の承認ではない。

## 優先所見

- inulin: 当該試験のVssは11.00 L/70 kg。保存13 LはDiscussionの過去文献一般論の誤帰属。
- ethinylestradiol: 配合錠EE0.02 mg由来値に100 mg単回scenarioを結合。半減期16.5–17.6 hの帰属も不一致。
- erythromycin: 原著は125 mg/30分静注、現specは1時間。
- mefenamic acid: FDA2024版はCL21.13、現在の引用先DailyMedは21.23。値を一律に誤りとせず出典版の差を保存。
- mexiletine: Vd5–9の引用がDailyMedではなくレビュー由来。V/Fというbasisも未確定。
- efavirenz: HIV反復投与PopPKのCL/Fを別の健常者単回fixtureへ移植。原著V/F237 Lと現1163.1 Lは別。

## 薬剤別

### dapagliflozin — qualified_fixture

静注CLとVssの数値はFDA審査資料で一致。経口終末半減期を再現する一組ではなく、Fの丸め説明が不足。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 12.42 L/h (systemic) | VERIFIED_VALUE_ONLY |
| volume | 118 L (systemic Vss) | QUALIFIED |
| half_life | 12.9 h | QUALIFIED |
| bioavailability | 0.78 | QUALIFIED |

根拠・取得状態:

- [retrieved] [https://www.accessdata.fda.gov/drugsatfda_docs/nda/2014/202293Orig1s000ClinPharmR.pdf](https://www.accessdata.fda.gov/drugsatfda_docs/nda/2014/202293Orig1s000ClinPharmR.pdf) — FDA審査資料128頁の本文とTable 1/24を取得。access_level full_labelは便宜上、実体は規制審査資料。

### efavirenz — hold

CL/Fの数値は原著で確認したが、HIV反復投与モデルのCLを健常者単回fixtureへ移植し、V/Fとkaも原著と異なる。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 13.9 L/h (CL/F) | QUALIFIED |
| volume | 1163.1007419646824 L (V/F) | DERIVED |
| half_life | 58 h (stored range 52–76 h) | FIXTURE_ASSUMPTION |
| bioavailability | null; spec F1=1 | FIXTURE_ASSUMPTION |

根拠・取得状態:

- [retrieved] [https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=13ca3456-e5bf-4bb1-af95-b1378658a358](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=13ca3456-e5bf-4bb1-af95-b1378658a358) — DailyMed現行ラベル本文取得。
- [retrieved] [https://pubmed.ncbi.nlm.nih.gov/40851704/](https://pubmed.ncbi.nlm.nih.gov/40851704/) — PubMed抄録取得。
- [retrieved] [https://pmc.ncbi.nlm.nih.gov/articles/PMC12370162/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12370162/) — webはCAPTCHA。curl HTTPSで原著HTML全文取得しMethods/Results/Discussionを照合。

### erythromycin — hold

健常群のCLと半減期は原著一致。Vは導出で、投与時間が原著30分と現spec1時間で違う。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 0.53 L/h/kg → 37.1 L/h at 70 kg | VERIFIED_VALUE_ONLY |
| volume | 1.7586452548436462 L/kg → 123.10516783905524 L | DERIVED |
| half_life | 2.3 h | VERIFIED_VALUE_ONLY |
| bioavailability | 1.0; IV | FIXTURE_ASSUMPTION |

根拠・取得状態:

- [retrieved] [https://pmc.ncbi.nlm.nih.gov/articles/PMC3581054/](https://pmc.ncbi.nlm.nih.gov/articles/PMC3581054/) — webはCAPTCHA、curl HTTPSで同一PMC本文全体を取得。Table 2とMethodsを確認。

### ethinylestradiol — hold

配合錠の周期内PKを単剤100 mgへ移植している。半減期範囲の出典帰属と絶対Fの一次根拠が不十分。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 25.7 L/h (CL/F) | QUALIFIED |
| volume | 632.1673264919305 L (V/F) | DERIVED |
| half_life | 17.05 h, stored 16.5–17.6 h range | CONTRADICTION |
| bioavailability | 0.43 (midpoint of 0.38–0.48) | FIXTURE_ASSUMPTION |

根拠・取得状態:

- [retrieved] [https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=142c4b90-c9ab-45ce-9172-f1ea7d366686](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=142c4b90-c9ab-45ce-9172-f1ea7d366686) — DailyMed配合錠kitラベル全文取得。
- [retrieved] [https://pmc.ncbi.nlm.nih.gov/articles/PMC4285808/](https://pmc.ncbi.nlm.nih.gov/articles/PMC4285808/) — PMC原著全文取得。ただし絶対F範囲の主張は当該研究で実測せず二次引用。

### felodipine — hold

レビューの血液CL上限とV/終末半減期を合成。公式ラベルでは血漿CL・製剤別半減期が異なり、100 mgへの外挿も未検証。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 90 L/h (1.5 L/min upper bound) | QUALIFIED |
| volume | 10 L/kg → 700 L at 70 kg | QUALIFIED |
| half_life | 24.5 h (24–25 midpoint) | FIXTURE_ASSUMPTION |
| bioavailability | 0.15 | QUALIFIED |

根拠・取得状態:

- [failed] [https://pubmed.ncbi.nlm.nih.gov/1782737/](https://pubmed.ncbi.nlm.nih.gov/1782737/) — PubMed本文はCAPTCHAで未取得。検索結果に抄録はあるが単独検証には使用しない。
- [retrieved] [https://pubmed.ncbi.nlm.nih.gov/3327676/](https://pubmed.ncbi.nlm.nih.gov/3327676/) — PubMedレビュー抄録を取得。原著ではない。
- [retrieved] [https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=2e4298cf-02e9-49c7-9803-887161e1989a](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=2e4298cf-02e9-49c7-9803-887161e1989a) — 公式ERラベル全文取得。
- [failed] [https://pubmed.ncbi.nlm.nih.gov/3593901/](https://pubmed.ncbi.nlm.nih.gov/3593901/) — 一次試験候補を同定したが本文/抄録ページ取得は失敗。

### fluconazole — qualified_fixture

元setidのラベルは取得不可。別の公式ラベルで数値を再確認したが、Vは導出、静注200 mgの同一試験組としては未検証。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 0.23 mL/min/kg → 0.966 L/h at 70 kg | QUALIFIED |
| volume | 41.80930228496216 L | DERIVED |
| half_life | 30 h | QUALIFIED |
| bioavailability | 1.0; IV | FIXTURE_ASSUMPTION |

根拠・取得状態:

- [failed] [https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=f6e44764-c652-4926-b081-9111c82c7957](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=f6e44764-c652-4926-b081-9111c82c7957) — web取得エラー。curl取得はDailyMedホーム画面で対象ラベル本文ではなかった。
- [retrieved] [https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=4d7cf836-d115-456c-a636-6f05eae043cd](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=4d7cf836-d115-456c-a636-6f05eae043cd) — 別製造販売者の公式錠剤ラベル全文取得。IV/PO PK要約を含む。

### fluvoxamine — hold

F53%とV約25 L/kgは確認。ただしV/Fという定義と9–28 hの単回代表値は未確認で、導出CLに影響する。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 65.56797653945428 L/h (claimed CL/F) | DERIVED |
| volume | 25 L/kg → 1750 L at 70 kg (claimed V/F) | QUALIFIED |
| half_life | 18.5 h (9–28 midpoint) | FIXTURE_ASSUMPTION |
| bioavailability | 0.53; spec F1=1 | VERIFIED_VALUE_ONLY |

根拠・取得状態:

- [retrieved] [https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=35b377d9-5b7a-4d8e-b6c1-4291d02f5dae](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=35b377d9-5b7a-4d8e-b6c1-4291d02f5dae) — DailyMed公式錠剤ラベル全文取得。その他の二次サイトは数値確定の根拠に使わない。

### inulin — hold

13 Lは当該試験Vssの実測値ではなくDiscussionの過去文献一般論。原著の健常者Vssは11.00 L/70kgで、出典帰属の誤りがある。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 5.61 L/h (93.5 mL/min at 70 kg) | QUALIFIED |
| volume | 13 L (claimed study Vss) | CONTRADICTION |
| half_life | 1.6062234130622617 h | DERIVED |
| bioavailability | 1.0; IV | FIXTURE_ASSUMPTION |

根拠・取得状態:

- [retrieved] [https://pmc.ncbi.nlm.nih.gov/articles/PMC1873801/](https://pmc.ncbi.nlm.nih.gov/articles/PMC1873801/) — webはCAPTCHA、curl HTTPSで同一原論文全文取得。Abstract/Methods/Discussionを直接照合。

### itraconazole — qualified_fixture

CLと経口Fの数値はラベル支持。V>700 Lを700 Lに置くこと、22 hの中点と1comp線形化はfixture仮定に限定。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 16.68 L/h systemic | VERIFIED_VALUE_ONLY |
| volume | 700 L from >700 L | FIXTURE_ASSUMPTION |
| half_life | 22 h from single-dose 16–28 h | FIXTURE_ASSUMPTION |
| bioavailability | 0.55 | QUALIFIED |

根拠・取得状態:

- [retrieved] [https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b1274d78-1096-4ae3-8299-a2e94eaa0ea5](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b1274d78-1096-4ae3-8299-a2e94eaa0ea5) — DailyMed100 mgカプセルラベル全文取得。

### mefenamic_acid — hold

21.13 L/hはFDA2024版で支持されるが、引用先DailyMedの現本文は21.23。値と出典版の対応修復が必要。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 21.13 L/h (oral CL/F) | CONTRADICTION |
| volume | 1.06 L/kg → 74.2 L at 70 kg | QUALIFIED |
| half_life | 3 h from 2–4 h | FIXTURE_ASSUMPTION |
| bioavailability | null; spec F1=1 | QUALIFIED |

根拠・取得状態:

- [retrieved] [https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d0291319-ab3e-20c8-e053-2a95a90afabb](https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d0291319-ab3e-20c8-e053-2a95a90afabb) — DailyMed本文取得、oral CL21.23を直接確認。
- [retrieved] [https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/015034s046lbl.pdf](https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/015034s046lbl.pdf) — FDA2024ラベルPDF全文取得、Table1の21.13を確認。

### metoprolol — hold

静注CL48 L/hは原著抄録で支持。Vの参照ラベル帰属とFのCmax比からの確定に問題が残る。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 48 L/h systemic | VERIFIED_VALUE_ONLY |
| volume | 346.2468098133512 L | DERIVED |
| half_life | 5 h from 3–7 h | FIXTURE_ASSUMPTION |
| bioavailability | 0.5; spec F1=0.5 | UNVERIFIED |

根拠・取得状態:

- [retrieved] [https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=cbc32a80-717b-4cf2-b76a-6d03a3720419](https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=cbc32a80-717b-4cf2-b76a-6d03a3720419) — DailyMed ERラベル本文取得。
- [failed] [https://pubmed.ncbi.nlm.nih.gov/6102500/](https://pubmed.ncbi.nlm.nih.gov/6102500/) — PubMedページの本文取得は失敗。
- [retrieved] [https://link.springer.com/article/10.2165/00003088-198005020-00004](https://link.springer.com/article/10.2165/00003088-198005020-00004) — 同一原著の出版社Summaryを取得。本文は購読が必要で未確認。

### mexiletine — hold

V範囲と引用source_idが混線。V/Fの定義は確認できず、systemic換算と派生CLも保留。

| 項目 | 保存値 | 判定 |
|---|---|---|
| clearance | 30.87655622494302 L/h (claimed CL/F) | DERIVED |
| volume | 7 L/kg → 490 L, claimed V/F | CONTRADICTION |
| half_life | 11 h from 10–12 h | FIXTURE_ASSUMPTION |
| bioavailability | 0.9; spec F1=1 | QUALIFIED |

根拠・取得状態:

- [retrieved] [https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=ab73778b-6794-441c-b127-610a6d0733ea](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=ab73778b-6794-441c-b127-610a6d0733ea) — DailyMedカプセルラベル全文取得。
- [retrieved] [https://pubmed.ncbi.nlm.nih.gov/10589372/](https://pubmed.ncbi.nlm.nih.gov/10589372/) — レビュー抄録取得、一次試験本文ではない。
- [retrieved] [https://www.medicines.org.uk/emc/product/13305/smpc](https://www.medicines.org.uk/emc/product/13305/smpc) — Clinigen100 mgカプセルSmPC全文取得、改訂2024-09-30。

## 共通の制約

- 70 kgへの単位換算が正しいことと、体重分布40–120 kgへ同じ関係を適用できることは別である。
- 範囲中点、上限/下限、複数研究の混成値を母集団平均・SDとして扱わない。
- 既定のKA1.2/h・ALAG0.5 h・IIV・残差・SD1 h等は4項目の原資料確認で検証された値ではない。
- AUC=Dose/CLまたはF×Dose/CLは同じ入力値による自己整合性検査であり、独立した実測AUC検証ではない。
- 多相性のある薬剤でln(2)Vss/CLを終末半減期と同一視しない。逆算で三者を合わせても臨床モデルの妥当性は証明しない。
- 各項目の詳細理由・locator・必要措置は[group-b.json](group-b.json)に記録。原資料が未取得の箇所を推測で補っていない。
