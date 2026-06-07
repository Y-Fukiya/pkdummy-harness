# Site Adapter Guide

この文書は、施設ごとのADaM/NCA/PopPK dataset仕様へCSV列を合わせるための手順です。

基本template:

```text
external_validation/site_adapter_template.yml
```

site adapterはfacility-specificな列名、固定値、必須非欠損列を定義する薄い変換層です。submission-ready ADaM、正式Phoenix dataset、正式NONMEM datasetを保証するものではありません。

## Mapping fields

| Field | Meaning |
| --- | --- |
| `source` | `ADPC`, `NCA_INPUT`, `POPPK_INPUT` のどれを入力にするか |
| `output` | 生成するCSVファイル名 |
| `columns.name` | 出力列名 |
| `columns.source` | 入力列名 |
| `columns.value` | 固定値 |
| `required_nonblank` | 出力後に空欄を許さない列 |

## Review workflow

1. `external_validation/site_adapter_template.yml` を施設用にコピーする。
2. Phoenix / NONMEM / nlmixr2 など、実際の下流toolに合わせて列名を調整する。
3. `required_nonblank` に施設で必須の列を入れる。
4. `tools/make_site_adapters.py` を実行する。
5. `SITE_ADAPTER_MANIFEST.yml` で入力、出力、行数、警告を確認する。
6. 取り込み確認結果を施設側validation noteに残す。

実行例:

```bash
python tools/make_site_adapters.py \
  --analysis-dir examples/minimal_aciclovir/workflow/analysis_inputs \
  --spec-yml external_validation/site_adapter_template.yml \
  --out-dir outputs/site_adapter_check/minimal_aciclovir
```

## Minimum review checklist

| Check | Expected |
| --- | --- |
| Subject ID | 施設側のsubject keyと一致 |
| Time | NCA/PopPK toolが期待する単位、列名 |
| Concentration | 単位列と値列が揃っている |
| Dose | 投与行と濃度行の関係が説明できる |
| CMT/EVID/MDV | NONMEM/nlmixr2側control streamと一致 |
| Manifest | `SITE_ADAPTER_MANIFEST.yml` が残る |

site adapterは最後の列調整を見える化するためのものです。臨床薬理モデル妥当化や規制提出用validated datasetの代替ではありません。
