#!/usr/bin/env python3
"""Export parameter tables and downloads from the checked canonical snapshot."""

from __future__ import annotations

import argparse
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
    lines = [
        "---", "layout: page", "title: 薬剤別シミュレーションパラメータ",
        "permalink: /parameter-values/", "---", "",
        "# 薬剤別シミュレーションパラメータ", "",
        "このコミットの正本YAMLから生成した採用値です。CLはL/h、VはL、KAは1/h、F1は無次元、ALAG1はhです。",
        "数値の整合性は臨床モデルの妥当性を意味しません。全薬剤の臨床採用保留を継続しています。", "",
        "[検索・詳細画面](/pkdummy-harness/parameters/) / [原典修正と残る制約](/pkdummy-harness/parameter-corrections/)", "",
        "| 薬剤 | 経路 | CL | V | KA | F1 | ALAG1 | CL basis / V basis |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for drug in bundle["drugs"]:
        theta = drug["spec"]["model"]["theta"]
        values = [str(theta.get(key, "—")) for key in ("CL", "V", "KA", "F1", "ALAG1")]
        basis = " / ".join(str(drug["parsed"].get(key) or "未確認")
                           for key in ("clearance_basis", "volume_basis"))
        cells = [drug["slug"], drug["spec"]["regimen"]["route"], *values, basis]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend([
        "", "## 出典・変換・確認状態", "",
        "- [全パラメータCSV](/pkdummy-harness/parameters/PARAMETER_PROVENANCE.csv)",
        "- [出典CSV](/pkdummy-harness/parameters/SOURCES.csv)",
        "- [値の由来一覧](/pkdummy-harness/parameters/PARAMETER_PROVENANCE.html)", "",
        "F1=1は、apparent CL/F・V/Fを用いたモデルでは実際の利用率100%を主張しません。",
        "原典照合、導出、fixture仮定、未確認事項を区別して確認してください。", "",
    ])
    (destination / "PARAMETERS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Parameter documents exported: {bundle['drug_count']} drugs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
