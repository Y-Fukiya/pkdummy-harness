"""Half-life summarisation: harmonic mean support and no silent fall-through.

Before this change, a targets.yml asking for `summary: harmonic_mean` (or
geometric_mean) on t_half silently received the arithmetic mean. That is the kind
of silent default that hides a real statistical choice: the convention for
terminal t1/2 is the harmonic mean (t1/2 = ln2/ke; ke averages arithmetically).
"""

from __future__ import annotations

import math

from tools.validate_simulation import (
    SubjectMetrics,
    _harmonic_mean,
    _target_observed,
    summarize_metrics,
)


def _metrics(half_lives: list[float]) -> dict[str, SubjectMetrics]:
    out: dict[str, SubjectMetrics] = {}
    for i, h in enumerate(half_lives):
        out[str(i)] = SubjectMetrics(
            subject_id=str(i), n_points=5, auc0_last=1.0, auc0_inf=1.0, cmax=1.0,
            tmax_h=1.0, terminal_ke_1_per_h=math.log(2.0) / h, half_life_h=h,
        )
    return out


def test_harmonic_mean_matches_ln2_over_mean_ke() -> None:
    half_lives = [1.0, 2.0, 4.0]
    hm = _harmonic_mean(half_lives)
    mean_ke = sum(math.log(2.0) / h for h in half_lives) / len(half_lives)
    assert math.isclose(hm, math.log(2.0) / mean_ke, rel_tol=1e-12)


def test_ordering_harmonic_le_geomean_le_arithmetic() -> None:
    summary = summarize_metrics(_metrics([1.0, 2.0, 4.0]))
    assert (
        summary["half_life_h_harmonic"]
        <= summary["half_life_h_geomean"]
        <= summary["half_life_h_mean"]
    )


def test_target_observed_selects_requested_summary() -> None:
    summary = summarize_metrics(_metrics([1.0, 2.0, 4.0]))
    assert _target_observed(summary, "t_half", {"summary": "harmonic_mean"}) == summary["half_life_h_harmonic"]
    assert _target_observed(summary, "t_half", {"summary": "geometric_mean"}) == summary["half_life_h_geomean"]
    assert _target_observed(summary, "t_half", {"summary": "median"}) == summary["half_life_h_median"]
    assert _target_observed(summary, "t_half", {"summary": "arithmetic_mean"}) == summary["half_life_h_mean"]


def test_harmonic_mean_no_longer_falls_through_to_arithmetic() -> None:
    summary = summarize_metrics(_metrics([1.0, 2.0, 4.0]))
    # The whole point: requesting harmonic must NOT return the arithmetic mean.
    assert _target_observed(summary, "t_half", {"summary": "harmonic_mean"}) != summary["half_life_h_mean"]
