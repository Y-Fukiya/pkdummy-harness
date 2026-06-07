# Downstream E2E Smoke Checks

この文書は、`analysis_inputs/` から NCA / PopPK 側へ最低限つながるかを確認するための smoke check を説明します。

これは **Phoenix, NONMEM, nlmixr2 の正式検証ではありません**。目的は、fixture CSVが下流parser、簡易NCA計算、PopPK control/template作成まで破綻しないことを早く確認することです。

## Command

```bash
python3 tools/run_downstream_smoke.py \
  --analysis-dir outputs/<run>/workflow/analysis_inputs \
  --out-dir outputs/<run>/workflow/downstream_smoke
```

`make harness-check` では、versioned examplesに対してこのsmoke checkと外部validation profileのprobeを実行します。

```bash
make downstream-check
make external-validation-probe
```

## What It Does

```mermaid
flowchart LR
    A["analysis_inputs/ADPC.csv"] --> B["make_downstream_adapters.py"]
    A --> C["simple NCA smoke"]
    D["analysis_inputs/POPPK_INPUT.csv"] --> B
    D --> E["PopPK parser smoke"]
    B --> F["validate_downstream_adapters.py"]
    C --> G["NCA_SUMMARY.csv"]
    E --> H["NONMEM / nlmixr2 parser templates"]
    F --> I["DOWNSTREAM_SMOKE_MANIFEST.yml"]
    G --> I
    H --> I
```

## Outputs

| Output | Meaning |
| --- | --- |
| `adapters/` | R NCA / Phoenix-like / NONMEM-like / nlmixr2-like adapter CSVs |
| `nca_smoke/NCA_SUMMARY.csv` | simple linear-trapezoidal `CMAX`, `TMAX_H`, `AUCLAST` summary |
| `poppk_smoke/POPPK_PARSE_SUMMARY.yml` | dose/observation row counts and parser readiness checks |
| `poppk_smoke/nonmem_parser_template.ctl` | NONMEM parser smoke control template |
| `poppk_smoke/nlmixr2_parser_template.R` | nlmixr2 parser smoke model template |
| `DOWNSTREAM_SMOKE_MANIFEST.yml` | status, counts, warnings, limitations |

## Interpretation

| Status | Meaning |
| --- | --- |
| `OK` | Adapter CSVs have expected columns and simple NCA/PopPK parser smoke checks pass |
| `WARN` | Outputs were generated but some rows or summaries need review |
| `FAILED` | Adapter contract or required parser-ready structure is broken |

## Boundary

This check improves workflow confidence, but it does not replace:

- Phoenix project validation
- NONMEM execution
- nlmixr2 estimation
- model-specific dataset requirements
- clinical pharmacology validation

For formal tool use, treat the generated files as **starting fixtures** and add tool/project-specific control files, metadata, and validation outside this harness.

## Optional External Tool Validation In This Repo

Phoenix / NONMEM / nlmixr2 の実行環境がある場合は、同じリポジトリ内の optional validation layer から呼べます。

```bash
python3 tools/run_external_tool_validation.py \
  --profile-yml external_validation/tool_profiles.yml \
  --downstream-dir outputs/<run>/workflow/downstream_smoke \
  --out-dir outputs/<run>/workflow/external_tool_validation \
  --tools nonmem,nlmixr2 \
  --execute
```

`--execute` を付けない場合は、実行せずにコマンド存在確認だけ行います。

```bash
python3 tools/run_external_tool_validation.py \
  --downstream-dir outputs/<run>/workflow/downstream_smoke \
  --out-dir outputs/<run>/workflow/external_tool_validation
```

既定profileは [external_validation/tool_profiles.yml](../external_validation/tool_profiles.yml) です。

| Profile | Default behavior |
| --- | --- |
| `phoenix` | placeholder。各施設のPhoenix automation commandに置き換えて使う |
| `nonmem` | `nmfe75` と生成済み `nonmem_parser_template.ctl` を使う想定 |
| `nlmixr2` | `Rscript` から `nlmixr2` packageと生成済みtemplateを読む |

出力:

```text
EXTERNAL_TOOL_VALIDATION.yml
<tool>/stdout.log
<tool>/stderr.log
```

このlayerは同じrepoにありますが、外部ツール本体やライセンスは同梱しません。CIや通常の `make harness-check` では外部ツール実行を必須にしません。
