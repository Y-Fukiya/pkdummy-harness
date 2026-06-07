#!/usr/bin/env python3
"""Render a static HTML viewer for harness and workflow manifests."""

from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = yaml.safe_load(f)
    if not isinstance(obj, dict):
        raise ValueError(f"Manifest must be a mapping: {path}")
    return obj


def _rows(mapping: dict[str, Any]) -> str:
    if not mapping:
        return "<tr><td colspan=\"2\">None</td></tr>"
    lines = []
    for key, value in mapping.items():
        lines.append(f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>")
    return "\n".join(lines)


def _items(values: list[Any]) -> str:
    if not values:
        return "<li>None</li>"
    return "\n".join(f"<li>{html.escape(str(value))}</li>" for value in values)


def _status_class(status: str) -> str:
    lowered = status.lower()
    if lowered in {"ok", "warn", "failed"}:
        return lowered
    return "unknown"


def render_manifest_viewer(manifest_yml: Path | str, out_html: Path | str | None = None) -> Path:
    manifest_path = Path(manifest_yml)
    manifest = _load_yaml(manifest_path)
    out_path = Path(out_html) if out_html else manifest_path.with_suffix(".viewer.html")
    status = str(manifest.get("status") or "UNKNOWN")
    title = f"PK Fixture Manifest Viewer - {status}"
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; color: #111827; background: #f8fafc; }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 32px 20px 48px; }}
    h1 {{ font-size: 28px; margin: 0 0 8px; }}
    h2 {{ font-size: 18px; margin-top: 28px; }}
    .status {{ display: inline-block; padding: 4px 10px; border-radius: 999px; font-weight: 700; }}
    .ok {{ background: #dcfce7; color: #166534; }}
    .warn {{ background: #fef3c7; color: #92400e; }}
    .failed {{ background: #fee2e2; color: #991b1b; }}
    .unknown {{ background: #e5e7eb; color: #374151; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #e5e7eb; }}
    th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
    th {{ width: 260px; background: #f3f4f6; }}
    code {{ background: #eef2ff; padding: 1px 4px; border-radius: 4px; }}
    .note {{ color: #4b5563; }}
  </style>
</head>
<body>
<main>
  <h1>PK Fixture Manifest Viewer</h1>
  <p class="note">Static local viewer for workflow fixture manifests. It does not execute simulations or edit PK files.</p>
  <p>Status: <span class="status {_status_class(status)}">{html.escape(status)}</span></p>
  <h2>Summary</h2>
  <table>
    <tr><th>Manifest</th><td>{html.escape(str(manifest_path))}</td></tr>
    <tr><th>Purpose</th><td>{html.escape(str(manifest.get("purpose", "")))}</td></tr>
    <tr><th>Mode</th><td>{html.escape(str(manifest.get("mode", "")))}</td></tr>
    <tr><th>Created At</th><td>{html.escape(str(manifest.get("created_at", "")))}</td></tr>
  </table>
  <h2>Counts</h2>
  <table>{_rows(manifest.get("counts") if isinstance(manifest.get("counts"), dict) else {})}</table>
  <h2>Outputs</h2>
  <table>{_rows(manifest.get("outputs") if isinstance(manifest.get("outputs"), dict) else {})}</table>
  <h2>Warnings</h2>
  <ul>{_items(manifest.get("warnings") if isinstance(manifest.get("warnings"), list) else [])}</ul>
  <h2>Safeguards / Limitations</h2>
  <ul>{_items((manifest.get("safeguards") if isinstance(manifest.get("safeguards"), list) else []) + (manifest.get("limitations") if isinstance(manifest.get("limitations"), list) else []))}</ul>
</main>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest_yml", type=Path)
    parser.add_argument("--out-html", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        out_path = render_manifest_viewer(args.manifest_yml, args.out_html)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Manifest viewer written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
