#!/usr/bin/env python3
"""
One-shot runner:
  all_pk_parameters_combined.csv -> jobs_excluded22.yml -> harvest -> rebuild_index -> summarize

This is meant to be run on your machine (internet required for DailyMed / NCBI).
It simply wires together the existing tools.

Usage:
  python tools/run_excluded22_flow.py --csv all_pk_parameters_combined.csv --repo .
"""

from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path

def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="all_pk_parameters_combined.csv")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--jobs-out", default="jobs_excluded22.yml")
    ap.add_argument("--default-dose-mg", type=float, default=100.0)
    ap.add_argument("--weight-ref-kg", type=float, default=70.0)
    ap.add_argument("--pubmed", action="store_true", help="Force-enable PubMed search for all jobs.")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    csv_path = (repo / args.csv).resolve()
    jobs_out = (repo / args.jobs_out).resolve()
    excluded_csv = (repo / "EXCLUDED.csv").resolve()
    report_md = (repo / "reports" / "excluded_summary.md").resolve()
    report_md.parent.mkdir(parents=True, exist_ok=True)

    cmd1 = [sys.executable, str(repo / "tools" / "make_jobs_from_csv_v01.py"),
            "--in", str(csv_path), "--out", str(jobs_out),
            "--default-dose-mg", str(args.default_dose_mg),
            "--weight-ref-kg", str(args.weight_ref_kg)]
    if args.pubmed:
        cmd1.append("--pubmed")
    run(cmd1)

    # Harvest (requires internet)
    run([sys.executable, str(repo / "tools" / "harvest_and_generate.py"),
         "--jobs", str(jobs_out), "--repo", str(repo),
         "--default-dose-mg", str(args.default_dose_mg)])

    run([sys.executable, str(repo / "tools" / "rebuild_index.py"), str(repo)])

    run([sys.executable, str(repo / "tools" / "summarize_excluded.py"),
         "--excluded", str(excluded_csv), "--out-md", str(report_md)])

    print("Done.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
