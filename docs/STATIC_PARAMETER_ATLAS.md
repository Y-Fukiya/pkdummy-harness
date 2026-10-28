# パラメータ台帳のGitHub Pagesビルド

[パラメータ台帳](parameters/) は既存の `site/app/page.tsx` と `globals.css` をそのまま使った静的Reactアプリです。検索、経路フィルター、言語切替、薬剤詳細、出典表示はブラウザ内で動作します。詳細リンクは `parameters/#drug=dapagliflozin` のようなhash URLです。

```bash
cd site
npm ci
npm run build:pages
```

Node.jsは `site/package.json` の指定に従ってください。出力先は `docs/parameters/index.html` と `docs/parameters/atlas-assets/` です。既存のパラメータCSVと出典一覧は維持されます。生成済みHTML/CSS/JSをコミットすると、既存のDocs Pagesワークフローで公開されます。

表示データは `site/app/drugs.json` のスナップショットです。薬剤YAMLを更新した場合はリポジトリルートで `python3 tools/build_docs_site.py` を実行し、出典・basis・レビュー状態を確認してから再ビルドしてください。ソースの科学的値はビルド時に推測・補完しません。

保留理由、修正記録、原典に基づく制約の日本語訳は `docs/fixture-context-i18n.yml` に保持します。各訳文の `en` は薬剤YAMLの英語原文と完全一致する必要があります。ビルドでは全件の対応、順序、制約コード、空欄を検査し、原文の変更や未訳を検出すると停止します。原文を更新するときは対応する日本語訳も更新してください。日本語・英語とも省略せず全文を表示します。

翻訳は画面表示専用です。元の英語フィールドと、生成CSV・マニフェストの臨床的位置づけは変更しません。フェロジピンの血漿CLの候補と採用上の制約は、[原典照合記録](research/2026-10-28-felodipine-label-review.md)を参照してください。この照合ではパラメータと保留判定を変更していません。

以前の表形式ページは[パラメータ値の表](PARAMETERS.md)に残しています。`/parameters/` はアプリ専用、表は `/parameter-values/` です。

最新監査の判定・理由・対応・出典は `docs/research/2026-10-02-all-drug-audit/all-drug-audit.json` をビルド時に直接読み込みます。監査JSONを更新した場合も `npm run build:pages` でHTML/JSを再生成し、生成物を公開してください。数値のfixture台帳と監査判定は別の情報として表示します。
