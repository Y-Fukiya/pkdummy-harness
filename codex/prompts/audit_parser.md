AGENTS.md と docs/CODEX_HARNESS.md を読んでから作業してください。

目的: parser / unit conversion の安全性を監査してください。

対象:
- tools/pk_extract.py
- tools/pk_units.py
- tests/test_pk_extract.py
- tests/test_pk_units.py

条件:
- checked-in の `drugs/*/*.yml` は、根拠のある再生成なしに変更しない。
- 単位変換を修正したら、同じ単位の再発防止テストを追加する。
- `make all` を実行する。
- PK 値の臨床妥当性は判断せず、抽出・変換・整合性の問題だけ報告する。
