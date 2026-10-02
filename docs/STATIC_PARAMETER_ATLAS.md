# パラメータ台帳のGitHub Pagesビルド

[パラメータ台帳](parameters/) は既存の `site/app/page.tsx` と `globals.css` をそのまま使った静的Reactアプリです。検索、経路フィルター、言語切替、薬剤詳細、出典表示はブラウザ内で動作します。詳細リンクは `parameters/#drug=dapagliflozin` のようなhash URLです。

```bash
cd site
npm ci
npm run build:pages
```

Node.jsは `site/package.json` の指定に従ってください。出力先は `docs/parameters/index.html` と `docs/parameters/atlas-assets/` です。既存のパラメータCSVと出典一覧は維持されます。生成済みHTML/CSS/JSをコミットすると、既存のDocs Pagesワークフローで公開されます。

表示データは `site/app/drugs.json` のスナップショットです。薬剤YAMLを更新した場合はリポジトリルートで `python3 tools/build_docs_site.py` を実行し、出典・basis・レビュー状態を確認してから再ビルドしてください。ソースの科学的値はビルド時に推測・補完しません。

以前の表形式ページは[パラメータ値の表](PARAMETERS.md)に残しています。`/parameters/` はアプリ専用、表は `/parameter-values/` です。
