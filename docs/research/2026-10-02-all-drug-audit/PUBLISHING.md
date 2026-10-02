# GitHub掲載範囲と検証対象

掲載日: 2026-10-02。

今回のコミットはこの監査ディレクトリのみを追加する。薬剤データ、実装、既存の未コミット変更は含まない。

## 監査を実施した入力

- 元のcheckoutのHEAD: `55b3a840d2d5e5931b63a1dcd54b5549c708ac27`。
- 監査した111 YAMLのうち73ファイルは、このHEADと異なる既存のローカル変更を含む。対象は `input-manifest.json` のSHA-256で特定する。
- 実装・tests・Makefileにも既存のローカル変更があった。監査時の1002テスト（701成功・301スキップ）を、GitHub掲載先commit単体の試験結果として扱わない。
- 元の入力snapshotを同梱していないため、GitHubのfresh cloneだけでは `audit_internal.py` のhash照合は通らない。この停止は別の入力に監査結果を誤適用しないためのもの。
- 保存済み監査結果の再集計は `python3 docs/research/2026-10-02-all-drug-audit/consolidate.py` で行える。原典の新たな検証や入力snapshotの復元は行わない。

## 掲載前に別途実施した検証

最新の`origin/main`（`903bfae4326ed996f1bed7604a3b65048cb06cfc`）を分離したworktreeに取り出し、監査成果物だけを追加した。

- `make validate`: 終了コード0。掲載先canonicalの既存半減期警告は13薬剤。監査対象snapshotの11警告とは異なる。
- Python3.12.2で `make harness-check`: 終了コード0。
- pytest: **242件、241成功、1スキップ、失敗0**。スキップはPKNCA/rpy2の差分比較。
- 外部ツール検証は`execute=false`。nlmixr2はprobeのみ、NONMEM/Phoenix実行ファイルなし。
- [公開用harnessログ](publish-harness-check.log) / [公開用pytest XML](publish-test-results.xml)。これらは同ディレクトリ内の監査時ログと区別する。

認証情報パターンの混入、ディレクトリ外の未追跡文書へのリンク、ファイル件数、CSV/JSONの37薬剤・148項目、差分空白を確認。原文全文や一時venvはコミットしない。

Git掲載用に生成CSVの改行をLFへ統一し、ログ/XML等の行末空白を除去した。CSVの解析結果とテスト件数は変更していない。原典取得ファイルのSHA-256は取得原文のものを保持する。
