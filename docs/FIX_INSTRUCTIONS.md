# Fix Instructions: PK Fixture Harness Review (Review-driven)

この文書は、レビュー指摘を **Codex/エージェントがそのまま実装できる粒度** に落とし込んだ作業指示です。  
重大度順（実害が高い順）で並べています。  

## 目標と方針

- まず P1（IV注入配線）を完了して、明確な数理的誤差のある経路を止める
- 次に P2, P3 で検証ロジックの意味を正し、誤解を防ぐ
- 次点として P4 は fixture の用途に応じて実装可否を判断
- P5～P9 は仕様明文化を中心に最小変更で実施

受け入れ条件は各項目末尾の `Acceptance` に従うこと。

## 実施順と修正指示

### P1 (P0 相当): IV 注入（infusion_h）をエンジンに配線する

- 優先度: 最高
- 対象: `tools/run_demo_set.py`（`_concentration_ng_ml`, `make_demo_sim_full`）, `tools/make_analysis_inputs.py`（`_make_poppk` の `RATE`）
- 現状:
  - `route: iv` + `infusion_h: 1.0` の定義が無視され、すべて即時 bolus で計算される
  - その結果、albuterol で Tmax=0、Cmax 過大など、IV注入系が壊れる
- 指示:
  - `regimen.arms[arm].infusion_h` を読む（未指定は 0）
  - `route in {iv, iv_infusion}` かつ `infusion_h > 0` のときのみ注入式を使用
  - 注入中 (0 < t ≤ Tinf):
    - `C = Dose/(CL * Tinf) * (1 - exp(-ke*t)) * mult`
  - 注入後 (t > Tinf):
    - `C = Dose/(CL * Tinf) * (1 - exp(-ke*Tinf)) * exp(-ke*(t-Tinf)) * mult`
  - `infusion_h` 未指定/0 の IV は既存 bolus 経路を維持
  - PopPK 入力の投与行は注入時 `RATE = Dose/Tinf` を設定
  - 観測行は現行 `Time` と整合（現状 RATE=0 を条件分岐して上書き）
- Acceptance:
  - albuterol で `Tmax ≈ infusion_h (1h)`、`Cmax < bolus C0 = Dose / V` を満たす
  - IV注入薬の λz/AUC が注入後相（吸収終期）で算出される
  - `iv_bolus` 系既存テストが変更なしで通る
- 備考: 実害が明確なので最優先で完了する

### P2: t½ と CL/V の構造的矛盾を明示的に切り分ける

- 優先度: 高
- 対象: `drugs/*/targets.yml`, `drugs/*/spec_pk1_*.yml`, `README.md`, `USER_GUIDE.md`
- 現状:
  - validate_library で 13/36 薬剤に矛盾警告
  - demo sim は CL/V を使って計算するため、警告薬は validate_simulation でも WARN/FAIL し得る
- 指示:
  - 薬剤ごとに「採用する独立パラメータ対」を明記（例: CL/V, V/F 由来を採るか、t1/2 由来を採るか）
  - 非物理的整合の既知ケースは `targets.yml`/`README`（or drug の notes）へラベル化（例: abciximab）
  - そのうえで `targets` と `spec_pk1_*` の文言を相互一貫にする
- Acceptance:
  - 各薬剤で採用パラメータ対が明記される
  - `t1/2` の不整合が「既知か否か」明記される
  - FAIL 予定薬がストレステスト用途であることが判別可能

### P3: AUC ターゲットの循環参照性を明記する

- 優先度: 高
- 対象: `drugs/*/targets.yml`（notes）, `docs/SCHEMA.md`
- 現状:
  - `targets.auc = Dose/CL` で設定されるケースがあり、生物学的独立測定値ではない
- 指示:
  - 該当 entries の notes へ「AUC は Dose/CL 由来の積分整合性指標であり、生体内妥当性の独立検証ではない」旨を追記
  - 文献AUCでの検証に切替える場合の 1 行手順を追加
- Acceptance:
  - AUC が pass でも臨床妥当性の証拠にならないことが文書上明示される
  - 書き換え導線（差し替え手順）が読める

### P4: BLQ / LLOQ を fixture 仕様で追加する（任意）

