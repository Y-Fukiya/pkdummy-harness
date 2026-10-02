# PK fixture parameter provenance inventory

この一覧は `drugs/*/pk.yml`、`targets.yml`、`spec_pk1_*.yml` を読み取り、値の由来を確認するための監査用出力です。ソースURLが存在することだけでは、URL内のどの記載が特定の値に対応するかを証明しません。`reference_status` を必ず確認してください。

## 読み方

- `value_level_metadata`: `pk.yml.value_provenance` に解決済みsource_idがあり、source_review_status=checked。
- `value_level_metadata_needs_source_mapping`: value_provenanceはあるが、値単位のsource_idが未記録。
- `value_level_metadata_needs_source_review`: source_idはあるが、値単位のreviewが未完了。
- `source_mapping_status=checked`: その行のsource_idと値単位reviewが確認済み。これ以外は直接の科学的根拠として扱わない。
- `mapped_to_pk_derived`: specのCL/Vが `pk.yml.derived` と一致する。
- `derived_from_pk_yml_source_fields`: pk.yml内のparsed値から導出された値で、独立した直接報告値ではない。
- `source_url_present_not_parameter_mapped`: URLはあるが、特定パラメータとの直接対応は未記録。
- `fixture_policy_*`: デモ用specの仮定。外部文献値として扱わない。

CSVの全行は `PARAMETER_PROVENANCE.csv`、URLの全件は `SOURCES.csv` にあります。`raw_*`/`normalized_*`/`pk_raw_excerpt`/`conversion_*` と検証状態を併読してください。URL本文の直接引用や査読をこの一覧だけで代替しないでください。数値の変更はこの出力では行わず、canonicalなYAMLを更新してから再生成してください。

## 薬剤別サマリー

| Drug | Route | Spec | Source URLs | Parameter rows | Checked source-mapping rows | Status |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `abciximab` | iv | `spec_pk1_iv.yml` | 6 | 17 | 7 | source_urls_present |
| `aciclovir` | po | `spec_pk1_oral.yml` | 5 | 21 | 7 | source_urls_present |
| `albuterol` | iv | `spec_pk1_iv.yml` | 1 | 17 | 7 | source_urls_present |
| `alfentanil` | iv | `spec_pk1_iv.yml` | 1 | 17 | 7 | source_urls_present |
| `alprazolam` | po | `spec_pk1_oral.yml` | 1 | 21 | 7 | source_urls_present |
| `amikacin` | iv | `spec_pk1_iv.yml` | 1 | 17 | 7 | source_urls_present |
| `apixaban` | po | `spec_pk1_oral.yml` | 1 | 21 | 7 | source_urls_present |
| `atazanavir` | po | `spec_pk1_oral.yml` | 2 | 18 | 7 | source_urls_present |
| `buprenorphine` | iv | `spec_pk1_iv.yml` | 1 | 17 | 7 | source_urls_present |
| `carbamazepine` | po | `spec_pk1_oral.yml` | 1 | 21 | 7 | source_urls_present |
| `cda1` | iv | `spec_pk1_iv.yml` | 2 | 17 | 7 | source_urls_present |
| `cimetidine` | po | `spec_pk1_oral.yml` | 2 | 21 | 7 | source_urls_present |
| `clarithromycin` | po | `spec_pk1_oral.yml` | 3 | 21 | 7 | source_urls_present |
| `dapagliflozin` | po | `spec_pk1_oral.yml` | 1 | 21 | 7 | source_urls_present |
| `efavirenz` | po | `spec_pk1_oral.yml` | 2 | 18 | 7 | source_urls_present |
| `erythromycin` | iv | `spec_pk1_iv.yml` | 1 | 17 | 7 | source_urls_present |
| `ethinylestradiol` | po | `spec_pk1_oral.yml` | 2 | 21 | 7 | source_urls_present |
| `felodipine` | po | `spec_pk1_oral.yml` | 2 | 21 | 7 | source_urls_present |
| `fluconazole` | iv | `spec_pk1_iv.yml` | 1 | 17 | 7 | source_urls_present |
| `fluvoxamine` | po | `spec_pk1_oral.yml` | 8 | 21 | 7 | source_urls_present |
| `inulin` | iv | `spec_pk1_iv.yml` | 3 | 17 | 7 | source_urls_present |
| `itraconazole` | po | `spec_pk1_oral.yml` | 1 | 21 | 7 | source_urls_present |
| `mefenamic_acid` | po | `spec_pk1_oral.yml` | 2 | 18 | 7 | source_urls_present |
| `metoprolol` | po | `spec_pk1_oral.yml` | 2 | 21 | 7 | source_urls_present |
| `mexiletine` | po | `spec_pk1_oral.yml` | 2 | 21 | 7 | source_urls_present |
| `moclobemide` | po | `spec_pk1_oral.yml` | 5 | 21 | 7 | source_urls_present |
| `montelukast` | po | `spec_pk1_oral.yml` | 1 | 21 | 7 | source_urls_present |
| `motavizumab_medi_524` | iv | `spec_pk1_iv.yml` | 1 | 17 | 7 | source_urls_present |
| `motavizumab_yte` | iv | `spec_pk1_iv.yml` | 1 | 17 | 7 | source_urls_present |
| `omeprazole` | po | `spec_pk1_oral.yml` | 4 | 21 | 7 | source_urls_present |
| `raltegravir` | po | `spec_pk1_oral.yml` | 2 | 21 | 7 | source_urls_present |
| `sildenafil` | po | `spec_pk1_oral.yml` | 6 | 21 | 7 | source_urls_present |
| `sufentanil` | sl | `spec_pk1_oral.yml` | 1 | 21 | 7 | source_urls_present |
| `tefibazumab` | iv | `spec_pk1_iv.yml` | 1 | 17 | 7 | source_urls_present |
| `tizanidine` | po | `spec_pk1_oral.yml` | 1 | 21 | 7 | source_urls_present |
| `triazolam` | po | `spec_pk1_oral.yml` | 3 | 21 | 7 | source_urls_present |
| `verapamil` | po | `spec_pk1_oral.yml` | 3 | 21 | 7 | source_urls_present |

## 値単位の確認一覧

