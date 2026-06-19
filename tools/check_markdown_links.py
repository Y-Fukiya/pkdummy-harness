#!/usr/bin/env python3
"""Check local Markdown links in repository documentation."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
AUTOLINK_RE = re.compile(r"<((?:https?://|mailto:)[^>]+)>")
DEFAULT_GLOBS = ["*.md", "docs/**/*.md", ".github/**/*.md"]
SKIP_PREFIXES = (
    "http://",
    "https://",
    "mailto:",
    "tel:",
    "#",
    "javascript:",
)


def iter_markdown_files(root: Path, globs: list[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in globs:
        files.update(path for path in root.glob(pattern) if path.is_file())
    return sorted(files)


def strip_title(target: str) -> str:
    target = target.strip()
    if not target:
        return target
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    quote_positions = [i for i in (target.find(' "'), target.find(" '")) if i != -1]
    if quote_positions:
        target = target[: min(quote_positions)]
    return target.strip()


def normalize_target(raw: str) -> str:
    target = strip_title(raw)
    parsed = urlparse(target)
    if parsed.scheme or target.startswith(SKIP_PREFIXES):
        return ""
    path = target.split("#", 1)[0]
    return unquote(path)


def check_file(path: Path, root: Path) -> list[str]:
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        targets = [m.group(1) for m in LINK_RE.finditer(line)]
        targets.extend(m.group(1) for m in AUTOLINK_RE.finditer(line))
        for raw in targets:
            target = normalize_target(raw)
            if not target:
                continue
            candidate = (path.parent / target).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                issues.append(f"{path}:{lineno}: link escapes repo: {raw}")
                continue
            if candidate.exists():
                continue
            issues.append(f"{path}:{lineno}: missing local link target: {raw}")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--glob", action="append", dest="globs", help="Markdown glob to check")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    globs = args.globs or DEFAULT_GLOBS
    issues: list[str] = []
    for path in iter_markdown_files(root, globs):
        issues.extend(check_file(path.resolve(), root))

    if issues:
        print("Markdown link check: FAILED")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Markdown link check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
