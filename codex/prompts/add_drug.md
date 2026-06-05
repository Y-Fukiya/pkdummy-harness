AGENTS.md と docs/CODEX_HARNESS.md を読んでから作業してください。

目的: 新しい薬剤をテンプレート候補として追加してください。

手順:
1. source URL と raw PK text を必ず残す。
2. route は `po` または `iv` に正規化する。
3. 経口薬の CL/V は、根拠がない限り apparent CL/F, V/F として扱う。
4. 生成後に `python3 tools/rebuild_index.py .` を実行する。
5. `make all` を実行する。
6. 変更した PK 値、単位変換、前提を要約する。
