# CDISC Dataset Generator APIの補助利用

`tools/fetch_cdisc_reference.py` は、[CDISC Dataset Generator API](https://cdiscdataset.com/api-docs) からDM/EXのCSVを取得し、列構造を確認するための任意アダプタです。

```bash
python tools/fetch_cdisc_reference.py \
  --out-dir outputs/cdisc_reference/cardio_50 \
  --domains DM,EX \
  --num-subjects 50 \
  --therapeutic-area Cardiology
```

出力は `DM.csv`、`EX.csv`、`CDISC_API_MANIFEST.yml` です。manifestにはリクエスト条件、取得URL、行数、症例数、SHA-256が記録されます。

## 本ハーネスとの境界

このアダプタは `run_harness.py` の必須経路には接続していません。PKデモの正本は次のローカル経路です。

```text
pkdummy analytical_demo → sim_full.csv → clinical_samples.csv → DM / EX / PC
```

特にPC濃度は、同じシミュレーションから作られた `pkdummy` のPCを使います。APIから取得したDM/EXを、PK濃度と自動結合したり、既存のDM/EXを上書きしたりしません。APIのEXは複数投与・異なる投与時点を含むことがあるため、今回の単回投与PK fixtureにそのまま流用すると、投与条件と濃度が不整合になる可能性があります。

## 利用上の注意

- APIが取得できない場合でも、`harness_examples/demo_dm_ex_pc_50.yml` によるローカル生成は実行できます。
- APIのレスポンスはランダム生成のため、再現可能なテストの正本にはしません。必要な比較fixtureは取得後にSHA-256とともに保存します。
- 現行サービスのダウンロードURLは `/download/...` ですが、ドキュメントには `/api/download/...` の記載もあるため、アダプタは相対URLをサービスのoriginに解決します。
- 取得データは教育・研究用の参照fixtureです。申請用SDTM適合性やCDISC公式認証を意味しません。
- 実患者データや機密情報をAPIへ送信しないでください。このアダプタは生成リクエストだけを行います。
