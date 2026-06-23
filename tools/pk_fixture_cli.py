#!/usr/bin/env python3
"""Unified CLI entrypoint for the PK fixture harness.

This module is intentionally thin: each subcommand delegates to an existing
tool module so the CLI, Codex, and Claude Code paths share one implementation.
"""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CommandSpec:
    module: str
    summary: str


COMMANDS: dict[str, CommandSpec] = {
    "doctor": CommandSpec("tools.doctor", "Check local Python/R/Quarto/simPop readiness."),
    "run": CommandSpec("tools.run_harness", "Run a harness YAML config."),
    "workflow": CommandSpec("tools.run_workflow", "Run post-simulation validate/sample/SDTM-like/analysis workflow."),
    "validate-simulation": CommandSpec("tools.validate_simulation", "Recalculate AUC/Cmax/Tmax/t1/2 from sim_full.csv."),
    "validate-config": CommandSpec("tools.validate_harness_config", "Validate a run_harness YAML config."),
    "sample-timepoints": CommandSpec("tools.sample_clinical_timepoints", "Sample dense simulation output at nominal clinical times."),
    "make-sdtm": CommandSpec("tools.make_sdtm_like_domains", "Generate limited SDTM-like DM/VS/LB/EX/PC CSVs."),
    "make-analysis": CommandSpec("tools.make_analysis_inputs", "Generate ADPC/NCA/PopPK smoke-test input CSVs."),
    "downstream-smoke": CommandSpec("tools.run_downstream_smoke", "Run downstream NCA/PopPK parser smoke checks."),
    "site-adapter": CommandSpec("tools.make_site_adapters", "Generate site-specific adapter CSVs from a YAML mapping."),
    "external-validation": CommandSpec("tools.run_external_tool_validation", "Probe or run optional Phoenix/NONMEM/nlmixr2 profiles."),
    "manifest-viewer": CommandSpec("tools.render_manifest_viewer", "Render a MANIFEST.yml to a static HTML viewer."),
    "examples-check": CommandSpec("tools.check_examples", "Regenerate versioned examples in a temp dir and compare."),
    "audit-library": CommandSpec("tools.audit_library_priorities", "Read-only internal-first library priority audit."),
}


def _help_text() -> str:
    width = max(len(name) for name in COMMANDS)
    lines = [
        "pk_fixture_cli: CLI entrypoint for pkdummy-harness",
        "",
        "Usage:",
        "  python -m tools.pk_fixture_cli <command> [args...]",
        "  (run from the repository root)",
        "",
        "Commands:",
    ]
    for name, spec in COMMANDS.items():
        lines.append(f"  {name:<{width}}  {spec.summary}")
    lines.extend(
        [
            "",
            "Examples:",
            "  python -m tools.pk_fixture_cli doctor",
            "  python -m tools.pk_fixture_cli run harness_examples/demo_set.yml",
            "  python -m tools.pk_fixture_cli workflow --sim-full outputs/<run>/raw/sim_full.csv --drug aciclovir --times 0,1,2 --out-dir outputs/<run>/workflow",
            "",
            "Boundary:",
            "  Generated data are workflow fixtures, not clinical inference or dose-selection evidence.",
        ]
    )
    return "\n".join(lines)


def _load_main(module_name: str) -> Callable[[list[str] | None], int]:
    module = importlib.import_module(module_name)
    main = getattr(module, "main", None)
    if not callable(main):
        raise RuntimeError(f"{module_name} does not expose a callable main(argv)")
    return main


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(_help_text())
        return 0

    command = args[0]
    if command not in COMMANDS:
        print(f"ERROR: unknown command: {command}", file=sys.stderr)
        print("", file=sys.stderr)
        print(_help_text(), file=sys.stderr)
        return 2

    main_func = _load_main(COMMANDS[command].module)
    return int(main_func(args[1:]) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
