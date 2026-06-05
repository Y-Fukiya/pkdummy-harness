#!/usr/bin/env python3
"""Compatibility wrapper for tools/regen_check.py."""

from __future__ import annotations

from regen_check import main


if __name__ == "__main__":
    raise SystemExit(main())
