"""Consolidate the completed 37-drug manual audit; never alters scientific inputs."""
import csv
import json
from collections import Counter
from pathlib import Path

OUT = Path(__file__).resolve().parent
PARAMETERS = {"clearance", "volume", "half_life", "bioavailability"}


def csv_write(name, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (OUT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
                             for key, value in row.items()})


def md(value):
    return str(value).replace("|", "／").replace("\n", " ")


def main():
    internal = json.loads((OUT / "internal-audit.json").read_text())
    tests = json.loads((OUT / "test-summary.json").read_text())
    groups = [json.loads((OUT / f"group-{letter}.json").read_text()) for letter in "abc"]
    drugs = sorted([drug for group in groups for drug in group["drugs"]], key=lambda drug: drug["slug"])
    assert len(drugs) == len({drug["slug"] for drug in drugs}) == 37
    assert {drug["slug"] for drug in drugs} == {r["slug"] for r in internal["records"]}
    parameters, issues, source_checks = [], [], []
    for drug in drugs:
        assert len(drug["parameters"]) == 4 and {p["parameter"] for p in drug["parameters"]} == PARAMETERS, drug["slug"]
        drug["clinical_use_status"] = "HOLD"
        for parameter in drug["parameters"]:
            for field in ("stored_value", "verdict", "reason", "source_urls", "locator", "access_level", "required_action"):
                assert field in parameter, (drug["slug"], parameter["parameter"], field)
            parameters.append({"slug": drug["slug"], **parameter})
        issues.extend({"slug": drug["slug"], **issue} for issue in drug["issues"])
        source_checks.extend({"slug": drug["slug"], **source} for source in drug["source_checks"])
    verdict_counts = dict(Counter(p["verdict"] for p in parameters))
    access_counts = dict(Counter(p["access_level"] for p in parameters))
    summary = {"audit_date": "2026-10-02", "drug_count": 37, "core_parameter_count": len(parameters),
               "verdict_counts": verdict_counts, "access_counts": access_counts,
               "clinical_accepted_count": 0, "clinical_hold_count": 37,
               "note": "All drugs reviewed, not all values verified. Derived/qualified/fixture labels do not constitute clinical model validation.",
               "drugs": drugs}
    (OUT / "all-drug-audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    csv_write("core-parameter-audit.csv", parameters)
    csv_write("review-findings.csv", issues)
    csv_write("source-access.csv", source_checks)
    labels = {"VERIFIED_VALUE_ONLY": "数値照合", "QUALIFIED": "条件付き", "CONTRADICTION": "不整合",
              "UNVERIFIED": "未確認", "FIXTURE_ASSUMPTION": "仮定", "DERIVED": "派生"}
    by_slug = {r["slug"]: r for r in internal["records"]}
    lines = [
        "# 全37薬剤のPKパラメーター監査",
        "",
        "監査日: 2026-10-02（Asia/Tokyo）。対象: この作業開始時の `drugs/*/pk.yml` 全37薬剤と、対応する `targets.yml`・`spec_pk1_*.yml`。",
        "",
        "**全37薬剤を監査した。全パラメーターが正しいという結論ではない。臨床判断用モデルとしての採用は全37薬剤で保留する。** 一次資料の数値と一致していても、対象集団・投与条件・パラメーターの定義・モデル構造・変動の根拠を満たすとは限らない。今回の成果物は不整合と未確認事項を明示する監査結果であり、臨床モデルの認証ではない。",
        "",
        "監査対象の111 YAMLファイルのSHA-256は開始時と一致。原データの数値を推測で置換していない。既存の未コミット変更は監査開始時の状態として扱った。`INDEX.csv` / `EXCLUDED.csv` / `pk_library.yml` の編集も本監査では行っていない。",
        "",
        "**GitHub掲載時の対象区別:** この監査は、未コミット変更を含むローカル作業ツリーを対象にしている。監査対象そのものは `input-manifest.json` の111ファイルのhashで特定する。監査結果のみをGitHubへ追加しており、未コミットの薬剤データ・実装・テスト一式は同時に公開していない。したがって、掲載先commitのcanonicalデータ全体を監査済み、又は掲載先commitで1002テストを実行済み、とは解釈しない。",
        "",
        "## 範囲と判定方法",
        "",
        "- CL、V、半減期、Fの **37×4=148項目** を薬剤別に判定。原著・公的ラベル/審査資料の取得範囲（本文/抄録/未取得）を記録し、元の `checked` は再確認済みの証拠として流用しなかった。総説しか確認できない部分は、その限界を各行に記載した。データの `full_label` はFDA審査資料全文も含み、資料の種別はsource_checksに記した。",
        "- ソース値→単位・体重/BSA換算→保存値→モデルtheta→AUC/半減期ターゲットを追跡。投与経路、用量、輸注時間、対象集団、KA/lag、IIV、残差誤差、要約統計、観測時間も確認した。",
        "- 既存生成器の由来台帳720行は内部網羅性の補助であり、720行すべての外部根拠を新規に検証したという意味ではない。モデル・ターゲットの全スカラー値2,193行も別CSVへ保存した。",
        "- 既存83ソース登録の全URLを最新版まで取得した監査ではない。各値に必要な出典を読み直し、補完資料・取得失敗を `source-access.csv` に記録した。DailyMedの同一setidは更新され得る。未記載の版、分析法、試験集団詳細などを推定補完しない。",
        "- 個票濃度データに対する再推定、原PopPKモデルの完全再現、測定法/BLQ処理の全試験監査は今回実施していない。",
        "",
        "|判定|意味|件数|",
        "|---|---|---:|",
    ]
    descriptions = {
        "VERIFIED_VALUE_ONLY": "出典の値・換算を照合できた。セット全体や現シナリオへの適合は未承認。",
        "QUALIFIED": "値は追えるが、集団・製剤・定義・本文取得範囲等の条件が残る。",
        "CONTRADICTION": "出典、換算、定義、統計量又は保存メタデータに具体的不整合がある。",
        "UNVERIFIED": "今回の取得資料では根拠又は定義を確認できない。",
        "FIXTURE_ASSUMPTION": "範囲の中点/端点、便宜的な代表値、IV入力のF=1等。実測平均ではない。",
        "DERIVED": "他のパラメーターから計算した値。独立の実測・検証値ではない。",
    }
    for verdict in labels:
        lines.append(f"|{labels[verdict]} (`{verdict}`)|{descriptions[verdict]}|{verdict_counts.get(verdict, 0)}|")
    lines += ["", "同じ項目に問題が重なる場合は主判定を1つ付け、詳細な制約を理由・必要な対応欄に残した。`不整合` はすべてが薬物の数値誤りという意味ではなく、丸めの未記載や出典の誤帰属も含む。",
              "", "## 優先して解消する所見", "",
              "|薬剤|確認した問題|対応|", "|---|---|---|"]
    priorities = [
        ("omeprazole", "記録の624 mL/minは37.44 L/h。保存43.56 L/hは記録された換算式と一致しない。raw V0.4 L/kgと採用V0.23 L/kgの履歴も分離が必要。", "元研究のmedian CL、mean Vssとその集団を保持して修正案を作り、theta/派生/AUCを一括再計算する。"),
        ("apixaban", "total CL3.3 L/hをCL/F扱い。一次IV試験のCL3.2–3.5 L/hと保存systemic CL1.65 L/hが不整合。", "systemic/apparentの定義を修正審査。現在10mg、F1=1のAUCはF≈0.5を用いたsystemic計算の約2倍となる。Vss21Lの単純差替えは行わない。"),
        ("sildenafil", "V105 LはIV Vss。V/Fとしての扱いを支持しない。保存F0.44は参照ラベルの平均41%と異なる。", "同一研究のCL・V・F・半減期の定義を揃える。範囲25–63%の中点を観測平均へ読み替えない。"),
        ("inulin", "保存V13 L/70kgは当該研究の実測Vssではなく、Discussionが引用した従来文献の値。研究のVssは11.00 L/70kg。", "CLの推定法（93.5と主要推定96.1）とVの由来を揃え、派生半減期も再審査。"),
        ("ethinylestradiol", "保存16.5–17.6hという範囲が該当表で支持されない。現100mgは出典のEE0.02mgと大幅に異なる。", "併用製剤・cycle/day・要約統計を固定。半減期から派生したVと100mgデモ条件を臨床用に流用しない。"),
        ("cda1", "CL0.0014 mL/min/kgとV0.070 L/kgは異なる用量群から選択。半減期も群別幾何平均範囲の中点。", "同じ群・同じ要約統計のパラメーターセットを採用する。"),
        ("tefibazumab", "主要出典は血液透析中のESRD患者。現scenarioのadult_healthyとは異なる。", "患者集団と10/20mg/kgの投与条件を保ち、健康成人値と混同しない。"),
        ("motavizumab_yte", "43–68 mL/dayの中点は55.5。記録式の結果0.0023125 L/hに対し保存値は55 mL/day相当。", "無記載の丸め/選択を解消し、依存するV・AUCも再審査。"),
        ("mexiletine", "出典の分布容積5–7 L/kgは、保存V/Fという定義を直接支持しない。CLもそのVと半減期からの逆算。", "IV/経口とF補正の有無を一次試験で確定するまで派生systemic値を採用しない。"),
        ("erythromycin", "出典の125mg IVは30分輸注、現specは1時間。", "用量一致だけでなく入力速度も原条件へ対応づける。"),
    ]
    drug_map = {d["slug"]: d for d in drugs}
    for slug, problem, action in priorities:
        urls = list(dict.fromkeys(url for p in drug_map[slug]["parameters"] for url in p["source_urls"]))
        links = " ".join(f"[資料{i+1}]({url})" for i, url in enumerate(urls[:3]))
        group_letter = next(g["group"] for g in groups if any(d["slug"] == slug for d in g["drugs"]))
        lines.append(f"|[{slug}](group-{group_letter}.md)|{problem} {links}|{action}|")
    lines += [
        "", "dapagliflozinの77.8%→0.78は既存注記では丸めと説明されているが、登録式 `77.8/100` の結果は0.778である。これは上記の大きなbasis誤分類と同列の数値誤りではなく、精度・丸め規則の記載不一致として扱う。mefenamic acidはDailyMedとFDA版でCL21.23/21.13の差があり、数値と版の対応を残す必要がある。",
        "", "## 全薬剤に共通する採用上の制約", "",
        "1. **CL/Vと半減期の違いを、数値を合わせて消さない。** 1-compモデルなら `t½=ln(2)×V/CL` だが、多compのVss、Vz、Vcは互換ではない。Vss/CLはMRTに関係し、一般に終末半減期を直接再現しない。異なる相・集団の代表値を一組へ混ぜない。",
        "2. **18薬剤はCL・V・半減期のいずれかを他の値から逆算している。** 同じ半減期への一致は独立検証にならない。依存関係は `internal-audit.json` に記録。36薬剤のAUCも同じCLから計算した整合性ターゲットであり、独立の臨床AUCではない。sufentanilの0.278 ng*h/mLはlabelの278 h*pg/mLを換算した独立出典値として確認したが、これだけでモデル全体を検証したことにはならない。",
        "3. **個体間変動と残差誤差は全37薬剤で汎用設定。** IIVはCL0.09、V0.04、吸収モデル25薬剤のKA0.16（実装上OMEGAの分散、CVやSDではない）。残差はprop0.25/add0、相関なし。各薬剤の原PopPK推定値ではない。25薬剤のKA=1.2 /h、ALAG1=0.5hも共通の仮定であり、原著吸収モデルの再現ではない。",
        "4. **ターゲットの統計量を実測と混同しない。** 全37薬剤の半減期summaryはarithmetic_meanだが、元が中央値、幾何平均、範囲、中点、又は派生計算のものを含む。半減期SDは30薬剤が1h、残りも便宜的設定。AUC変動は全37薬剤がGCV35%で、独立出典AUCにもこの仮定が付く。典型値、母集団平均、変動、推定不確実性を区別する。",
        "5. **28薬剤に100mgのデモ用量。** 100mgで統一できる科学的根拠はなく、非線形PK、酵素誘導/阻害、製剤、食事、併用薬などの適用条件を超え得る。用量は監査ファイルに記録した現値であり、投与推奨ではない。70kg換算とBSA1.73m²の値も区別し、人口分布から自動的に個人のPKが検証されたとはみなさない。",
        "6. **長い半減期の観測窓が不足するケース。** motavizumab MEDI-524は168/636h、YTEは72/2040h、tefibazumabは168/420h（観測終了/保存半減期）。これは1半減期未満という記述であり、一律の合否閾値ではない。終末相サンプル・定量下限・AUC外挿率を用途ごとに評価する。",
        "",
        "FDAの[Population Pharmacokinetics guidance（2022、V.C–D）](https://www.fda.gov/media/128793/download)も、用途に応じたモデル評価、外挿の不確実性、個体間変動と推定不確実性の区別を求めている。今回の臨床採用保留は、現在のモデルと証拠に対する本監査の判断であり、FDAによる個別薬剤の不適合判定ではない。",
        "", "## 全37薬剤の判定一覧", "",
        "数値照合＝出典値の照合のみ。すべて臨床採用は保留。詳細は薬剤名のリンク、148行のCSV/JSONを参照。", "",
        "|薬剤|CL|V|t½|F|主要所見|", "|---|---|---|---|---|---|",
    ]
    for drug in drugs:
        group_letter = next(g["group"] for g in groups if any(d["slug"] == drug["slug"] for d in g["drugs"]))
        verdicts = {p["parameter"]: labels[p["verdict"]] for p in drug["parameters"]}
        lines.append(f"|[{drug['slug']}](group-{group_letter}.md)|" + "|".join(verdicts[p] for p in ("clearance", "volume", "half_life", "bioavailability")) + f"|{md(drug['summary'])}|")
    lines += ["", "## 既存11警告の再確認", "",
              "この25%閾値はリポジトリの機械的警告基準であり、臨床的同等性の基準ではない。警告なしの26薬剤を検証済みと扱わない。", "",
              "|薬剤|保存t½ (h)|ln(2)×V/CL (h)|", "|---|---:|---:|"]
    for slug in internal["half_warning_drugs"]:
        record = by_slug[slug]
        lines.append(f"|{slug}|{record['stored_half_h']:.8g}|{record['one_compartment_half_h']:.8g}|")
    lines += [
        "", "## 機械検証と再現性", "",
        "- 開始時 `make validate`: 通過、上記11警告あり。",
        "- Python3.12.2の監査用一時venv（PyYAML6.0.3、pytest9.1.1）で `make harness-check`: **終了コード0**。pytestは**1002件中701成功、301スキップ、失敗0**。",
        "- スキップ: SAS299件、PKNCA/rpy2比較1件、Quarto DOCX生成1件。Quartoはsandboxのsysctl/architecture判定で失敗してskip。",
        "- external-validation-probeは `execute=false`。nlmixr2はprobeのみ成功、NONMEM/Phoenix実行ファイルなし。実行・相互一致・臨床予測精度の証拠にはしない。",
        "- 初回Python3.10では3件失敗: 日本/米国の背景分布CSVで浮動小数点末尾のbyte不一致2件、ISO日時小数秒の例外メッセージ不一致1件。3.12で同じ5ケース再確認と全体チェックは通過。3.10互換性の問題は残し、コードを書き換えて隠していない。",
        f"- 文書化された換算/派生123項目の再計算: 一致{internal['formula_counts']['MATCH']}、式と保存値の差{internal['formula_counts']['MISMATCH']}、自動評価対象外{internal['formula_counts']['NOT_EVALUATED']}。対象外は手動レビューに明示し、全式合格とはしていない。",
        "- 内部のtheta/derived/target/F1方針の対応チェックは37薬剤で矛盾なし。ただし、元のbasis自体が誤っていても内部は整合する。これはapixaban等の科学的問題を否定しない。",
        "",
        "以下は監査時の実行記録であり、`/private/tmp/...` の環境を公開配布しているものではない。別環境ではPython3.12のvenvにPyYAMLとpytestを導入し、そのpythonへ置き換える必要がある。加えて、`audit_internal.py` は111入力すべてのhash一致を必須とするため、GitHubのfresh cloneだけでは元の未コミットsnapshotを再現できず、意図どおり停止する。保存済み判定の再集計 `consolidate.py` は標準ライブラリだけで実行できる。",
        "",
        "```bash",
        "PYTHONDONTWRITEBYTECODE=1 /private/tmp/pk-audit-20261002-py312/bin/python docs/research/2026-10-02-all-drug-audit/audit_internal.py",
        "PYTHONDONTWRITEBYTECODE=1 /private/tmp/pk-audit-20261002-py312/bin/python docs/research/2026-10-02-all-drug-audit/consolidate.py",
        "PYTHONDONTWRITEBYTECODE=1 make harness-check PYTHON=/private/tmp/pk-audit-20261002-py312/bin/python",
        "```",
        "",
        "## 収集botに必要な採用条件", "",
        "収集値をそのまま臨床モデルへ昇格させず、薬剤・analyte・matrix・total/unbound、CL/CL/F、Vss/Vz/Vc/V/F、投与経路・製剤・dose moiety・量・輸注時間・単回/反復/定常状態・食事・併用薬、対象人数/年齢/腎肝機能、要約統計と変動の種類、原典版/表/脚注、原文字列と換算式を1レコードとして保持する。",
        "",
        "原典値、派生値、範囲からの選択、仮定を分け、異なる群を結合しない。必須の定義・集団・原典が未確認なら `needs_review` に残す。算術不一致、出典誤帰属、相/統計量の不一致は自動採用を止める。モデルの用途を固定し、独立観測データによる妥当性評価と薬剤別変動の検証後に採用判断を行う。",
        "", "## 成果物", "",
        "- [全148パラメーターの監査CSV](core-parameter-audit.csv) / [全37薬剤の構造化JSON](all-drug-audit.json)",
        "- [薬剤別詳細 A](group-a.md) / [B](group-b.md) / [C](group-c.md)",
        "- [指摘・必要な対応](review-findings.csv) / [取得成否と補完経路](source-access.csv)",
        "- [原文取得ファイル27件のURL・SHA-256](source-capture-manifest.json)（shellで保存した分のみ。原文は一時フォルダにあり、永続アーカイブではない。Web取得のみの資料はsource-access参照）",
        "- [全薬剤の内部値・モデル条件](all-drug-internal.csv) / [換算再計算](arithmetic-checks.csv) / [全model・targetsスカラー](model-and-target-scalars.csv)",
        "- [既存由来台帳720行](provenance-inventory/PARAMETER_PROVENANCE.csv)（既存のreview状態は今回の外部確認結果ではない）",
        "- [開始時入力hash](input-manifest.json) / [機械チェックJSON](internal-audit.json)",
        "- [harnessログ](harness-check-py312.log) / [pytest XML](test-results-py312.xml) / [検証要約](test-summary.json) / [初回3.10失敗ログ](initial-tests-py310.log)",
        "",
        "前回のHermes caffeine候補1件はこの37薬剤ライブラリには含まれない。別監査のローカル文書は `docs/research/2026-10-02-pk-collector-reverification.md`（今回のGitHub掲載範囲外）。今回の全薬剤監査はその限定監査を37薬剤へ拡張したもので、Hermesの実行状態・公開・自動採用設定を変更したという主張ではない。",
    ]
    (OUT / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "drugs"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
