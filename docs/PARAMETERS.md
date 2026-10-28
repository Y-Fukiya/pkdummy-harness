---
layout: page
title: 薬剤別シミュレーションパラメータ
permalink: /parameter-values/
---

# 薬剤別シミュレーションパラメータ

このコミットの正本YAMLから生成した採用値です。CLはL/h、VはL、KAは1/h、F1は無次元、ALAG1はhです。
数値の整合性は臨床モデルの妥当性を意味しません。全37剤とも臨床モデルとしては未承認です。

[検索・詳細画面](https://y-fukiya.github.io/pkdummy-harness/parameters/) / [原典修正と残る制約](https://y-fukiya.github.io/pkdummy-harness/parameter-corrections/)

全剤の投与設定は計算用ストレス試験で、臨床常用量として未確認です。集団名は投与量の妥当性を保証しません。

| 薬剤 | 経路 | CL | V | KA | F1 | ALAG1 | CL basis / V basis | 臨床評価 | 半減期比・候補 | 実行用量・計算用 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| abciximab | iv_bolus | 10.98 | 100.8 | — | — | — | systemic / systemic | clinical_hold | 15.272 保留候補 | A: 100 mg・常用量未確認 |
| aciclovir | oral | 19.62 | 46.666666666666664 | 1.2 | 0.1 | 0.5 | systemic / systemic | not_assessed | 0.659 保留候補 | A: 100 mg・常用量未確認 |
| albuterol | iv | 28.8 | 160.38152230554428 | — | — | — | systemic / systemic | not_assessed | 1.000 臨床妥当性未判定 | A: 1.0 mg・常用量未確認 |
| alfentanil | iv_bolus | 21.0 | 70.0 | — | — | — | systemic / systemic | not_assessed | 1.379 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| alprazolam | oral | 6.3 | 91.0 | 1.2 | 1.0 | 0.5 | apparent / apparent | not_assessed | 0.801 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| amikacin | iv_bolus | 6.0 | 24.0 | — | — | — | systemic / systemic | not_assessed | 1.386 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| apixaban | oral | 3.3 | 21.0 | 1.2 | 0.5 | 0.5 | systemic / systemic | clinical_hold | 0.368 保留候補 | A: 10.0 mg・常用量未確認 |
| atazanavir | oral | 12.9 | 88.3 | 1.2 | 1.0 | 0.5 | apparent / apparent | not_assessed | 1.031 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| buprenorphine | iv | 54.0 | 806.0 | — | — | — | systemic / systemic | not_assessed | 1.000 臨床妥当性未判定 | A: 0.3 mg・常用量未確認 |
| carbamazepine | oral | 4.8 | 100.41157484587185 | 1.2 | 1.0 | 0.5 | apparent / apparent | not_assessed | 1.000 臨床妥当性未判定 | A: 200.0 mg・常用量未確認 |
| cda1 | iv_bolus | 0.00588 | 4.9 | — | — | — | systemic / systemic | not_assessed | 0.843 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| cimetidine | oral | 29.7 | 56.0 | 1.2 | 0.6 | 0.5 | systemic / systemic | not_assessed | 0.653 保留候補 | A: 100 mg・常用量未確認 |
| clarithromycin | oral | 58.1 | 172.0 | 1.2 | 1.0 | 0.5 | apparent / apparent | not_assessed | 0.410 保留候補 | A: 100 mg・常用量未確認 |
| dapagliflozin | oral | 12.42 | 118.0 | 1.2 | 0.78 | 0.5 | systemic / systemic | not_assessed | 0.511 保留候補 | A: 10.0 mg・常用量未確認 |
| efavirenz | oral | 13.9 | 1163.1007419646824 | 1.2 | 1.0 | 0.5 | apparent / apparent | not_assessed | 1.000 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| erythromycin | iv | 37.1 | 123.10516783905524 | — | — | — | systemic / systemic | not_assessed | 1.000 臨床妥当性未判定 | A: 125.0 mg・常用量未確認 |
| ethinylestradiol | oral | 25.7 | 632.1673264919305 | 1.2 | 1.0 | 0.5 | apparent / apparent | not_assessed | 1.000 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| felodipine | oral | 90.0 | 700.0 | 1.2 | 0.15 | 0.5 | systemic / systemic | clinical_hold | 0.220 保留候補 | A: 100 mg・常用量未確認 |
| fluconazole | iv | 0.966 | 41.80930228496216 | — | — | — | systemic / systemic | not_assessed | 1.000 臨床妥当性未判定 | A: 200.0 mg・常用量未確認 |
| fluvoxamine | oral | 65.56797653945428 | 1750.0 | 1.2 | 1.0 | 0.5 | apparent / apparent | not_assessed | 1.000 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| inulin | iv_bolus | 5.61 | 13.0 | — | — | — | systemic / systemic | not_assessed | 1.000 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| itraconazole | oral | 16.68 | 700.0 | 1.2 | 0.55 | 0.5 | systemic / systemic | not_assessed | 1.322 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| mefenamic_acid | oral | 21.13 | 74.2 | 1.2 | 1.0 | 0.5 | apparent / apparent | not_assessed | 0.811 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| metoprolol | oral | 48.0 | 346.2468098133512 | 1.2 | 0.5 | 0.5 | systemic / systemic | not_assessed | 1.000 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| mexiletine | oral | 30.87655622494302 | 490.0 | 1.2 | 1.0 | 0.5 | apparent / apparent | not_assessed | 1.000 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| moclobemide | oral | 39.4 | 84.3 | 1.2 | 0.56 | 0.5 | systemic / systemic | not_assessed | 0.927 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| montelukast | oral | 1.8479999999999999 | 9.7 | 1.2 | 0.61 | 0.5 | systemic / systemic | clinical_hold | 0.543 保留候補 | A: 100 mg・常用量未確認 |
| motavizumab_medi_524 | iv | 0.010229166666666666 | 7.35 | — | — | — | systemic / systemic | not_assessed | 0.783 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| motavizumab_yte | iv | 0.0022916666666666667 | 6.744599316155904 | — | — | — | systemic / systemic | not_assessed | 1.000 臨床妥当性未判定 | A: 100.0 mg・常用量未確認 |
| omeprazole | oral | 37.44 | 16.1 | 1.2 | 0.35 | 0.5 | systemic / systemic | clinical_hold | 0.397 保留候補 | A: 100 mg・常用量未確認 |
| raltegravir | oral | 60.2 | 677.4318833998217 | 1.2 | 1.0 | 0.5 | apparent / apparent | not_assessed | 1.000 臨床妥当性未判定 | A: 400.0 mg・常用量未確認 |
| sildenafil | oral | 41.0 | 105.0 | 1.2 | 0.41 | 0.5 | systemic / systemic | clinical_hold | 0.444 保留候補 | A: 100 mg・常用量未確認 |
| sufentanil | sublingual | 108.0 | 2087.868263174508 | 1.2 | 1.0 | 0.5 | apparent / apparent | not_assessed | 1.000 臨床妥当性未判定 | A: 0.03 mg・常用量未確認 |
| tefibazumab | iv | 0.012 | 7.3 | — | — | — | systemic / systemic | not_assessed | 1.004 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| tizanidine | oral | 46.579490533628324 | 168.0 | 1.2 | 0.4 | 0.5 | systemic / systemic | not_assessed | 1.000 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| triazolam | oral | 31.560000000000002 | 159.36009421659492 | 1.2 | 1.0 | 0.5 | apparent / apparent | clinical_hold | 1.000 臨床妥当性未判定 | A: 100 mg・常用量未確認 |
| verapamil | oral | 30.0384 | 175.7 | 1.2 | 0.2247 | 0.5 | systemic / systemic | not_assessed | 0.795 臨床妥当性未判定 | A: 100 mg・常用量未確認 |

## 出典・変換・確認状態

- [評価・投与設定・値の選択方針](https://y-fukiya.github.io/pkdummy-harness/fixture-governance/)
- [全37剤の評価・投与設定CSV](https://y-fukiya.github.io/pkdummy-harness/parameters/FIXTURE_GOVERNANCE.csv)
- [全パラメータの選択ルールCSV](https://y-fukiya.github.io/pkdummy-harness/parameters/PARAMETER_SELECTIONS.csv)
- [全パラメータCSV](https://y-fukiya.github.io/pkdummy-harness/parameters/PARAMETER_PROVENANCE.csv)
- [出典CSV](https://y-fukiya.github.io/pkdummy-harness/parameters/SOURCES.csv)
- [値の由来一覧](https://y-fukiya.github.io/pkdummy-harness/parameters/PARAMETER_PROVENANCE.html)

F1=1は、apparent CL/F・V/Fを用いたモデルでは実際の利用率100%を主張しません。
原典照合、導出、fixture仮定、未確認事項を区別して確認してください。