| Drug | Record | Parameter | Fixture value | Reference value | Basis | Source | Review status |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| `abciximab` | model_parameter | `model.theta.CL` | 10.98  | 10.98 L/h | derived_from_reported | source_2 | checked |
| `abciximab` | model_parameter | `model.theta.V` | 100.8  | 100.8 L | derived_from_reported | source_6 | checked |
| `abciximab` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 10.98 L/h | 10.98 L/h | derived_from_reported | source_2 | checked |
| `abciximab` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 10.98 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `abciximab` | pk_parameter | `V_abs_L_at_70kg` | 100.8 L | 100.8 L | derived_from_reported | source_6 | checked |
| `abciximab` | pk_parameter | `V_systemic_L_at_70kg` | 100.8 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `abciximab` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `abciximab` | pk_parameter | `clearance` | 10.98 L/h | 10.98 L/h | derived_from_reported | source_2 | checked |
| `abciximab` | pk_parameter | `ke_1_per_h` | 0.10892857142857143 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `abciximab` | pk_parameter | `t_half_h` | 0.4166666666666667 h | 0.4166666666666667 h | derived_from_reported | source_5 | checked |
| `abciximab` | pk_parameter | `volume` | 1.44 L/kg | 1.44 L/kg | derived_from_reported | source_6 | checked |
| `abciximab` | target | `targets.auc` | 9107.468123861567 ng*h/mL |   | dose_over_cl | - | derived_target |
| `abciximab` | target | `targets.t_half` | 0.4166666666666667 h |   | unknown_needs_review | - | target_without_source_mapping |
| `aciclovir` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `aciclovir` | model_parameter | `model.theta.CL` | 19.62  | 19.62 L/h | derived_from_reported | source_4 | checked |
| `aciclovir` | model_parameter | `model.theta.F1` | 0.1 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `aciclovir` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `aciclovir` | model_parameter | `model.theta.V` | 46.666666666666664  | 46.666666666666664 L | derived_from_reported | source_5 | checked |
| `aciclovir` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 19.62 L/h | 19.62 L/h | label_reported | source_4 | checked |
| `aciclovir` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 19.62 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `aciclovir` | pk_parameter | `V_abs_L_at_70kg` | 46.666666666666664 L | 46.666666666666664 L | literature_reported | source_5 | checked |
| `aciclovir` | pk_parameter | `V_systemic_L_at_70kg` | 46.666666666666664 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `aciclovir` | pk_parameter | `bioavailability` | 0.1 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `aciclovir` | pk_parameter | `clearance` | 19.62 L/h | 19.62 L/h | label_reported | source_4 | checked |
| `aciclovir` | pk_parameter | `ke_1_per_h` | 0.4204285714285715 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `aciclovir` | pk_parameter | `t_half_h` | 2.5 h | 2.5 h | derived_from_reported | source_1 | checked |
| `aciclovir` | pk_parameter | `volume` | 0.6666666666666666 L/kg | 0.6666666666666666 L/kg | literature_reported | source_5 | checked |
| `aciclovir` | target | `targets.auc` | 509.683995922528 ng*h/mL |   | f_dose_over_cl | - | target_without_source_mapping |
| `aciclovir` | target | `targets.t_half` | 2.5 h |   | unknown_needs_review | - | target_without_source_mapping |
| `albuterol` | model_parameter | `model.theta.CL` | 28.8  | 28.8 L/h | derived_from_reported | source_1 | checked |
| `albuterol` | model_parameter | `model.theta.V` | 160.38152230554428  | 160.38152230554428 L | derived_from_reported | source_1 | checked |
| `albuterol` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 28.8 L/h | 28.8 L/h | derived_from_reported | source_1 | checked |
| `albuterol` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 28.8 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `albuterol` | pk_parameter | `V_abs_L_at_70kg` | 160.38152230554428 L | 160.38152230554428 L | fixture_derived | source_1 | checked |
| `albuterol` | pk_parameter | `V_systemic_L_at_70kg` | 160.38152230554428 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `albuterol` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `albuterol` | pk_parameter | `clearance` | 28.8 L/h | 28.8 L/h | derived_from_reported | source_1 | checked |
| `albuterol` | pk_parameter | `ke_1_per_h` | 0.179571808435219 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `albuterol` | pk_parameter | `t_half_h` | 3.86 h | 3.86 h | literature_reported | source_1 | checked |
| `albuterol` | pk_parameter | `volume` | 160.38152230554428 L | 160.38152230554428 L | fixture_derived | source_1 | checked |
| `albuterol` | target | `targets.auc` | 34.72222222222222 ng*h/mL |   | dose_over_cl | - | derived_target |
| `albuterol` | target | `targets.t_half` | 3.86 h |   | unknown_needs_review | - | target_without_source_mapping |
| `alfentanil` | model_parameter | `model.theta.CL` | 21.0  | 21.0 L/h | derived_from_reported | source_1 | checked |
| `alfentanil` | model_parameter | `model.theta.V` | 70.0  | 70.0 L | derived_from_reported | source_1 | checked |
| `alfentanil` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 21.0 L/h | 21.0 L/h | derived_from_reported | source_1 | checked |
| `alfentanil` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 21.0 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `alfentanil` | pk_parameter | `V_abs_L_at_70kg` | 70.0 L | 70.0 L | derived_from_reported | source_1 | checked |
| `alfentanil` | pk_parameter | `V_systemic_L_at_70kg` | 70.0 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `alfentanil` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `alfentanil` | pk_parameter | `clearance` | 0.3 L/h/kg | 0.3 L/h/kg | derived_from_reported | source_1 | checked |
| `alfentanil` | pk_parameter | `ke_1_per_h` | 0.3 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `alfentanil` | pk_parameter | `t_half_h` | 1.675 h | 1.675 h | derived_from_reported | source_1 | checked |
| `alfentanil` | pk_parameter | `volume` | 1.0 L/kg | 1.0 L/kg | derived_from_reported | source_1 | checked |
| `alfentanil` | target | `targets.auc` | 4761.9047619047615 ng*h/mL |   | dose_over_cl | - | derived_target |
| `alfentanil` | target | `targets.t_half` | 1.675 h |   | unknown_needs_review | - | target_without_source_mapping |
| `alprazolam` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `alprazolam` | model_parameter | `model.theta.CL` | 6.3  | 6.3 L/h | derived_from_reported | source_1 | checked |
| `alprazolam` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `alprazolam` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `alprazolam` | model_parameter | `model.theta.V` | 91.0  | 91.0 L | derived_from_reported | source_1 | checked |
| `alprazolam` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 6.3 L/h | 6.3 L/h | derived_from_reported | source_1 | checked |
| `alprazolam` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 5.67 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `alprazolam` | pk_parameter | `V_abs_L_at_70kg` | 91.0 L | 91.0 L | derived_from_reported | source_1 | checked |
| `alprazolam` | pk_parameter | `V_systemic_L_at_70kg` | 81.9 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `alprazolam` | pk_parameter | `bioavailability` | 0.9 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `alprazolam` | pk_parameter | `clearance` | 0.09 L/h/kg | 0.09 L/h/kg | derived_from_reported | source_1 | checked |
| `alprazolam` | pk_parameter | `ke_1_per_h` | 0.06923076923076923 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `alprazolam` | pk_parameter | `t_half_h` | 12.5 h | 12.5 h | derived_from_reported | source_1 | checked |
| `alprazolam` | pk_parameter | `volume` | 1.3 L/kg | 1.3 L/kg | derived_from_reported | source_1 | checked |
| `alprazolam` | target | `targets.auc` | 15873.015873015873 ng*h/mL |   | dose_over_cl | - | derived_target |
| `alprazolam` | target | `targets.t_half` | 12.5 h |   | unknown_needs_review | - | target_without_source_mapping |
| `amikacin` | model_parameter | `model.theta.CL` | 6.0  | 6.0 L/h | derived_from_reported | source_1 | checked |
| `amikacin` | model_parameter | `model.theta.V` | 24.0  | 24.0 L | derived_from_reported | source_1 | checked |
| `amikacin` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 6.0 L/h | 6.0 L/h | label_reported | source_1 | checked |
| `amikacin` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 6.0 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `amikacin` | pk_parameter | `V_abs_L_at_70kg` | 24.0 L | 24.0 L | label_reported | source_1 | checked |
| `amikacin` | pk_parameter | `V_systemic_L_at_70kg` | 24.0 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `amikacin` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `amikacin` | pk_parameter | `clearance` | 6.0 L/h | 6.0 L/h | label_reported | source_1 | checked |
| `amikacin` | pk_parameter | `ke_1_per_h` | 0.25 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `amikacin` | pk_parameter | `t_half_h` | 2.0 h | 2.0 h | derived_from_reported | source_1 | checked |
| `amikacin` | pk_parameter | `volume` | 24.0 L | 24.0 L | label_reported | source_1 | checked |
| `amikacin` | target | `targets.auc` | 16666.666666666668 ng*h/mL |   | dose_over_cl | - | derived_target |
| `amikacin` | target | `targets.t_half` | 2.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `apixaban` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `apixaban` | model_parameter | `model.theta.CL` | 3.3  | 3.3 L/h | derived_from_reported | source_1 | checked |
| `apixaban` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `apixaban` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `apixaban` | model_parameter | `model.theta.V` | 57.130723619202946  | 57.130723619202946 L | derived_from_reported | source_1 | checked |
| `apixaban` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 3.3 L/h | 3.3 L/h | label_reported | source_1 | checked |
| `apixaban` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 1.65 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `apixaban` | pk_parameter | `V_abs_L_at_70kg` | 57.130723619202946 L | 57.130723619202946 L | fixture_derived | source_1 | checked |
| `apixaban` | pk_parameter | `V_systemic_L_at_70kg` | 28.565361809601473 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `apixaban` | pk_parameter | `bioavailability` | 0.5 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `apixaban` | pk_parameter | `clearance` | 3.3 L/h | 3.3 L/h | label_reported | source_1 | checked |
| `apixaban` | pk_parameter | `ke_1_per_h` | 0.05776226504666211 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `apixaban` | pk_parameter | `t_half_h` | 12.0 h | 12.0 h | label_reported | source_1 | checked |
| `apixaban` | pk_parameter | `volume` | 57.130723619202946 L | 57.130723619202946 L | fixture_derived | source_1 | checked |
| `apixaban` | target | `targets.auc` | 3030.3030303030305 ng*h/mL |   | dose_over_cl | - | derived_target |
| `apixaban` | target | `targets.t_half` | 12.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `atazanavir` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `atazanavir` | model_parameter | `model.theta.CL` | 12.9  | 12.9 L/h | derived_from_reported | source_2 | checked |
| `atazanavir` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `atazanavir` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `atazanavir` | model_parameter | `model.theta.V` | 88.3  | 88.3 L | derived_from_reported | source_2 | checked |
| `atazanavir` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 12.9 L/h | 12.9 L/h | literature_reported | source_2 | checked |
| `atazanavir` | pk_parameter | `V_abs_L_at_70kg` | 88.3 L | 88.3 L | literature_reported | source_2 | checked |
| `atazanavir` | pk_parameter | `clearance` | 12.9 L/h | 12.9 L/h | literature_reported | source_2 | checked |
| `atazanavir` | pk_parameter | `ke_1_per_h` | 0.14609286523216308 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `atazanavir` | pk_parameter | `t_half_h` | 4.6 h | 4.6 h | literature_reported | source_2 | checked |
| `atazanavir` | pk_parameter | `volume` | 88.3 L | 88.3 L | literature_reported | source_2 | checked |
| `atazanavir` | target | `targets.auc` | 7751.937984496124 ng*h/mL |   | dose_over_cl | - | derived_target |
| `atazanavir` | target | `targets.t_half` | 4.6 h |   | unknown_needs_review | - | target_without_source_mapping |
| `buprenorphine` | model_parameter | `model.theta.CL` | 54.0  | 54.0 L/h | derived_from_reported | source_2 | checked |
| `buprenorphine` | model_parameter | `model.theta.V` | 806.0  | 806.0 L | derived_from_reported | source_2 | checked |
| `buprenorphine` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 54.0 L/h | 54.0 L/h | literature_reported | source_2 | checked |
| `buprenorphine` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 54.0 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `buprenorphine` | pk_parameter | `V_abs_L_at_70kg` | 806.0 L | 806.0 L | literature_reported | source_2 | checked |
| `buprenorphine` | pk_parameter | `V_systemic_L_at_70kg` | 806.0 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `buprenorphine` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `buprenorphine` | pk_parameter | `clearance` | 54.0 L/h | 54.0 L/h | literature_reported | source_2 | checked |
| `buprenorphine` | pk_parameter | `ke_1_per_h` | 0.06699751861042183 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `buprenorphine` | pk_parameter | `t_half_h` | 10.345863472802147 h | 10.345863472802147 h | derived_from_reported | source_2 | checked |
| `buprenorphine` | pk_parameter | `volume` | 806.0 L | 806.0 L | literature_reported | source_2 | checked |
| `buprenorphine` | target | `targets.auc` | 5.555555555555555 ng*h/mL |   | dose_over_cl | - | derived_target |
| `buprenorphine` | target | `targets.t_half` | 10.345863472802147 h |   | unknown_needs_review | - | target_without_source_mapping |
| `carbamazepine` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `carbamazepine` | model_parameter | `model.theta.CL` | 4.8  | 4.8 L/h | derived_from_reported | source_1 | checked |
| `carbamazepine` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `carbamazepine` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `carbamazepine` | model_parameter | `model.theta.V` | 100.41157484587185  | 100.41157484587185 L | derived_from_reported | source_1 | checked |
| `carbamazepine` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 4.8 L/h | 4.8 L/h | label_reported | source_1 | checked |
| `carbamazepine` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 4.8 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `carbamazepine` | pk_parameter | `V_abs_L_at_70kg` | 100.41157484587185 L | 100.41157484587185 L | derived_from_reported | source_1 | checked |
| `carbamazepine` | pk_parameter | `V_systemic_L_at_70kg` | 100.41157484587185 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `carbamazepine` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `carbamazepine` | pk_parameter | `clearance` | 4.8 L/h | 4.8 L/h | label_reported | source_1 | checked |
| `carbamazepine` | pk_parameter | `ke_1_per_h` | 0.04780325383172036 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `carbamazepine` | pk_parameter | `t_half_h` | 14.5 h | 14.5 h | derived_from_reported | source_1 | checked |
| `carbamazepine` | pk_parameter | `volume` | 100.41157484587185 L | 100.41157484587185 L | derived_from_reported | source_1 | checked |
| `carbamazepine` | target | `targets.auc` | 41666.66666666667 ng*h/mL |   | dose_over_cl | - | derived_target |
| `carbamazepine` | target | `targets.t_half` | 14.5 h |   | unknown_needs_review | - | target_without_source_mapping |
| `cda1` | model_parameter | `model.theta.CL` | 0.00588  | 0.00588 L/h | derived_from_reported | source_2 | checked |
| `cda1` | model_parameter | `model.theta.V` | 4.9  | 4.9 L | derived_from_reported | source_2 | checked |
| `cda1` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 0.00588 L/h | 0.00588 L/h | literature_reported | source_2 | checked |
| `cda1` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 0.00588 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `cda1` | pk_parameter | `V_abs_L_at_70kg` | 4.9 L | 4.9 L | literature_reported | source_2 | checked |
| `cda1` | pk_parameter | `V_systemic_L_at_70kg` | 4.9 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `cda1` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `cda1` | pk_parameter | `clearance` | 8.4e-05 L/h/kg | 8.4e-05 L/h/kg | literature_reported | source_2 | checked |
| `cda1` | pk_parameter | `ke_1_per_h` | 0.0012 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `cda1` | pk_parameter | `t_half_h` | 685.2 h | 685.2 h | derived_from_reported | source_1 | checked |
| `cda1` | pk_parameter | `volume` | 0.07 L/kg | 0.07 L/kg | literature_reported | source_2 | checked |
| `cda1` | target | `targets.auc` | 17006802.721088436 ng*h/mL |   | dose_over_cl | - | derived_target |
| `cda1` | target | `targets.t_half` | 685.2 h |   | unknown_needs_review | - | target_without_source_mapping |
| `cimetidine` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `cimetidine` | model_parameter | `model.theta.CL` | 29.7  | 29.7 L/h | derived_from_reported | source_2 | checked |
| `cimetidine` | model_parameter | `model.theta.F1` | 0.6 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `cimetidine` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `cimetidine` | model_parameter | `model.theta.V` | 56.0  | 56.0 L | derived_from_reported | source_2 | checked |
| `cimetidine` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 29.7 L/h | 29.7 L/h | literature_reported | source_2 | checked |
| `cimetidine` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 29.7 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `cimetidine` | pk_parameter | `V_abs_L_at_70kg` | 56.0 L | 56.0 L | literature_reported | source_2 | checked |
| `cimetidine` | pk_parameter | `V_systemic_L_at_70kg` | 56.0 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `cimetidine` | pk_parameter | `bioavailability` | 0.6 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `cimetidine` | pk_parameter | `clearance` | 29.7 L/h | 29.7 L/h | literature_reported | source_2 | checked |
| `cimetidine` | pk_parameter | `ke_1_per_h` | 0.5303571428571429 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `cimetidine` | pk_parameter | `t_half_h` | 2.0 h | 2.0 h | label_reported | source_1 | checked |
| `cimetidine` | pk_parameter | `volume` | 0.8 L/kg | 0.8 L/kg | literature_reported | source_2 | checked |
| `cimetidine` | target | `targets.auc` | 2020.2020202020203 ng*h/mL |   | f_dose_over_cl | - | target_without_source_mapping |
| `cimetidine` | target | `targets.t_half` | 2.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `clarithromycin` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `clarithromycin` | model_parameter | `model.theta.CL` | 58.1  | 58.1 L/h | derived_from_reported | source_2 | checked |
| `clarithromycin` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `clarithromycin` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `clarithromycin` | model_parameter | `model.theta.V` | 172.0  | 172.0 L | derived_from_reported | source_3 | checked |
| `clarithromycin` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 58.1 L/h | 58.1 L/h | derived_from_reported | source_2 | checked |
| `clarithromycin` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 30.5025 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `clarithromycin` | pk_parameter | `V_abs_L_at_70kg` | 172.0 L | 172.0 L | derived_from_reported | source_3 | checked |
| `clarithromycin` | pk_parameter | `V_systemic_L_at_70kg` | 90.3 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `clarithromycin` | pk_parameter | `bioavailability` | 0.525 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `clarithromycin` | pk_parameter | `clearance` | 58.1 L/h | 58.1 L/h | derived_from_reported | source_2 | checked |
| `clarithromycin` | pk_parameter | `ke_1_per_h` | 0.3377906976744186 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `clarithromycin` | pk_parameter | `t_half_h` | 5.0 h | 5.0 h | derived_from_reported | source_1 | checked |
| `clarithromycin` | pk_parameter | `volume` | 172.0 L | 172.0 L | derived_from_reported | source_3 | checked |
| `clarithromycin` | target | `targets.auc` | 1721.170395869191 ng*h/mL |   | dose_over_cl | - | derived_target |
| `clarithromycin` | target | `targets.t_half` | 5.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `dapagliflozin` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `dapagliflozin` | model_parameter | `model.theta.CL` | 12.42  | 12.42 L/h | derived_from_reported | source_1 | checked |
| `dapagliflozin` | model_parameter | `model.theta.F1` | 0.78 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `dapagliflozin` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `dapagliflozin` | model_parameter | `model.theta.V` | 118.0  | 118.0 L | derived_from_reported | source_1 | checked |
| `dapagliflozin` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 12.42 L/h | 12.42 L/h | literature_reported | source_1 | checked |
| `dapagliflozin` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 12.42 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `dapagliflozin` | pk_parameter | `V_abs_L_at_70kg` | 118.0 L | 118.0 L | literature_reported | source_1 | checked |
| `dapagliflozin` | pk_parameter | `V_systemic_L_at_70kg` | 118.0 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `dapagliflozin` | pk_parameter | `bioavailability` | 0.78 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `dapagliflozin` | pk_parameter | `clearance` | 12.42 L/h | 12.42 L/h | literature_reported | source_1 | checked |
| `dapagliflozin` | pk_parameter | `ke_1_per_h` | 0.1052542372881356 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `dapagliflozin` | pk_parameter | `t_half_h` | 12.9 h | 12.9 h | label_reported | source_1 | checked |
| `dapagliflozin` | pk_parameter | `volume` | 118.0 L | 118.0 L | literature_reported | source_1 | checked |
| `dapagliflozin` | target | `targets.auc` | 628.0193236714975 ng*h/mL |   | f_dose_over_cl | - | target_without_source_mapping |
| `dapagliflozin` | target | `targets.t_half` | 12.9 h |   | unknown_needs_review | - | target_without_source_mapping |
| `efavirenz` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `efavirenz` | model_parameter | `model.theta.CL` | 13.9  | 13.9 L/h | derived_from_reported | source_2 | checked |
| `efavirenz` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `efavirenz` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `efavirenz` | model_parameter | `model.theta.V` | 1163.1007419646824  | 1163.1007419646824 L | derived_from_reported | source_2 | checked |
| `efavirenz` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 13.9 L/h | 13.9 L/h | literature_reported | source_2 | checked |
| `efavirenz` | pk_parameter | `V_abs_L_at_70kg` | 1163.1007419646824 L | 1163.1007419646824 L | derived_from_reported | source_2 | checked |
| `efavirenz` | pk_parameter | `clearance` | 13.9 L/h | 13.9 L/h | literature_reported | source_2 | checked |
| `efavirenz` | pk_parameter | `ke_1_per_h` | 0.01195081345793009 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `efavirenz` | pk_parameter | `t_half_h` | 58.0 h | 58.0 h | derived_from_reported | source_1 | checked |
| `efavirenz` | pk_parameter | `volume` | 1163.1007419646824 L | 1163.1007419646824 L | derived_from_reported | source_2 | checked |
| `efavirenz` | target | `targets.auc` | 7194.244604316546 ng*h/mL |   | dose_over_cl | - | derived_target |
| `efavirenz` | target | `targets.t_half` | 58.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `erythromycin` | model_parameter | `model.theta.CL` | 37.1  | 37.1 L/h | derived_from_reported | source_1 | checked |
| `erythromycin` | model_parameter | `model.theta.V` | 123.10516783905524  | 123.10516783905524 L | derived_from_reported | source_1 | checked |
| `erythromycin` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 37.1 L/h | 37.1 L/h | literature_reported | source_1 | checked |
| `erythromycin` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 37.1 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `erythromycin` | pk_parameter | `V_abs_L_at_70kg` | 123.10516783905524 L | 123.10516783905524 L | fixture_derived | source_1 | checked |
| `erythromycin` | pk_parameter | `V_systemic_L_at_70kg` | 123.10516783905524 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `erythromycin` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `erythromycin` | pk_parameter | `clearance` | 0.53 L/h/kg | 0.53 L/h/kg | literature_reported | source_1 | checked |
| `erythromycin` | pk_parameter | `ke_1_per_h` | 0.3013683393738893 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `erythromycin` | pk_parameter | `t_half_h` | 2.3 h | 2.3 h | literature_reported | source_1 | checked |
| `erythromycin` | pk_parameter | `volume` | 1.7586452548436462 L/kg | 1.7586452548436462 L/kg | fixture_derived | source_1 | checked |
| `erythromycin` | target | `targets.auc` | 3369.272237196765 ng*h/mL |   | dose_over_cl | - | derived_target |
| `erythromycin` | target | `targets.t_half` | 2.3 h |   | unknown_needs_review | - | target_without_source_mapping |
| `ethinylestradiol` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `ethinylestradiol` | model_parameter | `model.theta.CL` | 25.7  | 25.7 L/h | derived_from_reported | source_1 | checked |
| `ethinylestradiol` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `ethinylestradiol` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `ethinylestradiol` | model_parameter | `model.theta.V` | 632.1673264919305  | 632.1673264919305 L | derived_from_reported | source_1 | checked |
| `ethinylestradiol` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 25.7 L/h | 25.7 L/h | literature_reported | source_1 | checked |
| `ethinylestradiol` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 11.051 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `ethinylestradiol` | pk_parameter | `V_abs_L_at_70kg` | 632.1673264919305 L | 632.1673264919305 L | fixture_derived | source_1 | checked |
| `ethinylestradiol` | pk_parameter | `V_systemic_L_at_70kg` | 271.8319503915301 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `ethinylestradiol` | pk_parameter | `bioavailability` | 0.43 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `ethinylestradiol` | pk_parameter | `clearance` | 25.7 L/h | 25.7 L/h | literature_reported | source_1 | checked |
| `ethinylestradiol` | pk_parameter | `ke_1_per_h` | 0.04065379358122846 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `ethinylestradiol` | pk_parameter | `t_half_h` | 17.05 h | 17.05 h | derived_from_reported | source_1 | checked |
| `ethinylestradiol` | pk_parameter | `volume` | 632.1673264919305 L | 632.1673264919305 L | fixture_derived | source_1 | checked |
| `ethinylestradiol` | target | `targets.auc` | 3891.0505836575876 ng*h/mL |   | dose_over_cl | - | derived_target |
| `ethinylestradiol` | target | `targets.t_half` | 17.05 h |   | unknown_needs_review | - | target_without_source_mapping |
| `felodipine` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `felodipine` | model_parameter | `model.theta.CL` | 90.0  | 90.0 L/h | derived_from_reported | source_2 | checked |
| `felodipine` | model_parameter | `model.theta.F1` | 0.15 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `felodipine` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `felodipine` | model_parameter | `model.theta.V` | 700.0  | 700.0 L | derived_from_reported | source_2 | checked |
| `felodipine` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 90.0 L/h | 90.0 L/h | derived_from_reported | source_2 | checked |
| `felodipine` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 90.0 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `felodipine` | pk_parameter | `V_abs_L_at_70kg` | 700.0 L | 700.0 L | derived_from_reported | source_2 | checked |
| `felodipine` | pk_parameter | `V_systemic_L_at_70kg` | 700.0 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `felodipine` | pk_parameter | `bioavailability` | 0.15 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `felodipine` | pk_parameter | `clearance` | 90.0 L/h | 90.0 L/h | derived_from_reported | source_2 | checked |
| `felodipine` | pk_parameter | `ke_1_per_h` | 0.12857142857142856 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `felodipine` | pk_parameter | `t_half_h` | 24.5 h | 24.5 h | derived_from_reported | source_2 | checked |
| `felodipine` | pk_parameter | `volume` | 10.0 L/kg | 10.0 L/kg | derived_from_reported | source_2 | checked |
| `felodipine` | target | `targets.auc` | 166.66666666666666 ng*h/mL |   | f_dose_over_cl | - | target_without_source_mapping |
| `felodipine` | target | `targets.t_half` | 24.5 h |   | unknown_needs_review | - | target_without_source_mapping |
| `fluconazole` | model_parameter | `model.theta.CL` | 0.966  | 0.966 L/h | derived_from_reported | source_1 | checked |
| `fluconazole` | model_parameter | `model.theta.V` | 41.80930228496216  | 41.80930228496216 L | derived_from_reported | source_1 | checked |
| `fluconazole` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 0.966 L/h | 0.966 L/h | derived_from_reported | source_1 | checked |
| `fluconazole` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 0.966 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `fluconazole` | pk_parameter | `V_abs_L_at_70kg` | 41.80930228496216 L | 41.80930228496216 L | fixture_derived | source_1 | checked |
| `fluconazole` | pk_parameter | `V_systemic_L_at_70kg` | 41.80930228496216 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `fluconazole` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `fluconazole` | pk_parameter | `clearance` | 0.0138 L/h/kg | 0.0138 L/h/kg | derived_from_reported | source_1 | checked |
| `fluconazole` | pk_parameter | `ke_1_per_h` | 0.023104906018664845 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `fluconazole` | pk_parameter | `t_half_h` | 30.0 h | 30.0 h | label_reported | source_1 | checked |
| `fluconazole` | pk_parameter | `volume` | 0.5972757469280309 L/kg | 0.5972757469280309 L/kg | fixture_derived | source_1 | checked |
| `fluconazole` | target | `targets.auc` | 207039.33747412008 ng*h/mL |   | dose_over_cl | - | derived_target |
| `fluconazole` | target | `targets.t_half` | 30.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `fluvoxamine` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `fluvoxamine` | model_parameter | `model.theta.CL` | 65.56797653945428  | 65.56797653945428 L/h | derived_from_reported | source_1 | checked |
| `fluvoxamine` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `fluvoxamine` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `fluvoxamine` | model_parameter | `model.theta.V` | 1750.0  | 1750.0 L | derived_from_reported | source_1 | checked |
| `fluvoxamine` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 65.56797653945428 L/h | 65.56797653945428 L/h | derived_from_reported | source_1 | checked |
| `fluvoxamine` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 34.75102756591077 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `fluvoxamine` | pk_parameter | `V_abs_L_at_70kg` | 1750.0 L | 1750.0 L | literature_reported | source_1 | checked |
| `fluvoxamine` | pk_parameter | `V_systemic_L_at_70kg` | 927.5 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `fluvoxamine` | pk_parameter | `bioavailability` | 0.53 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `fluvoxamine` | pk_parameter | `clearance` | 65.56797653945428 L/h | 65.56797653945428 L/h | derived_from_reported | source_1 | checked |
| `fluvoxamine` | pk_parameter | `ke_1_per_h` | 0.037467415165402446 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `fluvoxamine` | pk_parameter | `t_half_h` | 18.5 h | 18.5 h | derived_from_reported | source_1 | checked |
| `fluvoxamine` | pk_parameter | `volume` | 25.0 L/kg | 25.0 L/kg | literature_reported | source_1 | checked |
| `fluvoxamine` | target | `targets.auc` | 1525.1347575111902 ng*h/mL |   | dose_over_cl | - | derived_target |
| `fluvoxamine` | target | `targets.t_half` | 18.5 h |   | unknown_needs_review | - | target_without_source_mapping |
| `inulin` | model_parameter | `model.theta.CL` | 5.61  | 5.61 L/h | derived_from_reported | source_3 | checked |
| `inulin` | model_parameter | `model.theta.V` | 13.0  | 13.0 L | derived_from_reported | source_3 | checked |
| `inulin` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 5.61 L/h | 5.61 L/h | literature_reported | source_3 | checked |
| `inulin` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 5.61 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `inulin` | pk_parameter | `V_abs_L_at_70kg` | 13.0 L | 13.0 L | literature_reported | source_3 | checked |
| `inulin` | pk_parameter | `V_systemic_L_at_70kg` | 13.0 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `inulin` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `inulin` | pk_parameter | `clearance` | 5.61 L/h | 5.61 L/h | literature_reported | source_3 | checked |
| `inulin` | pk_parameter | `ke_1_per_h` | 0.43153846153846154 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `inulin` | pk_parameter | `t_half_h` | 1.6062234130622617 h | 1.6062234130622617 h | derived_from_reported | source_3 | checked |
| `inulin` | pk_parameter | `volume` | 13.0 L | 13.0 L | literature_reported | source_3 | checked |
| `inulin` | target | `targets.auc` | 17825.311942959 ng*h/mL |   | dose_over_cl | - | derived_target |
| `inulin` | target | `targets.t_half` | 1.6062234130622617 h |   | unknown_needs_review | - | target_without_source_mapping |
| `itraconazole` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `itraconazole` | model_parameter | `model.theta.CL` | 16.68  | 16.68 L/h | derived_from_reported | source_1 | checked |
| `itraconazole` | model_parameter | `model.theta.F1` | 0.55 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `itraconazole` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `itraconazole` | model_parameter | `model.theta.V` | 700.0  | 700.0 L | derived_from_reported | source_1 | checked |
| `itraconazole` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 16.68 L/h | 16.68 L/h | label_reported | source_1 | checked |
| `itraconazole` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 16.68 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `itraconazole` | pk_parameter | `V_abs_L_at_70kg` | 700.0 L | 700.0 L | derived_from_reported | source_1 | checked |
| `itraconazole` | pk_parameter | `V_systemic_L_at_70kg` | 700.0 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `itraconazole` | pk_parameter | `bioavailability` | 0.55 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `itraconazole` | pk_parameter | `clearance` | 16.68 L/h | 16.68 L/h | label_reported | source_1 | checked |
| `itraconazole` | pk_parameter | `ke_1_per_h` | 0.023828571428571428 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `itraconazole` | pk_parameter | `t_half_h` | 22.0 h | 22.0 h | derived_from_reported | source_1 | checked |
| `itraconazole` | pk_parameter | `volume` | 700.0 L | 700.0 L | derived_from_reported | source_1 | checked |
| `itraconazole` | target | `targets.auc` | 3297.3621103117507 ng*h/mL |   | f_dose_over_cl | - | target_without_source_mapping |
| `itraconazole` | target | `targets.t_half` | 22.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `mefenamic_acid` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `mefenamic_acid` | model_parameter | `model.theta.CL` | 21.13  | 21.13 L/h | derived_from_reported | source_1 | checked |
| `mefenamic_acid` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `mefenamic_acid` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `mefenamic_acid` | model_parameter | `model.theta.V` | 74.2  | 74.2 L | derived_from_reported | source_1 | checked |
| `mefenamic_acid` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 21.13 L/h | 21.13 L/h | literature_reported | source_1 | checked |
| `mefenamic_acid` | pk_parameter | `V_abs_L_at_70kg` | 74.2 L | 74.2 L | literature_reported | source_1 | checked |
| `mefenamic_acid` | pk_parameter | `clearance` | 21.13 L/h | 21.13 L/h | literature_reported | source_1 | checked |
| `mefenamic_acid` | pk_parameter | `ke_1_per_h` | 0.2847708894878706 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `mefenamic_acid` | pk_parameter | `t_half_h` | 3.0 h | 3.0 h | derived_from_reported | source_1 | checked |
| `mefenamic_acid` | pk_parameter | `volume` | 1.06 L/kg | 1.06 L/kg | literature_reported | source_1 | checked |
| `mefenamic_acid` | target | `targets.auc` | 4732.60766682442 ng*h/mL |   | dose_over_cl | - | derived_target |
| `mefenamic_acid` | target | `targets.t_half` | 3.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `metoprolol` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `metoprolol` | model_parameter | `model.theta.CL` | 48.0  | 48.0 L/h | derived_from_reported | source_2 | checked |
| `metoprolol` | model_parameter | `model.theta.F1` | 0.5 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `metoprolol` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `metoprolol` | model_parameter | `model.theta.V` | 346.2468098133512  | 346.2468098133512 L | derived_from_reported | source_1 | checked |
| `metoprolol` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 48.0 L/h | 48.0 L/h | literature_reported | source_2 | checked |
| `metoprolol` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 48.0 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `metoprolol` | pk_parameter | `V_abs_L_at_70kg` | 346.2468098133512 L | 346.2468098133512 L | derived_from_reported | source_1 | checked |
| `metoprolol` | pk_parameter | `V_systemic_L_at_70kg` | 346.2468098133512 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `metoprolol` | pk_parameter | `bioavailability` | 0.5 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `metoprolol` | pk_parameter | `clearance` | 48.0 L/h | 48.0 L/h | literature_reported | source_2 | checked |
| `metoprolol` | pk_parameter | `ke_1_per_h` | 0.13862943611198908 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `metoprolol` | pk_parameter | `t_half_h` | 5.0 h | 5.0 h | derived_from_reported | source_1 | checked |
| `metoprolol` | pk_parameter | `volume` | 346.2468098133512 L | 346.2468098133512 L | derived_from_reported | source_1 | checked |
| `metoprolol` | target | `targets.auc` | 1041.6666666666667 ng*h/mL |   | f_dose_over_cl | - | target_without_source_mapping |
| `metoprolol` | target | `targets.t_half` | 5.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `mexiletine` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `mexiletine` | model_parameter | `model.theta.CL` | 30.87655622494302  | 30.87655622494302 L/h | derived_from_reported | source_1 | checked |
| `mexiletine` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `mexiletine` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `mexiletine` | model_parameter | `model.theta.V` | 490.0  | 490.0 L | derived_from_reported | source_1 | checked |
| `mexiletine` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 30.87655622494302 L/h | 30.87655622494302 L/h | derived_from_reported | source_1 | checked |
| `mexiletine` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 27.788900602448717 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `mexiletine` | pk_parameter | `V_abs_L_at_70kg` | 490.0 L | 490.0 L | derived_from_reported | source_1 | checked |
| `mexiletine` | pk_parameter | `V_systemic_L_at_70kg` | 441.0 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `mexiletine` | pk_parameter | `bioavailability` | 0.9 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `mexiletine` | pk_parameter | `clearance` | 30.87655622494302 L/h | 30.87655622494302 L/h | derived_from_reported | source_1 | checked |
| `mexiletine` | pk_parameter | `ke_1_per_h` | 0.06301338005090412 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `mexiletine` | pk_parameter | `t_half_h` | 11.0 h | 11.0 h | derived_from_reported | source_1 | checked |
| `mexiletine` | pk_parameter | `volume` | 7.0 L/kg | 7.0 L/kg | derived_from_reported | source_1 | checked |
| `mexiletine` | target | `targets.auc` | 3238.7031530160402 ng*h/mL |   | dose_over_cl | - | derived_target |
| `mexiletine` | target | `targets.t_half` | 11.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `moclobemide` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `moclobemide` | model_parameter | `model.theta.CL` | 39.4  | 39.4 L/h | derived_from_reported | source_5 | checked |
| `moclobemide` | model_parameter | `model.theta.F1` | 0.56 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `moclobemide` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `moclobemide` | model_parameter | `model.theta.V` | 84.3  | 84.3 L | derived_from_reported | source_5 | checked |
| `moclobemide` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 39.4 L/h | 39.4 L/h | derived_from_reported | source_5 | checked |
| `moclobemide` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 39.4 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `moclobemide` | pk_parameter | `V_abs_L_at_70kg` | 84.3 L | 84.3 L | literature_reported | source_5 | checked |
| `moclobemide` | pk_parameter | `V_systemic_L_at_70kg` | 84.3 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `moclobemide` | pk_parameter | `bioavailability` | 0.56 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `moclobemide` | pk_parameter | `clearance` | 39.4 L/h | 39.4 L/h | derived_from_reported | source_5 | checked |
| `moclobemide` | pk_parameter | `ke_1_per_h` | 0.46737841043890865 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `moclobemide` | pk_parameter | `t_half_h` | 1.6 h | 1.6 h | literature_reported | source_5 | checked |
| `moclobemide` | pk_parameter | `volume` | 84.3 L | 84.3 L | literature_reported | source_5 | checked |
| `moclobemide` | target | `targets.auc` | 1421.3197969543148 ng*h/mL |   | f_dose_over_cl | - | target_without_source_mapping |
| `moclobemide` | target | `targets.t_half` | 1.6 h |   | unknown_needs_review | - | target_without_source_mapping |
| `montelukast` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `montelukast` | model_parameter | `model.theta.CL` | 1.8479999999999999  | 1.8479999999999999 L/h | derived_from_reported | source_1 | checked |
| `montelukast` | model_parameter | `model.theta.F1` | 0.615 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `montelukast` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `montelukast` | model_parameter | `model.theta.V` | 9.7  | 9.7 L | derived_from_reported | source_1 | checked |
| `montelukast` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 1.8479999999999999 L/h | 1.8479999999999999 L/h | literature_reported | source_1 | checked |
| `montelukast` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 1.8479999999999999 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `montelukast` | pk_parameter | `V_abs_L_at_70kg` | 9.7 L | 9.7 L | literature_reported | source_1 | checked |
| `montelukast` | pk_parameter | `V_systemic_L_at_70kg` | 9.7 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `montelukast` | pk_parameter | `bioavailability` | 0.615 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `montelukast` | pk_parameter | `clearance` | 1.8479999999999999 L/h | 1.8479999999999999 L/h | literature_reported | source_1 | checked |
| `montelukast` | pk_parameter | `ke_1_per_h` | 0.19051546391752577 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `montelukast` | pk_parameter | `t_half_h` | 6.7 h | 6.7 h | literature_reported | source_1 | checked |
| `montelukast` | pk_parameter | `volume` | 9.7 L | 9.7 L | literature_reported | source_1 | checked |
| `montelukast` | target | `targets.auc` | 33279.22077922078 ng*h/mL |   | f_dose_over_cl | - | target_without_source_mapping |
| `montelukast` | target | `targets.t_half` | 6.7 h |   | unknown_needs_review | - | target_without_source_mapping |
| `motavizumab_medi_524` | model_parameter | `model.theta.CL` | 0.010229166666666666  | 0.010229166666666666 L/h | derived_from_reported | source_1 | checked |
| `motavizumab_medi_524` | model_parameter | `model.theta.V` | 7.35  | 7.35 L | derived_from_reported | source_1 | checked |
| `motavizumab_medi_524` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 0.010229166666666666 L/h | 0.010229166666666666 L/h | derived_from_reported | source_1 | checked |
| `motavizumab_medi_524` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 0.010229166666666666 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `motavizumab_medi_524` | pk_parameter | `V_abs_L_at_70kg` | 7.35 L | 7.35 L | derived_from_reported | source_1 | checked |
| `motavizumab_medi_524` | pk_parameter | `V_systemic_L_at_70kg` | 7.35 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `motavizumab_medi_524` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `motavizumab_medi_524` | pk_parameter | `clearance` | 0.010229166666666666 L/h | 0.010229166666666666 L/h | derived_from_reported | source_1 | checked |
| `motavizumab_medi_524` | pk_parameter | `ke_1_per_h` | 0.0013917233560090702 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `motavizumab_medi_524` | pk_parameter | `t_half_h` | 636.0 h | 636.0 h | derived_from_reported | source_1 | checked |
| `motavizumab_medi_524` | pk_parameter | `volume` | 7.35 L | 7.35 L | derived_from_reported | source_1 | checked |
| `motavizumab_medi_524` | target | `targets.auc` | 9775967.413441956 ng*h/mL |   | dose_over_cl | - | derived_target |
| `motavizumab_medi_524` | target | `targets.t_half` | 636.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `motavizumab_yte` | model_parameter | `model.theta.CL` | 0.0022916666666666667  | 0.0022916666666666667 L/h | derived_from_reported | source_1 | checked |
| `motavizumab_yte` | model_parameter | `model.theta.V` | 6.744599316155904  | 6.744599316155904 L | derived_from_reported | source_1 | checked |
| `motavizumab_yte` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 0.0022916666666666667 L/h | 0.0022916666666666667 L/h | derived_from_reported | source_1 | checked |
| `motavizumab_yte` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 0.0022916666666666667 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `motavizumab_yte` | pk_parameter | `V_abs_L_at_70kg` | 6.744599316155904 L | 6.744599316155904 L | fixture_derived | source_1 | checked |
| `motavizumab_yte` | pk_parameter | `V_systemic_L_at_70kg` | 6.744599316155904 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `motavizumab_yte` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `motavizumab_yte` | pk_parameter | `clearance` | 0.0022916666666666667 L/h | 0.0022916666666666667 L/h | derived_from_reported | source_1 | checked |
| `motavizumab_yte` | pk_parameter | `ke_1_per_h` | 0.0003397780296862477 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `motavizumab_yte` | pk_parameter | `t_half_h` | 2040 h | 2040 h | derived_from_reported | source_1 | checked |
| `motavizumab_yte` | pk_parameter | `volume` | 6.744599316155904 L | 6.744599316155904 L | fixture_derived | source_1 | checked |
| `motavizumab_yte` | target | `targets.auc` | 43636363.63636363 ng*h/mL |   | dose_over_cl | - | derived_target |
| `motavizumab_yte` | target | `targets.t_half` | 2040.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `omeprazole` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `omeprazole` | model_parameter | `model.theta.CL` | 43.56  | 43.56 L/h | derived_from_reported | source_4 | checked |
| `omeprazole` | model_parameter | `model.theta.F1` | 0.35 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `omeprazole` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `omeprazole` | model_parameter | `model.theta.V` | 16.1  | 16.1 L | derived_from_reported | source_4 | checked |
| `omeprazole` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 43.56 L/h | 43.56 L/h | literature_reported | source_4 | checked |
| `omeprazole` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 43.56 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `omeprazole` | pk_parameter | `V_abs_L_at_70kg` | 16.1 L | 16.1 L | literature_reported | source_4 | checked |
| `omeprazole` | pk_parameter | `V_systemic_L_at_70kg` | 16.1 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `omeprazole` | pk_parameter | `bioavailability` | 0.35 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `omeprazole` | pk_parameter | `clearance` | 43.56 L/h | 43.56 L/h | literature_reported | source_4 | checked |
| `omeprazole` | pk_parameter | `ke_1_per_h` | 2.705590062111801 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `omeprazole` | pk_parameter | `t_half_h` | 0.75 h | 0.75 h | derived_from_reported | source_2 | checked |
| `omeprazole` | pk_parameter | `volume` | 0.23 L/kg | 0.23 L/kg | literature_reported | source_4 | checked |
| `omeprazole` | target | `targets.auc` | 803.4894398530762 ng*h/mL |   | f_dose_over_cl | - | target_without_source_mapping |
| `omeprazole` | target | `targets.t_half` | 0.75 h |   | unknown_needs_review | - | target_without_source_mapping |
| `raltegravir` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `raltegravir` | model_parameter | `model.theta.CL` | 60.2  | 60.2 L/h | derived_from_reported | source_1 | checked |
| `raltegravir` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `raltegravir` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `raltegravir` | model_parameter | `model.theta.V` | 677.4318833998217  | 677.4318833998217 L | derived_from_reported | source_1 | checked |
| `raltegravir` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 60.2 L/h | 60.2 L/h | literature_reported | source_1 | checked |
| `raltegravir` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 60.2 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `raltegravir` | pk_parameter | `V_abs_L_at_70kg` | 677.4318833998217 L | 677.4318833998217 L | derived_from_reported | source_1 | checked |
| `raltegravir` | pk_parameter | `V_systemic_L_at_70kg` | 677.4318833998217 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `raltegravir` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `raltegravir` | pk_parameter | `clearance` | 60.2 L/h | 60.2 L/h | literature_reported | source_1 | checked |
| `raltegravir` | pk_parameter | `ke_1_per_h` | 0.08886502314871093 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `raltegravir` | pk_parameter | `t_half_h` | 7.8 h | 7.8 h | literature_reported | source_2 | checked |
| `raltegravir` | pk_parameter | `volume` | 677.4318833998217 L | 677.4318833998217 L | derived_from_reported | source_1 | checked |
| `raltegravir` | target | `targets.auc` | 6644.518272425249 ng*h/mL |   | dose_over_cl | - | derived_target |
| `raltegravir` | target | `targets.t_half` | 7.8 h |   | unknown_needs_review | - | target_without_source_mapping |
| `sildenafil` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `sildenafil` | model_parameter | `model.theta.CL` | 18.195113489698564  | 18.195113489698564 L/h | derived_from_reported | source_2 | checked |
| `sildenafil` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `sildenafil` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `sildenafil` | model_parameter | `model.theta.V` | 105.0  | 105.0 L | derived_from_reported | source_3 | checked |
| `sildenafil` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 18.195113489698564 L/h | 18.195113489698564 L/h | fixture_derived | source_2 | checked |
| `sildenafil` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 8.005849935467369 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `sildenafil` | pk_parameter | `V_abs_L_at_70kg` | 105.0 L | 105.0 L | literature_reported | source_3 | checked |
| `sildenafil` | pk_parameter | `V_systemic_L_at_70kg` | 46.2 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `sildenafil` | pk_parameter | `bioavailability` | 0.44 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `sildenafil` | pk_parameter | `clearance` | 18.195113489698564 L/h | 18.195113489698564 L/h | fixture_derived | source_2 | checked |
| `sildenafil` | pk_parameter | `ke_1_per_h` | 0.17328679513998632 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `sildenafil` | pk_parameter | `t_half_h` | 4.0 h | 4.0 h | derived_from_reported | source_2 | checked |
| `sildenafil` | pk_parameter | `volume` | 105.0 L | 105.0 L | literature_reported | source_3 | checked |
| `sildenafil` | target | `targets.auc` | 5495.981108148432 ng*h/mL |   | dose_over_cl | - | derived_target |
| `sildenafil` | target | `targets.t_half` | 4.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `sufentanil` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `sufentanil` | model_parameter | `model.theta.CL` | 108.0  | 108.0 L/h | derived_from_reported | source_1 | checked |
| `sufentanil` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_no_external_source |
| `sufentanil` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `sufentanil` | model_parameter | `model.theta.V` | 2087.868263174508  | 2087.868263174508 L | derived_from_reported | source_1 | checked |
| `sufentanil` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 108.0 L/h | 108.0 L/h | label_reported | source_1 | checked |
| `sufentanil` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 57.24 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `sufentanil` | pk_parameter | `V_abs_L_at_70kg` | 2087.868263174508 L | 2087.868263174508 L | fixture_derived | source_1 | checked |
| `sufentanil` | pk_parameter | `V_systemic_L_at_70kg` | 1106.5701794824893 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `sufentanil` | pk_parameter | `bioavailability` | 0.53 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `sufentanil` | pk_parameter | `clearance` | 108.0 L/h | 108.0 L/h | label_reported | source_1 | checked |
| `sufentanil` | pk_parameter | `ke_1_per_h` | 0.05172740153432428 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `sufentanil` | pk_parameter | `t_half_h` | 13.4 h | 13.4 h | label_reported | source_1 | checked |
| `sufentanil` | pk_parameter | `volume` | 2087.868263174508 L | 2087.868263174508 L | fixture_derived | source_1 | checked |
| `sufentanil` | target | `targets.auc` | 0.278 ng*h/mL |   | literature_reported | - | target_without_source_mapping |
| `sufentanil` | target | `targets.t_half` | 13.4 h |   | unknown_needs_review | - | target_without_source_mapping |
| `tefibazumab` | model_parameter | `model.theta.CL` | 0.012  | 0.012 L/h | derived_from_reported | source_1 | checked |
| `tefibazumab` | model_parameter | `model.theta.V` | 7.3  | 7.3 L | derived_from_reported | source_1 | checked |
| `tefibazumab` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 0.012 L/h | 0.012 L/h | literature_reported | source_1 | checked |
| `tefibazumab` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 0.012 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `tefibazumab` | pk_parameter | `V_abs_L_at_70kg` | 7.3 L | 7.3 L | literature_reported | source_1 | checked |
| `tefibazumab` | pk_parameter | `V_systemic_L_at_70kg` | 7.3 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `tefibazumab` | pk_parameter | `bioavailability` | 1.0 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `tefibazumab` | pk_parameter | `clearance` | 0.012 L/h | 0.012 L/h | literature_reported | source_1 | checked |
| `tefibazumab` | pk_parameter | `ke_1_per_h` | 0.0016438356164383563 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `tefibazumab` | pk_parameter | `t_half_h` | 420.0 h | 420.0 h | derived_from_reported | source_1 | checked |
| `tefibazumab` | pk_parameter | `volume` | 7.3 L | 7.3 L | literature_reported | source_1 | checked |
| `tefibazumab` | target | `targets.auc` | 8333333.333333333 ng*h/mL |   | dose_over_cl | - | derived_target |
| `tefibazumab` | target | `targets.t_half` | 420.0 h |   | unknown_needs_review | - | target_without_source_mapping |
| `tizanidine` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `tizanidine` | model_parameter | `model.theta.CL` | 46.579490533628324  | 46.579490533628324 L/h | derived_from_reported | source_1 | checked |
| `tizanidine` | model_parameter | `model.theta.F1` | 0.4 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `tizanidine` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `tizanidine` | model_parameter | `model.theta.V` | 168.0  | 168.0 L | derived_from_reported | source_1 | checked |
| `tizanidine` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 46.579490533628324 L/h | 46.579490533628324 L/h | derived_from_reported | source_1 | checked |
| `tizanidine` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 46.579490533628324 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `tizanidine` | pk_parameter | `V_abs_L_at_70kg` | 168.0 L | 168.0 L | literature_reported | source_1 | checked |
| `tizanidine` | pk_parameter | `V_systemic_L_at_70kg` | 168.0 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `tizanidine` | pk_parameter | `bioavailability` | 0.4 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `tizanidine` | pk_parameter | `clearance` | 46.579490533628324 L/h | 46.579490533628324 L/h | derived_from_reported | source_1 | checked |
| `tizanidine` | pk_parameter | `ke_1_per_h` | 0.2772588722239781 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `tizanidine` | pk_parameter | `t_half_h` | 2.5 h | 2.5 h | label_reported | source_1 | checked |
| `tizanidine` | pk_parameter | `volume` | 2.4 L/kg | 2.4 L/kg | literature_reported | source_1 | checked |
| `tizanidine` | target | `targets.auc` | 858.7470481481926 ng*h/mL |   | f_dose_over_cl | - | target_without_source_mapping |
| `tizanidine` | target | `targets.t_half` | 2.5 h |   | unknown_needs_review | - | target_without_source_mapping |
| `triazolam` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `triazolam` | model_parameter | `model.theta.CL` | 31.560000000000002  | 31.560000000000002 L/h | derived_from_reported | source_3 | checked |
| `triazolam` | model_parameter | `model.theta.F1` | 1.0 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `triazolam` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `triazolam` | model_parameter | `model.theta.V` | 159.36009421659492  | 159.36009421659492 L | derived_from_reported | source_3 | checked |
| `triazolam` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 31.560000000000002 L/h | 31.560000000000002 L/h | literature_reported | source_3 | checked |
| `triazolam` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 13.886400000000002 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `triazolam` | pk_parameter | `V_abs_L_at_70kg` | 159.36009421659492 L | 159.36009421659492 L | derived_from_reported | source_3 | checked |
| `triazolam` | pk_parameter | `V_systemic_L_at_70kg` | 70.11844145530176 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `triazolam` | pk_parameter | `bioavailability` | 0.44 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `triazolam` | pk_parameter | `clearance` | 31.560000000000002 L/h | 31.560000000000002 L/h | literature_reported | source_3 | checked |
| `triazolam` | pk_parameter | `ke_1_per_h` | 0.19804205158855578 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `triazolam` | pk_parameter | `t_half_h` | 3.5 h | 3.5 h | derived_from_reported | source_1 | checked |
| `triazolam` | pk_parameter | `volume` | 159.36009421659492 L | 159.36009421659492 L | derived_from_reported | source_3 | checked |
| `triazolam` | target | `targets.auc` | 3168.5678073510776 ng*h/mL |   | dose_over_cl | - | derived_target |
| `triazolam` | target | `targets.t_half` | 3.5 h |   | unknown_needs_review | - | target_without_source_mapping |
| `verapamil` | model_parameter | `model.theta.ALAG1` | 0.5  |   | fixture_policy | - | fixture_policy_no_external_source |
| `verapamil` | model_parameter | `model.theta.CL` | 30.0384  | 30.0384 L/h | derived_from_reported | source_3 | checked |
| `verapamil` | model_parameter | `model.theta.F1` | 0.2247 fraction |   | fixture_policy | - | fixture_policy_apparent_parameters |
| `verapamil` | model_parameter | `model.theta.KA` | 1.2  |   | fixture_policy | - | fixture_policy_no_external_source |
| `verapamil` | model_parameter | `model.theta.V` | 175.7  | 175.7 L | derived_from_reported | source_3 | checked |
| `verapamil` | pk_parameter | `CL_abs_L_per_h_at_70kg` | 30.0384 L/h | 30.0384 L/h | literature_reported | source_3 | checked |
| `verapamil` | pk_parameter | `CL_systemic_L_per_h_at_70kg` | 30.0384 L/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `verapamil` | pk_parameter | `V_abs_L_at_70kg` | 175.7 L | 175.7 L | literature_reported | source_3 | checked |
| `verapamil` | pk_parameter | `V_systemic_L_at_70kg` | 175.7 L |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `verapamil` | pk_parameter | `bioavailability` | 0.2247 fraction |   | - | - | source_url_present_not_parameter_mapped |
| `verapamil` | pk_parameter | `clearance` | 30.0384 L/h | 30.0384 L/h | literature_reported | source_3 | checked |
| `verapamil` | pk_parameter | `ke_1_per_h` | 0.17096414342629482 1/h |   | derived_from_reported | - | derived_from_pk_yml_source_fields |
| `verapamil` | pk_parameter | `t_half_h` | 5.1 h | 5.1 h | derived_from_reported | source_1 | checked |
| `verapamil` | pk_parameter | `volume` | 175.7 L | 175.7 L | literature_reported | source_3 | checked |
| `verapamil` | target | `targets.auc` | 748.0425055928413 ng*h/mL |   | f_dose_over_cl | - | target_without_source_mapping |
| `verapamil` | target | `targets.t_half` | 5.1 h |   | unknown_needs_review | - | target_without_source_mapping |