- 優先度: 中
- 対象: `tools/run_demo_set.py`, `tools/make_sdtm_like_domains.py`, `tools/make_analysis_inputs.py`, spec schema
- 現状: LLOQ / BLQ のフラグが未実装、M3等の経路未検証
- 指示:
  - spec に任意 `lloq` を追加（空欄は既存動作）
  - `DV < lloq` を BLQ と判定して:
    - NCA: BLFL / PCSTAT に反映
    - PopPK: MDV または M3 前段フラグへ反映
- Acceptance:
  - LLOQ 設定薬で末梢相に BLQ 行が生成される
  - 下流の BLQ ハンドリングが起動する（少なくとも fixture として BLQ 行が観測可能）
- 方針: 「NCA/PopPK検証用 fixture」として必要なら必須化、smoke-test止まりなら見送り

### P5: iiv/residual は demo エンジン非消費であることを明記

- 優先度: 中
- 対象: `USER_GUIDE.md`
- 現状: 外部ランナー向け仕様と混在し誤解の可能性
- 指示:
  - USER_GUIDE に、demo エンジンは theta のみ消費で、`iiv`/`residual` は外部 mrgsolve 実行時に有効化されることを明記
  - 将来実装時の注意（`iiv`=ω² への変換、CV 解釈）を追記
- Acceptance:
  - 説明だけで demo 単体実行と外部ランナーの差が明確に理解できる

### P6: predose 観測規約（`DV=0/MDV=0`）を明文化し、必要なら分岐追加

- 優先度: 中
- 対象: `USER_GUIDE.md`、必要なら CLI（`--predose-mdv1`）
- 現状: predose=0 の扱いは明示不足
- 指示:
  - 文書で `predose` 観測を `DV=0/MDV=0` とする規約を明記
  - 希望時は `--predose-mdv1` オプションで `MDV=1` に切替える分岐を検討
  - `aciclovir` は `ALAG1=0.5, F1=1.0` の既存設定で正当
- Acceptance:
  - 規約がドキュメント上で明確化される
  - 実装追加時は `MDV=1` 分岐の挙動が再現可能

### P7: 共変量・吸収パラメータの利用範囲を明記

- 優先度: 中〜低
- 対象: `USER_GUIDE.md`, `README.md`
- 現状:
  - WT/AGE/SEX/CREAT など人口統計は PK 式には未接続
  - 吸収パラメータ `KA` は全薬剤固定など簡略実装
- 指示:
  - 「共変量モデル・吸収多様性検証には使わない」用途境界を明記
  - より実データに近い母集団を作る場合は `subjects_csv` / `simpop` 経路推奨を追記
- Acceptance:
  - 誤用途リスクを避けるため、README/ガイド側で用途境界が明示される

### P8: SC/IM 経路対応の明示的ガード

- 優先度: 低
- 対象: `tools/run_demo_set.py`（経路判定ロジック）、`_is_oral` 判定
- 現状: `_is_oral` 以外は bolus になるため、SC/IM 将来追加時に吸収相が消失
- 指示:
  - `_is_oral` 判定を oral/po/sc/im を吸収あり経路として一般化、または未対応経路には明示エラー/WARN
  - 今回対象薬剤に SC/IM が無い場合は「将来対応」扱いでの明文化でも可
- Acceptance:
  - SC/IM 追加時の実害リスクが設計で抑止される

### P9: 補間・ソートの意図をコメント化

- 優先度: 低
- 対象: `tools/sample_clinical_timepoints.py`
- 現状:
  - `_merge_row` で線形補間を使用
  - `sort` キー `(len(v), v)` が実装意図的か判別しづらい
- 指示:
  - 終末相の上振れ等の注意点を軽く明記
  - log-linear 補間はオプション検討（導入時は既定変更なし）
  - ソート式はコメントで意図を記録（仕様変更がない場合はバグ指摘を止める）
- Acceptance:
  - 修正意図と副作用がドキュメント化される

## 実行管理（Codex/エージェント運用用）

- 各項目は `status`（`pending` / `in_progress` / `done` / `deferred`）で管理
- PR/コミット時は対象ファイル・テスト有無・受け入れ基準充足を添付
- P1完了後に P2/P3、次点で P4〜P9 の順で進める
- 目的外利用（臨床妥当性の直接保証）への誤解を避けるため、都度 `notes` に意図と境界を記録する

