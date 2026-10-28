#!/usr/bin/env python3
"""Export parameter tables and downloads from the checked canonical snapshot."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

try:
    from build_docs_site import build_bundle
    from make_parameter_provenance_report import build_report
except ModuleNotFoundError:
    from tools.build_docs_site import build_bundle
    from tools.make_parameter_provenance_report import build_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--out-dir", type=Path, default=Path("docs"))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    destination = args.out_dir if args.out_dir.is_absolute() else root / args.out_dir
    bundle = build_bundle(root)
    inventory = destination / "parameters"
    build_report(root, inventory)
    for filename in ("PARAMETER_PROVENANCE.csv", "SOURCES.csv"):
        path = inventory / filename
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    report = inventory / "PARAMETER_PROVENANCE.md"
    report.write_text(
        "---\nlayout: page\ntitle: 全パラメータと出典\n---\n\n"
        + report.read_text(encoding="utf-8"), encoding="utf-8",
    )
    (inventory / "PARAMETER_PROVENANCE.yml").unlink()
    governance_rows = []
    selection_rows = []
    for drug in bundle["drugs"]:
        check = drug["fixture_assessment"]["half_life_check"]
        governance_rows.append({
            "drug": drug["slug"], "clinical_assessment": drug["simulation_validity"]["status"],
            "dose_purpose": drug["fixture_assessment"]["dose_context"]["purpose"],
            "clinical_dose_verified": False,
            "execution_arms": json.dumps(drug["spec"]["regimen"]["arms"], ensure_ascii=False),
            "half_life_ratio": check["ratio"], "hold_candidate": check["hold_candidate"],
            "circular": check["circular"], "limitations": json.dumps(drug["fixture_limitations"], ensure_ascii=False),
        })
        for field, entry in drug["provenance"].items():
            selection = entry.get("selection") or {}
            selection_rows.append({"drug": drug["slug"], "parameter": field,
                "rule": selection.get("rule"), "rationale": selection.get("rationale"),
                "depends_on": json.dumps(selection.get("depends_on") or []),
                "raw_value": entry.get("raw_value"), "raw_unit": entry.get("raw_unit"),
                "normalized_value": entry.get("normalized_value"), "normalized_unit": entry.get("normalized_unit"),
                "source_id": entry.get("source_id")})
    for filename, rows in (("FIXTURE_GOVERNANCE.csv", governance_rows), ("PARAMETER_SELECTIONS.csv", selection_rows)):
        with (inventory / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    lines = [
        "---", "layout: page", "title: 薬剤別シミュレーションパラメータ",
        "permalink: /parameter-values/", "---", "",
        "# 薬剤別シミュレーションパラメータ", "",
        "このコミットの正本YAMLから生成した採用値です。CLはL/h、VはL、KAは1/h、F1は無次元、ALAG1はhです。",
        "数値の整合性は臨床モデルの妥当性を意味しません。全薬剤の臨床採用保留を継続しています。", "",
        "[検索・詳細画面](https://y-fukiya.github.io/pkdummy-harness/parameters/) / [原典修正と残る制約](https://y-fukiya.github.io/pkdummy-harness/parameter-corrections/)", "",
        "全剤の投与設定は計算用ストレス試験で、臨床常用量として未確認です。集団名は投与量の妥当性を保証しません。", "",
        "| 薬剤 | 経路 | CL | V | KA | F1 | ALAG1 | CL basis / V basis | 臨床評価 | 半減期比・候補 | 実行用量・計算用 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for drug in bundle["drugs"]:
        theta = drug["spec"]["model"]["theta"]
        values = [str(theta.get(key, "—")) for key in ("CL", "V", "KA", "F1", "ALAG1")]
        basis = " / ".join(str(drug["parsed"].get(key) or "未確認")
                           for key in ("clearance_basis", "volume_basis"))
        check = drug["fixture_assessment"]["half_life_check"]
        ratio = f"{check['ratio']:.3f}" if check["evaluated"] else "評価不能"
        candidate = "保留候補" if check["hold_candidate"] else "臨床妥当性未判定"
        dose = "; ".join(f"{name}: {arm['dose_mg']} mg" for name, arm in drug["spec"]["regimen"]["arms"].items())
        cells = [drug["slug"], drug["spec"]["regimen"]["route"], *values, basis,
                 drug["simulation_validity"]["status"], ratio + " " + candidate, dose + "・常用量未確認"]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend([
        "", "## 出典・変換・確認状態", "",
        "- [評価・投与設定・値の選択方針](https://y-fukiya.github.io/pkdummy-harness/fixture-governance/)",
        "- [全37剤の評価・投与設定CSV](https://y-fukiya.github.io/pkdummy-harness/parameters/FIXTURE_GOVERNANCE.csv)",
        "- [全パラメータの選択ルールCSV](https://y-fukiya.github.io/pkdummy-harness/parameters/PARAMETER_SELECTIONS.csv)",
        "- [全パラメータCSV](https://y-fukiya.github.io/pkdummy-harness/parameters/PARAMETER_PROVENANCE.csv)",
        "- [出典CSV](https://y-fukiya.github.io/pkdummy-harness/parameters/SOURCES.csv)",
        "- [値の由来一覧](https://y-fukiya.github.io/pkdummy-harness/parameters/PARAMETER_PROVENANCE.html)", "",
        "F1=1は、apparent CL/F・V/Fを用いたモデルでは実際の利用率100%を主張しません。",
        "原典照合、導出、fixture仮定、未確認事項を区別して確認してください。", "",
    ])
    (destination / "PARAMETERS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Parameter documents exported: {bundle['drug_count']} drugs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
