# README-only Acceptance Test

この文書は、第三者がREADMEだけを起点にして、このハーネスを安全に動かせるかを確認するための受け入れテストです。

目的は、Phoenix / NONMEM / nlmixr2 本体の正式validationではなく、**同じrepo内で synthetic PK fixture workflow が再現でき、施設依存の差分を設定として確認できること** を示すことです。

## 1. Fresh Setup

```bash
python3 -m pip install -r requirements.txt
make validate
```

期待結果:

- `validate_library.py` が通る
- `codex_harness_check.py` が通る
- 必須ファイル、薬剤library、example、docsが見つかる

## 2. Full Repository Check

```bash
make acceptance-check
```

このtargetは次を実行します。

| Step | Purpose |
| --- | --- |
| `make harness-check` | library整合性、pytest、index再現性、example再生成、下流smoke、site adapter smokeを確認 |
| `make doctor` | Python/R/Quarto/simPopなどのローカル環境を確認 |
| `python3 -m tools.pk_fixture_cli doctor --json` | standalone CLI入口がpreflightへ正しくdispatchできることを確認 |

`doctor` では任意依存の不足が `WARN` になることがあります。QuartoやsimPopがない場合でも、CLI本体とCSV fixture生成が通ればハーネスの中核は利用できます。

editable install後は次の形でも同じ入口を使えます。

```bash
pk-fixture doctor
pk-fixture run harness_examples/demo_set.yml
```

## 3. Downstream Tool Boundary

外部ツール本体がある施設では、次のprofileを施設環境に合わせて編集します。

```text
external_validation/tool_profiles.yml
```

確認コマンド:

```bash
python3 tools/run_external_tool_validation.py \
  --downstream-dir outputs/downstream_smoke_check/minimal_aciclovir \
  --out-dir outputs/external_validation_probe/minimal_aciclovir
```

実行環境がある場合だけ `--execute` を付けます。

```bash
python3 tools/run_external_tool_validation.py \
  --downstream-dir outputs/downstream_smoke_check/minimal_aciclovir \
  --out-dir outputs/external_validation_probe/minimal_aciclovir \
  --tools nonmem,nlmixr2 \
  --execute
```

解釈:

| Result | Meaning |
| --- | --- |
| `OK` | profileのコマンド確認、または任意実行が通った |
| `WARN` | toolが見つからない、任意profileが未設定、または実行結果に確認事項がある |
| `FAILED` | required profileや実行に必要なartifactが壊れている |

Phoenix / NONMEM / nlmixr2 のライセンス、インストール、実project/control streamはこのrepoに同梱しません。

## 4. Site-specific Dataset Mapping

施設ごとの列名や必須列は、次のtemplateをコピーして調整します。

```text
external_validation/site_adapter_template.yml
```

確認コマンド:

```bash
python3 tools/make_site_adapters.py \
  --analysis-dir examples/minimal_aciclovir/workflow/analysis_inputs \
  --spec-yml external_validation/site_adapter_template.yml \
  --out-dir outputs/site_adapter_check/minimal_aciclovir
```

出力:

```text
outputs/site_adapter_check/minimal_aciclovir/
  site_nca_example.csv
  site_poppk_example.csv
  SITE_ADAPTER_MANIFEST.yml
```

このadapterは、施設ごとのNCA/PopPK dataset仕様に合わせるためのCSV変換層です。submission-ready ADaM、正式Phoenix dataset、正式NONMEM datasetを保証するものではありません。

## 5. Pass Criteria

受け入れOKと考えてよい状態:

- `make acceptance-check` が通る
- `python3 -m tools.pk_fixture_cli --help` で主要commandが表示される
- `external_validation/tool_profiles.yml` に、施設で使う外部コマンド名と実行方針が書ける
- `external_validation/site_adapter_template.yml` をコピーして、施設の列名・必須列に合わせたCSVを作れる
- `SITE_ADAPTER_MANIFEST.yml`, `DOWNSTREAM_SMOKE_MANIFEST.yml`, `EXTERNAL_TOOL_VALIDATION.yml` で `OK/WARN/FAILED` の理由を確認できる

まだ施設側validationとして残るもの:

- 実Phoenix projectでの取り込み確認
- 実NONMEM環境での `nmfe75` などのコマンド名、control stream、`.lst` 出力確認
- 実nlmixr2 package環境でのparser/estimation確認
- 施設ごとのADaM/NCA/PopPK dataset仕様への最終調整
- READMEだけで第三者が実行したときの観察メモ

これらはこのrepo内で設定・記録できますが、外部ソフトウェア本体や施設SOPの代替にはしません。
