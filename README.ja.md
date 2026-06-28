# pkdummy-harness

*[English](README.md) | 日本語*

[![CI](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/codeql.yml/badge.svg)](https://github.com/Y-Fukiya/pkdummy-harness/actions/workflows/codeql.yml)
[![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

本リポジトリは、PK workflow 用の deterministic fixture harness です。
目的は、データ整形、ワークフロー実行、manifest 生成、下流ツール連携の
テストであり、PK値の真値ライブラリ、臨床判断、投与設計、規制申請用の
検証パッケージではありません。

1-compartment の簡易モデルから、構造的に整合した SDTM/ADaM/NCA/PopPK の
*ワークフロー fixture* を生成します。用途は**下流ツールの構築とテスト**です。

本リポジトリでは、主要なPK fixture parameter について value-level
provenance metadata を保持します。これは、値の出典、単位正規化、
変換方法、reviewer status を追跡するためのものです。
これは臨床的なPK真値ライブラリ化を意味しません。deterministic workflow
fixture としての監査性を高めるための情報です。

> **設計上、安全:** 患者データなし・IP なし・完全に決定論的で再現可能。
> この境界こそが目的です（後述の「使うべきでない用途」を参照）。

---

## なぜ存在するか

SDTM → ADaM → NCA/PopPK のパイプライン検証には「形」が現実的な入力が要りますが、
実患者データはプライバシー・IP の制約があり入手も遅い。`pkdummy-harness` は、
正しい構造ともっともらしい PK 形状を持つ fixture を、1セットの入力から
バイト単位で再現可能に生成します。

- 入力1セットから SDTM/ADaM 風の中間データを再現性高く生成
- 生成データに対する AUC/Cmax/Tmax/t1/2 の再計算チェックを内蔵
- NCA / PopPK につなぐ薄い adapter CSV をまとめて生成
- `pk.yml` / `targets.yml` は**自動で書き換えない**。manifest と trace ログで監査可能
- 既存施設のデータ形式（DM/LB/VS/PC）にも対応

典型用途: 下流パーサや conformance エンジンの入力 fixture、CI の固定入力・
スモークテスト、データ機微のないデモ／オンボーディング。

---

## どういうデータを作る？

- 薬剤の PK パラメータ: `drugs/<slug>/pk.yml`
- 目標値（AUC/t1/2 など）: `drugs/<slug>/targets.yml`
- 1-compartment の簡易シミュレーション仕様: `drugs/<slug>/spec_pk1_*.yml`
- 実行定義: `harness_examples/*.yml`

フロー図: [docs/assets/pk-harness-process.drawio](docs/assets/pk-harness-process.drawio)、
末端まで含めた全体 [docs/assets/pk-fixture-end-to-end-workflow.drawio](docs/assets/pk-fixture-end-to-end-workflow.drawio)、
読み方は [docs/PROCESS_FLOW.md](docs/PROCESS_FLOW.md)。

---

## まず実行してみる（最短）

このツールは **git チェックアウト前提**で使います（PyPI 配布なし）。クローンして
依存を入れ、**リポジトリのルートで** `make` か `python -m tools.pk_fixture_cli` で実行します。

```bash
python3 -m pip install -r requirements-dev.txt   # コア(PyYAML)+pytest
make harness-check
```

```bash
python3 -m tools.pk_fixture_cli doctor
python3 -m tools.pk_fixture_cli run harness_examples/demo_set.yml
```

コアのランタイム依存は PyYAML のみ。一部ツールは extras で追加します:
`pip install .[harvest]`（Web採取: DailyMed/PubMed）、
`pip install .[jobs]`（ジョブ/除外 CSV ユーティリティ）。

> 配布 wheel/sdist には `tools/` のコードのみが含まれ、薬剤ライブラリ
> （`drugs/`、`pk_library.yml`、`templates/` ほか）は**非同梱**です。素の
> `pip install` 後は実行対象データがありません。`pip install -e .`（editable）は
> チェックアウト内のデータを参照するため動作します。いずれもルートから実行してください。

外部 mrgsolve の `sim_full.csv` がある場合は後段処理:

```bash
python3 tools/run_workflow.py \
  --sim-full outputs/<run>/raw/sim_full.csv \
  --drug <slug> \
  --times 0,0.5,1,2,4,8,12,24 \
  --out-dir outputs/<run>/workflow
```

`run_workflow.py` は既存採血時点用の `--schedule-csv`、既存 DM/LB/VS/PC skeleton 用の
`--dm-csv/--vs-csv/--lb-csv/--pc-csv` も受け付けます。

---

## 出力イメージ

```text
outputs/<run>/workflow/
  MANIFEST.yml
  trace.log
  raw/clinical_samples.csv
  reports/simulation_validation.md
  reports/pk_fixture_report/REPORT.md
  sdtm_like/{DM,VS,LB,EX,PC}.csv
  analysis_inputs/{ADPC,NCA_INPUT,POPPK_INPUT}.csv
  adapters/*.csv
```

### サンプル: 小分子（時間スケール）

`examples/minimal_aciclovir/workflow/analysis_inputs/ADPC.csv`:

```csv
STUDYID,USUBJID,PARAMCD,AVAL,AVALU,TIME_H,MDV,BLQ,EXTRT,DOSE_MG,ROUTE
EXAMPLE,EXAMPLE-001,CONC,0,ng/mL,0,0,0,ACICLOVIR,100,ORAL
EXAMPLE,EXAMPLE-001,CONC,950,ng/mL,1,0,0,ACICLOVIR,100,ORAL
```

### サンプル: 生物製剤 / mAb（days〜weeks スケール）

`examples/minimal_cda1_mab_iv/` は長半減期モノクローナル抗体 fixture
（CDA1、fixture 終末相 t1/2 ≈ 24 日）。終末相の緩やかな減衰が見えるよう 84 日まで採血:

```csv
STUDYID,USUBJID,PARAMCD,AVAL,AVALU,TIME_H,MDV,BLQ,EXTRT,DOSE_MG,ROUTE
OSP_cda1,OSP_cda1-001,CONC,20408.163265,ng/mL,0,0,0,CDA1,100,INTRAVENOUS
OSP_cda1,OSP_cda1-001,CONC,19828.791167,ng/mL,24,0,0,CDA1,100,INTRAVENOUS
OSP_cda1,OSP_cda1-001,CONC,9111.478396,ng/mL,672,0,0,CDA1,100,INTRAVENOUS
OSP_cda1,OSP_cda1-001,CONC,1816.179249,ng/mL,2016,0,0,CDA1,100,INTRAVENOUS
```

`sdtm_like/` が真実の源で、`analysis_inputs/` はそこから再生成し、
`python -m tools.check_examples` がドリフトを検査します。

**status:** `OK`（標準チェック許容）/ `WARN`（使えるが原因をノート化）/
`FAILED`（原則停止、必要なら `--allow-validation-failed`）。

run-level `MANIFEST.yml` には、`target_metadata` として機械可読の注意情報も残ります。
たとえば AUC target が独立した文献AUCではなく `dose_over_cl` 由来かどうか、
1-compartment fixture として `t_half` と CL/V の不整合が検出されたか、
またそれが fixture limitation として確認済みかを確認できます。
warning薬剤では `value_provenance_summary` にも、CL/V/t_half の provenance
確認状況、source review が残る項目、fixture limitation として確認済みの
mismatch field が記録されます。

## 検証ステータス

| Area | Status |
| --- | --- |
| Internal fixture generation | CIでテスト済み |
| Manifest / drift checks | CIでテスト済み |
| SDTM-like output checks | CIでテスト済み |
| NONMEM adapter file generation | smoke test済み |
| Phoenix adapter file generation | smoke test済み |
| nlmixr2 execution | 任意、CI-qualifiedではない |
| Clinical PK validation | 対象外 |

---

## 使うべきでない用途（重要）

このハーネスは「実臨床の予測モデル」ではありません。以下は別レイヤーで扱います。

- 投与設計・用量推定・規制提出用の妥当化
- 共変量モデル（年齢/体重/性別等）や非線形 PK の正当化
- IIV/residual を使った厳密な再現性評価（現在は fixture 用途向け）

`targets.auc.value` は通常 `Dose/CL` 由来で、厳密な文献 AUC と同一視しないでください。
モデルは意図的に 1-compartment 解析解で、NCA 再計算は sanity check であって NCA エンジンではありません。
一部 fixture は、採用した CL/V ペアと完全には両立しない `t_half` target を意図的に保持しています。
その場合は `targets.yml`、validation warning、workflow manifest の `target_metadata` に、
検出済みかつ確認済みの制約としてラベルが残ります。

任意の `profiles/*_oral_systemic_basis.yml` は、systemic-basis の経口薬について
systemic CL + bioavailability と整合した曝露を与えます（いずれも fixture テンプレート）。
詳細は [docs/CALIBRATED_PROFILES.md](docs/CALIBRATED_PROFILES.md)。

---

## ライセンスとデータ境界

- コードとドキュメントは [MIT License](LICENSE) で公開。
- DailyMed、PubMed、OSP PBPK Model Library 等の外部情報は参照元として扱い、上流の利用条件に従います。
- 外部ツール本体、商用ライセンス、施設 SOP、実患者データは含めません。
- 生成 CSV やテンプレートは workflow fixture であり、submission-ready SDTM/ADaM・臨床推論・投与設計・規制提出用モデル妥当化の証拠ではありません。

---

## ドキュメント

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md): 日常操作
- [docs/QUICKSTART.md](docs/QUICKSTART.md): 初見向けの短い順番
- [docs/index.md](docs/index.md): GitHub Pages docs 入口
- [docs/ACCEPTANCE_TEST.md](docs/ACCEPTANCE_TEST.md): README-only で第三者が回せる確認手順
- [docs/DOWNSTREAM_E2E.md](docs/DOWNSTREAM_E2E.md): NCA/PopPK 下流 smoke 検証
- [docs/EXTERNAL_TOOL_VALIDATION_GUIDE.md](docs/EXTERNAL_TOOL_VALIDATION_GUIDE.md): Phoenix/NONMEM/nlmixr2 での実行検証
- [docs/SITE_ADAPTER_GUIDE.md](docs/SITE_ADAPTER_GUIDE.md): 施設別 CSV adapter の作り方
- [docs/CALIBRATED_PROFILES.md](docs/CALIBRATED_PROFILES.md): F補正の経口プロファイル
- [docs/USER_TEST_REPORT_TEMPLATE.md](docs/USER_TEST_REPORT_TEMPLATE.md): 利用者テスト報告テンプレート
- [docs/VALIDATION_AND_RELEASE_CHECKLIST.md](docs/VALIDATION_AND_RELEASE_CHECKLIST.md): リリース前チェック
- [docs/RELEASE_NOTES_TEMPLATE.md](docs/RELEASE_NOTES_TEMPLATE.md): リリースノート雛形
- [docs/WINDOWS_POWERSHELL.md](docs/WINDOWS_POWERSHELL.md): Windows 向け実行手順
- [docs/CODEX_HARNESS.md](docs/CODEX_HARNESS.md): Codex 運用メモ
- [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) · [CITATION.cff](CITATION.cff) · [CHANGELOG.md](CHANGELOG.md)

---

## 主要設計思想

1. **canonical は壊さない** — `pk.yml`, `targets.yml`, `spec` は自動更新しない
2. **再現性を優先** — seed、manifest、trace、ログで実行履歴を固定
3. **接続性を優先** — 下流 NCA/PopPK の差異は site adapter で吸収し、ハーネスは fixture と検証に集中
4. **検証と実臨床を分離** — 本リポジトリは fixture 作成。臨床妥当化は別レイヤー

---

## 一言で言うと

**「本番の解析モデルを作るための、速く壊れにくい検証配管を先に作る」**ための道具です。
外部でのモデル実装とパラメータ更新を分離し、実装者・統計家・臨床薬理担当が
同じログを見ながら同じ議論をできる状態にすることを目的にしています。
