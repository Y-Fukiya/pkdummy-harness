# AGENTS.md

## 目的

このリポジトリは、OSP PBPK Model Library / DailyMed / PubMed などから得た薬物動態（PK）要約を、1-compartment PopPK/mrgsolve 実行用テンプレートへ変換するためのライブラリです。

Codex はこのファイルを作業前に読み、以下の制約を守ってください。

## 守るべき不変条件

- PK 数値は科学データです。推測や丸め直しで値を作らないでください。
- `drugs/<slug>/pk.yml` の `pk_raw`、`sources`、`pk_parsed`、`derived` の対応関係を壊さないでください。
- 経口薬では CL/V が CL/F, V/F（見かけ値）である可能性が高いです。systemic CL/V へ変換する場合は、F と根拠を明示してください。
- 70 kg 成人換算、BSA 1.73 m² 正規化、per-kg 単位の扱いを変更する場合は、テストを追加してください。
- `INDEX.csv`、`EXCLUDED.csv`、`pk_library.yml`、`drugs/*/*.yml` を更新した場合は、何が変わったかを必ず要約してください。
- `__pycache__`、`.DS_Store`、`._*`、一時生成物をコミット対象にしないでください。

## 主要コマンド

```bash
make validate           # ライブラリ整合性 + ハーネス健全性
make test               # pytest による単体テスト
make regen-index-check  # INDEX.csv が rebuild_index.py と一致するか確認
make harness-check      # validate + test + regen-index-check
```

依存関係を入れる場合:

```bash
python3 -m pip install -r requirements.txt
```

## 作業パターン

1. まず `make validate` を実行して、開始時点の状態を確認します。
2. parser / unit conversion / generation logic を変更したら、関連する pytest を追加または更新します。
3. 生成物を更新する前に、可能なら一時ディレクトリで生成して差分を確認します。
4. 最後に `make harness-check` を実行します。
5. 失敗を無視して完了扱いにしないでください。未解決の失敗がある場合は、原因と残タスクを明記してください。

## 変更してよいもの / 注意が必要なもの

- 変更しやすい: `tools/*.py`、`tests/*.py`、`docs/*.md`、`jobs/*.yml`。
- 注意して変更: `drugs/*/pk.yml`、`spec_pk1_*.yml`、`targets.yml`、`INDEX.csv`、`EXCLUDED.csv`。
- 原則変更しない: source URL、raw PK text、既存の薬剤名・slug。ただし明確な誤記修正は可。

## 受け入れ条件

Codex の作業は、原則として以下を満たしたときだけ完了です。

- `make harness-check` が通る。
- PK 数値を変えた場合、元文字列、変換式、単位、前提を説明できる。
- route、CL/V basis、F1 の扱いが `pk.yml`、`targets.yml`、`spec_pk1_*.yml` で矛盾しない。
- 新しい抽出ルールには、最小限の単体テストがある。
