AGENTS.md と docs/CODEX_HARNESS.md を読んでから作業してください。

目的: `INDEX.csv` が `drugs/*/pk.yml` から再生成した内容と一致するか確認してください。

実行:
```bash
make regen-check
```

失敗した場合:
- どの row / column がずれているかを特定する。
- `pk.yml` 側が正しいか、`INDEX.csv` 側が古いかを判断する。
- 更新が必要なら `python3 tools/rebuild_index.py .` を実行し、`make all` まで通す。
