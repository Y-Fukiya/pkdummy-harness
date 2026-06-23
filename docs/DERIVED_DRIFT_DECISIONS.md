# Resolving derived-block drift: two decisions required before regenerating

`tools/check_derived_drift.py` shows that 27 of 37 committed `pk.yml` files have a
`derived` block that does not match `tools/template_gen.derive_quantities`. A blind
bulk regeneration is unsafe because the divergence is about *conventions*, not just
stale values, and one of those conventions is actively enforced by
`tools/validate_library.py`. Two maintainer decisions are needed first.

## What the library currently looks like

The 37 drugs fall into three groups:

| Group | Count | ke convention | basis persisted | Regenerate as-is? |
| --- | ---: | --- | --- | --- |
| Consistent | 10 | CL/V == ln2/t_half (coincide) | yes | safe (no change) |
| ke-conflict | 19 | ke = ln2/t_half only | no | **breaks validate_library ke check** |
| systemic-loss | 8 | coincide | no | ke ok, but loses CL_systemic/V_systemic |

The "consistent" group (albuterol, apixaban, buprenorphine, carbamazepine,
dapagliflozin, erythromycin, fluconazole, motavizumab_yte, raltegravir, sufentanil)
was produced by the current pipeline and already round-trips.

## Decision 1 — canonical ke convention

Three places disagree:

- committed pk.yml (19 drugs): `ke = ln2 / t_half`
- `derive_quantities`: `ke = CL_abs / V_abs`
- `validate_library`: **enforces** `ke == ln2 / t_half` (hard FAIL otherwise)

These coincide only when `t_half == ln2 * V / CL`, which is exactly the case the
1-compartment attainability warning says is frequently false (e.g. aciclovir:
ln2/t_half = 0.277 vs CL/V = 0.467 per hour).

Recommendation: make **`ke = CL/V` canonical**. The spec/simulator uses CL and V as
the independent parameters (stated in every `targets.yml`: "CL and V are the
independent simulation parameters"), so the ke that actually governs the simulated
profile is CL/V. The literature `t_half` is a check target, not the ke source.
Concretely:

1. change `validate_library` to compare `derived.ke_1_per_h` against `CL_abs/V_abs`
   (not `ln2/t_half`);
2. keep the existing `t_half` vs CL/V attainability WARN — it already captures the
   discrepancy and is the right place for it;
3. then `ke` from `derive_quantities` is correct and the 19 drugs can be regenerated.

If instead `t_half` is meant to be the independent truth, the fix is the reverse
(change `derive_quantities` to set `ke = ln2/t_half`), but that contradicts how the
simulator consumes CL/V and would make derived.ke inconsistent with the generated
concentrations. That is why this is a decision, not a mechanical fix.

## Decision 2 — basis persistence

Only 10/37 persist `pk_parsed.clearance_basis`. Where it is absent,
`derive_quantities` resolves basis to "unknown" and leaves CL_systemic/V_systemic as
`None`, so the route-auto apparent assumption baked into the committed values cannot
be reproduced from `pk.yml` alone.

Recommendation: **persist `clearance_basis` / `volume_basis` into `pk_parsed`** for
all drugs. Backfill the 27 unpersisted ones with the documented route-auto default
(oral -> apparent, iv -> systemic), then let the basis warning added in
`validate_library` (systemic-style source unit on an oral drug) flag the cases that
need manual review (aciclovir, alprazolam, cimetidine, felodipine, itraconazole,
montelukast, omeprazole, triazolam, verapamil). This makes the basis explicit and
auditable, kills the silent default, and makes regeneration deterministic.

## After both decisions: safe regeneration path

1. Implement Decision 1 in `validate_library` (ke vs CL/V) and Decision 2
   (persist basis) in the harvest/template path.
2. Add a `--write` mode to a regen tool that recomputes `derived` from
   `pk_parsed` (now including basis) via `derive_quantities`, in place.
3. Run `python tools/check_derived_drift.py . --strict` — it should report zero
   drift, and wire it into `make harness-check` / CI so drift cannot reappear.
4. Re-run `tools/validate_library.py` and the full test suite; the basis warnings
   should remain (they are warnings, not failures), and the ground-truth NCA test
   is unaffected (it reads spec theta, not the derived block).

`check_derived_drift.py --strict` is the lock; until Decisions 1 and 2 are made it
stays informational (exit 0) so it does not break CI.
