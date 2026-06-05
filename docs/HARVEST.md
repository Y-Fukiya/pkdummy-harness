# Harvest (DailyMed / PubMed) → CL/V extraction → template generation

このリポジトリ(v0.6)では、v0.3の形式（`pk.yml / spec / targets`）を維持したまま、

- **DailyMed (SPL)** からラベルを取得
- **PubMed / PMC**（オープンアクセスがあれば全文XML）からテキスト取得
- テキストから **CL / V / t1/2 / F** を正規表現で抽出
- `drugs/<drug>/` 以下へ **テンプレを自動生成**

を行うスクリプトを追加しました。

v0.8 ではさらに、取りこぼしの原因を**機械可読な理由コード**として `EXCLUDED.csv` に出力し、
理由別の救済（table行 `PKROW:` の直接解析／t1/2からの導出）を自動で試します。

> 重要：論文は**抄録にCL/Vが無い**ことが多く、PMCに全文が無い（=著作権で取得できない）場合は抽出できません。  
> その場合は `jobs.yml` に「確実なソース（PDF/URL）」を追加するか、手で値を入れてください。

## 1) 依存関係

最小限で動かすなら `requests, lxml, pyyaml` が必要です。
`uv` を使うなら例：

```bash
uv run --with requests --with lxml --with pyyaml python tools/harvest_and_generate.py --help
```

PubMed/PMCも使うなら追加は不要です（同じ依存で動きます）。

## 2) jobs.yml 形式

`jobs.yml` は **配列**、または `{jobs: [...]}` 形式。

```yaml
jobs:
  - name: aciclovir
    route: oral        # oral | iv
    dose_mg: 100       # 省略時は --default-dose-mg
    weight_ref_kg_for_abs: 70
    param_basis: auto  # auto | apparent | systemic | any
    dailymed: true     # true なら drug_name で検索して最新っぽいSPLを選びます
    pubmed: false      # PubMed/PMCも回すなら true
```

DailyMedのSETIDを固定したい場合：

```yaml
- name: simvastatin
  route: oral
  dailymed:
    setid: fdbfe194-b845-42c5-bb87-a48118bc72e7
  pubmed: false
```

PubMed側をPMID指定したい場合：

```yaml
- name: rifampin
  route: oral
  pubmed:
    pmid: "12345678"
  dailymed: true
```

検索クエリを指定したい場合：

```yaml
- name: caffeine
  pubmed:
    query: 'caffeine[Title/Abstract] AND (clearance OR "volume of distribution")'
  dailymed: true
```

## 3) 実行

リポジトリ直下で：

```bash
uv run --with requests --with lxml --with pyyaml python tools/harvest_and_generate.py \
  --jobs jobs.yml --repo . --default-dose-mg 100
```

- 成功すると `drugs/<slug>/pk.yml`, `spec_*.yml`, `targets.yml` が生成されます
- 成果は `reports/harvest_report.json` に出ます

### 3.1) `EXCLUDED.csv`（取りこぼし一覧）

`clearance` / `volume` が埋まらなかった、または生成に失敗した薬剤は、リポジトリ直下の
`EXCLUDED.csv` に行として出力されます。

列:

- `drug`, `slug`, `route_inferred`, `status`, `missing`
- `reason`: `;` 区切りの理由コード（例: `MISSING_CLEARANCE;CLEARANCE_KEYWORDS_BUT_NO_CANDIDATES;PUBMED_ABSTRACT_ONLY`）
- `reason_json`: 詳細（sources / pk / diagnostics / codes）を JSON 文字列で格納
- `remediation_hint`: 機械的な対処ヒント

生成後に `INDEX.csv` を更新するには：

```bash
python tools/rebuild_index.py
```

## 4) 抽出ロジックの注意点（重要）

- DailyMedはSPL XMLの `CLINICAL PHARMACOLOGY` / `PHARMACOKINETICS` などのセクションを優先してテキスト化し、そこから抽出します
  - v0.5 から **tableを行単位で整形**して付加し、値+単位が崩れにくくなりました
  - v0.6 から **表のヘッダ推定（列名→単位列の対応）**を軽量に行い、`PKROW: Clearance 5.2 L/h` のような“抽出向け正規化行”を追加します
  - v0.8 から **`PKROW:` を直接パースする救済パス**を追加し、フラット化された表で正規表現が外れるケースを拾いやすくしています
  - v0.8 から **t1/2 と片方(CL/V)が取れたときに、もう片方を導出**する救済パスを追加しています（`ke=ln2/t1/2` を仮定）
  - v0.5 から **PKセクション→全セクション**の2段階抽出で、CL/Vが別セクションにあるケースを拾いやすくしています
- CL/Vの単位はできる範囲で `L/h` or `L/h/kg`, `L` or `L/kg` へ変換します
  - 変換した場合は `pk.yml:derived.notes` に記録されます
- **oralのCL/VはCL/F, V/Fとして載っていることが多い**ため、テンプレ生成では `theta.F1=1.0` をデフォルトにしています
  - もしソースが「systemic CL/V」と明確なら、`theta.F1` と `CL/V` を自分で整合させてください
  - v0.6 では `param_basis` により **CL と CL/F（V と V/F）の優先順位**を指定できます
    - `auto` (デフォルト): `route: oral` → apparent（CL/F, V/F）を優先 / `route: iv` → systemic（CL, V）を優先
    - `apparent`: 常に CL/F, V/F を優先（両方あるとき）
    - `systemic`: 常に CL, V を優先（両方あるとき）
    - `any`: 優先なし（距離やセクション重みで選択）

## 5) うまくいかない時の定石

- `reports/harvest_report.json` で `missing: ["clearance"]` 等になっている → ソースにCL/Vが書かれていません
  - v0.8 では `reason_codes` と `EXCLUDED.csv:reason_json` に「なぜ拾えなかったか」が残ります
  - DailyMedの別SETIDを試す（brand/genericで差がある）
  - PubMed/PMCの別論文（PMCIDがあるもの）を指定する
  - それでも無理なら手入力（その方が早いケースが多い）


## 5) いちばん速い実行フロー（"除外22"だけ回す）

v0.1相当の「15 selected / 22 excluded」を **all_pk_parameters_combined.csv から再現**し、
除外22薬剤だけを harvest にかける最短手順です。

### 5.1 jobs.yml を作る（除外22）
```bash
python tools/make_jobs_from_csv_v01.py --in all_pk_parameters_combined.csv --out jobs_excluded22.yml
```

生成された `jobs_excluded22.yml` をそのまま使うか、既に用意済みの
`jobs/jobs_excluded22_v01.yml` を使ってOKです。

### 5.2 harvest → EXCLUDED集計 → 次の改善ポイント抽出
```bash
uv run --with requests --with lxml --with pyyaml python tools/harvest_and_generate.py \
  --jobs jobs_excluded22.yml --repo . --default-dose-mg 100

python tools/rebuild_index.py

python tools/summarize_excluded.py --excluded EXCLUDED.csv --out-md reports/excluded_summary.md
```

- `EXCLUDED.csv` には **理由コード（reason）** と **詳細JSON（reason_json）** が入ります
- `reports/excluded_summary.md` に **理由コード集計** と **次のパーサ強化候補** がまとまります


### 5.3 ワンショットで回す
```bash
python tools/run_excluded22_flow.py --csv all_pk_parameters_combined.csv --repo .
```
