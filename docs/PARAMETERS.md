---
layout: page
title: 薬剤別シミュレーションパラメータ
permalink: /parameter-values/
---

# 薬剤別シミュレーションパラメータ

2026-10-02のローカル作業版 `drugs/*/spec_pk1_*.yml` から取り出した採用値です。未コミットの作業版を含むスナップショットで、GitHub mainの薬剤YAMLと一致することを保証するものではありません。値の丸め直しや推測補完は行っていません。

CLはL/h、VはL、KAは1/h、ALAG1はh、F1は無次元です。経口のCL・VにはCL/F・V/Fの見かけ値が含まれます。basis欄はpk.ymlの明示情報を表示し、specの扱いと合わせて確認してください。basisが空欄の場合は「未確認」とし、F1=1を利用率100%の証拠と解釈しないでください。KA・ラグ・IIV・残差はfixture仮定を含み、出典確認済みの値とは区別します。

## 採用パラメータ一覧

| 薬剤 | 経路 | CL | V | KA | F1 | ALAG1 | pk.ymlのCL basis / V basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| abciximab | iv_bolus | 10.98 | 100.8 | — | — | — | systemic / systemic |
| aciclovir | oral | 19.62 | 46.666666666666664 | 1.2 | 0.1 | 0.5 | systemic / systemic |
| albuterol | iv | 28.8 | 160.38152230554428 | — | — | — | systemic / systemic |
| alfentanil | iv_bolus | 21.0 | 70.0 | — | — | — | systemic / systemic |
| alprazolam | oral | 6.3 | 91.0 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| amikacin | iv_bolus | 6.0 | 24.0 | — | — | — | systemic / systemic |
| apixaban | oral | 3.3 | 57.130723619202946 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| atazanavir | oral | 12.9 | 88.3 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| buprenorphine | iv | 54.0 | 806.0 | — | — | — | systemic / systemic |
| carbamazepine | oral | 4.8 | 100.41157484587185 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| cda1 | iv_bolus | 0.00588 | 4.9 | — | — | — | systemic / systemic |
| cimetidine | oral | 29.7 | 56.0 | 1.2 | 0.6 | 0.5 | systemic / systemic |
| clarithromycin | oral | 58.1 | 172.0 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| dapagliflozin | oral | 12.42 | 118.0 | 1.2 | 0.78 | 0.5 | systemic / systemic |
| efavirenz | oral | 13.9 | 1163.1007419646824 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| erythromycin | iv | 37.1 | 123.10516783905524 | — | — | — | systemic / systemic |
| ethinylestradiol | oral | 25.7 | 632.1673264919305 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| felodipine | oral | 90.0 | 700.0 | 1.2 | 0.15 | 0.5 | systemic / systemic |
| fluconazole | iv | 0.966 | 41.80930228496216 | — | — | — | systemic / systemic |
| fluvoxamine | oral | 65.56797653945428 | 1750.0 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| inulin | iv_bolus | 5.61 | 13.0 | — | — | — | systemic / systemic |
| itraconazole | oral | 16.68 | 700.0 | 1.2 | 0.55 | 0.5 | systemic / systemic |
| mefenamic_acid | oral | 21.13 | 74.2 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| metoprolol | oral | 48.0 | 346.2468098133512 | 1.2 | 0.5 | 0.5 | systemic / systemic |
| mexiletine | oral | 30.87655622494302 | 490.0 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| moclobemide | oral | 39.4 | 84.3 | 1.2 | 0.56 | 0.5 | systemic / systemic |
| montelukast | oral | 1.8479999999999999 | 9.7 | 1.2 | 0.615 | 0.5 | systemic / systemic |
| motavizumab_medi_524 | iv | 0.010229166666666666 | 7.35 | — | — | — | systemic / systemic |
| motavizumab_yte | iv | 0.0022916666666666667 | 6.744599316155904 | — | — | — | systemic / systemic |
| omeprazole | oral | 43.56 | 16.1 | 1.2 | 0.35 | 0.5 | systemic / systemic |
| raltegravir | oral | 60.2 | 677.4318833998217 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| sildenafil | oral | 18.195113489698564 | 105.0 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| sufentanil | sublingual | 108.0 | 2087.868263174508 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| tefibazumab | iv | 0.012 | 7.3 | — | — | — | systemic / systemic |
| tizanidine | oral | 46.579490533628324 | 168.0 | 1.2 | 0.4 | 0.5 | systemic / systemic |
| triazolam | oral | 31.560000000000002 | 159.36009421659492 | 1.2 | 1.0 | 0.5 | apparent / apparent |
| verapamil | oral | 30.0384 | 175.7 | 1.2 | 0.2247 | 0.5 | systemic / systemic |

## 個体間変動・残差・出典の詳細

全パラメータの値、単位、basis、元値、変換式、出典URL、レビュー状態は次のファイルで確認できます。

- [パラメータ・由来一覧 CSV](parameters/PARAMETER_PROVENANCE.csv)
- [出典一覧 CSV](parameters/SOURCES.csv)
- [レビュー用の全項目一覧](parameters/PARAMETER_PROVENANCE.md)

`source_mapping_status=checked` は値単位のsource mappingが確認された行です。URLがあるだけの行、未確認の行、`fixture_policy` の行を同じ確度として扱わないでください。生成値はワークフロー試験用であり、臨床用量の選択に使うための検証済みモデルではありません。

入力キー・投与・採血条件の説明は[パラメータ仕様](SIMULATION_PARAMETERS.md)を参照してください。