## ソースURL

| Drug | Source key | URL |
| --- | --- | --- |
| `abciximab` | `source_1` | https://go.drugbank.com/drugs/DB00054 |
| `abciximab` | `source_2` | https://pubmed.ncbi.nlm.nih.gov/11907493/ |
| `abciximab` | `source_3` | https://www.researchgate.net/publication/232754238_Pharmacokinetics_PK_pharmacodynamics_PD_and_GPIIBIIIA_receptor_blockade_of_ABCIXIMAB_in_stable_angina_pectoris_patients |
| `abciximab` | `source_4` | https://www.sciencedirect.com/topics/biochemistry-genetics-and-molecular-biology/abciximab |
| `abciximab` | `source_5` | https://pubmed.ncbi.nlm.nih.gov/14618072/ |
| `abciximab` | `source_6` | https://ascpt.onlinelibrary.wiley.com/doi/abs/10.1016/j.clpt.2003.11.342 |
| `aciclovir` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=e8a0f9f8-294f-4dd6-bd55-10a6253f1aa8 |
| `aciclovir` | `source_2` | https://pubmed.ncbi.nlm.nih.gov/6355048/ |
| `aciclovir` | `source_3` | https://www.sciencedirect.com/science/article/pii/S2590170220300339 |
| `aciclovir` | `source_4` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=69a98000-adef-4323-89a7-09e035a257d4 |
| `aciclovir` | `source_5` | https://pubmed.ncbi.nlm.nih.gov/7048912/ |
| `albuterol` | `source_1` | https://pubmed.ncbi.nlm.nih.gov/3790406/ |
| `alfentanil` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/downloadpdffile.cfm?setId=c965d63f-933b-4a83-88f6-c8c74159530b |
| `alprazolam` | `source_1` | https://pubmed.ncbi.nlm.nih.gov/8513649/ |
| `amikacin` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=0b56f6df-a05d-4520-8bf0-d7cefe20f6ad |
| `apixaban` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=095a08ac-cf0e-497e-a682-ddef38d6b29c |
| `atazanavir` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=7fbea274-d6b5-4faa-bbf0-05fefab42114 |
| `atazanavir` | `source_2` | https://pmc.ncbi.nlm.nih.gov/articles/PMC1635184/ |
| `buprenorphine` | `source_2` | https://pmc.ncbi.nlm.nih.gov/articles/PMC3663890/ |
| `carbamazepine` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=52f0f753-a70c-4572-a85c-97ea7a2601a9 |
| `cda1` | `source_1` | https://pubmed.ncbi.nlm.nih.gov/18502001/ |
| `cda1` | `source_2` | https://pmc.ncbi.nlm.nih.gov/articles/PMC2628753/ |
| `cimetidine` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=496e258d-a5fd-42da-9a86-73afc8be359b |
| `cimetidine` | `source_2` | https://pubmed.ncbi.nlm.nih.gov/7363531/ |
| `clarithromycin` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=b1bdf526-4f16-4130-b614-4cb678f060d7 |
| `clarithromycin` | `source_2` | https://pubmed.ncbi.nlm.nih.gov/10589373/ |
| `clarithromycin` | `source_3` | https://journals.asm.org/doi/10.1128/aac.01193-08 |
| `dapagliflozin` | `source_1` | https://www.accessdata.fda.gov/drugsatfda_docs/nda/2014/202293Orig1s000ClinPharmR.pdf |
| `efavirenz` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=13ca3456-e5bf-4bb1-af95-b1378658a358 |
| `efavirenz` | `source_2` | https://pubmed.ncbi.nlm.nih.gov/40851704/ |
| `erythromycin` | `source_1` | https://pmc.ncbi.nlm.nih.gov/articles/PMC3581054/ |
| `ethinylestradiol` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=142c4b90-c9ab-45ce-9172-f1ea7d366686 |
| `ethinylestradiol` | `source_2` | https://pmc.ncbi.nlm.nih.gov/articles/PMC4285808/ |
| `felodipine` | `source_1` | https://pubmed.ncbi.nlm.nih.gov/1782737/ |
| `felodipine` | `source_2` | https://pubmed.ncbi.nlm.nih.gov/3327676/ |
| `fluconazole` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=f6e44764-c652-4926-b081-9111c82c7957 |
| `fluvoxamine` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=35b377d9-5b7a-4d8e-b6c1-4291d02f5dae |
| `fluvoxamine` | `source_2` | https://link.springer.com/article/10.2165/00003088-199500291-00003 |
| `fluvoxamine` | `source_3` | https://www.clinpgx.org/pmid/7988100 |
| `fluvoxamine` | `source_4` | https://psychopharmacologyinstitute.com/section/fluvoxamine-essentials-mechanism-of-action-indications-pharmacokinetics-and-dosing-2051-4052/ |
| `fluvoxamine` | `source_5` | https://en.wikipedia.org/wiki/Fluvoxamine |
| `fluvoxamine` | `source_6` | https://www.accessdata.fda.gov/drugsatfda_docs/label/2007/021519lbl.pdf |
| `fluvoxamine` | `source_7` | https://pubmed.ncbi.nlm.nih.gov/9184622/ |
| `fluvoxamine` | `source_8` | https://go.drugbank.com/drugs/DB00176 |
| `inulin` | `source_1` | https://go.drugbank.com/drugs/DB00638 |
| `inulin` | `source_2` | https://www.sciencedirect.com/topics/immunology-and-microbiology/elimination-half-life |
| `inulin` | `source_3` | https://pmc.ncbi.nlm.nih.gov/articles/PMC1873801/ |
| `itraconazole` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=b1274d78-1096-4ae3-8299-a2e94eaa0ea5 |
| `mefenamic_acid` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/fda/fdaDrugXsl.cfm?setid=d0291319-ab3e-20c8-e053-2a95a90afabb |
| `mefenamic_acid` | `source_2` | https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/015034s046lbl.pdf |
| `metoprolol` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=cbc32a80-717b-4cf2-b76a-6d03a3720419 |
| `metoprolol` | `source_2` | https://pubmed.ncbi.nlm.nih.gov/6102500/ |
| `mexiletine` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=ab73778b-6794-441c-b127-610a6d0733ea |
| `mexiletine` | `source_2` | https://pubmed.ncbi.nlm.nih.gov/10589372/ |
| `moclobemide` | `source_1` | https://go.drugbank.com/drugs/DB01171 |
| `moclobemide` | `source_2` | https://pubmed.ncbi.nlm.nih.gov/2248087/ |
| `moclobemide` | `source_3` | https://pubmed.ncbi.nlm.nih.gov/8582117/ |
| `moclobemide` | `source_4` | https://en.wikipedia.org/wiki/Moclobemide |
| `moclobemide` | `source_5` | https://pubmed.ncbi.nlm.nih.gov/3665338/ |
| `montelukast` | `source_1` | https://pubmed.ncbi.nlm.nih.gov/9429741/ |
| `motavizumab_medi_524` | `source_1` | https://pmc.ncbi.nlm.nih.gov/articles/PMC3837853/ |
| `motavizumab_yte` | `source_1` | https://pmc.ncbi.nlm.nih.gov/articles/PMC3837853/ |
| `omeprazole` | `source_1` | https://en.wikipedia.org/wiki/Omeprazole |
| `omeprazole` | `source_2` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=d8b466e0-a35e-4fba-9d43-4e6c0122e7ad |
| `omeprazole` | `source_3` | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=a17e415e-a559-4a8d-a455-699184a01523 |
| `omeprazole` | `source_4` | https://pubmed.ncbi.nlm.nih.gov/2315973/ |
| `raltegravir` | `source_1` | https://pmc.ncbi.nlm.nih.gov/articles/PMC3370715/ |
| `raltegravir` | `source_2` | https://pubmed.ncbi.nlm.nih.gov/21746959/ |
| `sildenafil` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/lookup.cfm?setid=7086e222-0f2b-4c02-84c0-4f8635c90993 |
| `sildenafil` | `source_2` | https://pmc.ncbi.nlm.nih.gov/articles/PMC1874251/ |
| `sildenafil` | `source_3` | https://www.accessdata.fda.gov/drugsatfda_docs/label/2007/020895s027lbl.pdf |
| `sildenafil` | `source_4` | https://en.wikipedia.org/wiki/Sildenafil |
| `sildenafil` | `source_5` | https://go.drugbank.com/drugs/DB00203 |
| `sildenafil` | `source_6` | https://labeling.pfizer.com/ShowLabeling.aspx?id=14610 |
| `sufentanil` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=8b580f3d-e3b5-4086-b093-87a980631147 |
| `tefibazumab` | `source_1` | https://pmc.ncbi.nlm.nih.gov/articles/PMC1610062/ |
| `tizanidine` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=043d9e51-bfa2-4add-9058-5ece332f7e99 |
| `triazolam` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=ce6ddb53-89ca-4edf-a519-553d34ce7938 |
| `triazolam` | `source_2` | https://go.drugbank.com/drugs/DB00897 |
| `triazolam` | `source_3` | https://pmc.ncbi.nlm.nih.gov/articles/PMC1401197/ |
| `verapamil` | `source_1` | https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=c9d71191-b32a-44f9-bc5a-283a06884c82 |
| `verapamil` | `source_2` | https://pubchem.ncbi.nlm.nih.gov/compound/Verapamil |
| `verapamil` | `source_3` | https://pubmed.ncbi.nlm.nih.gov/432439/ |
