# Review Follow-up Status

この文書は、公開リポジトリ化前後の厳しめレビュー指摘に対する現在の対応状況を記録します。
古い実装指示をそのまま残すと、未解決問題と完了済み機能が混ざって第三者レビューを混乱させるため、
ここでは **done / tracked / external** を明確に分けます。

このリポジトリは workflow fixture generator です。PK truth source、臨床推論、投与設計、
規制提出用モデル妥当化の証拠としては扱いません。

## Current Triage

| Review item | Status | Current evidence | Remaining action |
| --- | --- | --- | --- |
| IV infusion handling | Done | `tools/run_demo_set.py` uses `infusion_h` for IV infusion equations; `tools/make_analysis_inputs.py` emits PopPK `RATE`; tests cover both paths | Keep regression tests when changing regimen logic |
| t1/2 vs CL/V structural mismatch labeling | Done, now machine-readable in `targets.yml` and workflow manifests | `targets.yml` carries `structural_mismatch.acknowledged`; run-level `MANIFEST.yml` includes `detected_structural_mismatch`, `acknowledged_structural_mismatch`, `relative_error`, and `attainability_status` | Do not auto-fix PK values; use source review before changing canonical data |
| AUC target circularity | Done, now machine-readable in `targets.yml` and workflow manifests | `targets.yml` carries `basis`, `target_basis`, `independent_literature_target`, `source_value`, and `role`; run-level `MANIFEST.yml` mirrors these under `target_metadata.auc` | Replace `targets.auc` only when a literature AUC has source/raw text/unit conversion evidence |
| BLQ / LLOQ fixture support | Done for fixture contract | `assay.lloq` creates SDTM-like BLQ flags and PopPK `BLQ/CENS/LIMIT`; tests cover SDTM-like and analysis inputs | External M3 likelihood execution remains tool/environment-specific |
| Demo IIV/residual meaning | Done | `docs/SCHEMA.md` and `docs/USER_GUIDE.md` distinguish demo-only variability from model-specific external runner behavior | Revisit only if full stochastic model execution is added |
| Predose convention | Done | Default predose remains `DV=0/MDV=0`; `--predose-mdv1` is available and tested | Site-specific PopPK adapters may still choose another convention |
| Covariate / absorption scope | Done | Docs state demographic covariates are fixture attributes, not a justified covariate model | Add model-specific covariate support only behind explicit schema/tests |
| SC/IM route guard | Done | Demo generator treats SC/IM as first-order absorption and rejects unknown routes instead of silently using bolus | Do not broaden route support without tests |
| Interpolation / sorting intent | Done | `linear` and `log-linear` behavior is documented; tests cover log-linear sampling | Formal NCA interpolation remains downstream-tool scope |
| Package vs checkout UX | Tracked | README states this is a git-checkout tool; wheel/sdist ship code only and not the drug library | Decide separately if the project should become a fully installable data package |
| Value-level provenance | Tracked | `pk.yml` stores sources/raw/parsed/derived, but value-to-source snippets and reviewer status are not uniformly normalized | Improve one drug at a time with source/raw text/unit conversion/reviewer evidence |
| External Phoenix/NONMEM/nlmixr2 execution | External | Probe/smoke paths exist; real execution needs licensed/local environments | Track in `docs/READINESS_GAPS.md` and release notes |
| Independent README-only user test | External | Checklist/template exists | Needs a third-party tester, not Codex |

## Machine-readable Fields

Run-level workflow manifests now carry target provenance and structural mismatch metadata:

```yaml
target_metadata:
  parameter_pair_policy: spec_theta_uses_pk_yml_derived_cl_v_abs
  auc:
    basis: dose_over_cl
    target_basis: dose_over_cl_not_literature_auc
    independent_literature_target: false
  t_half:
    basis: literature_target_retained_as_check
    detected_structural_mismatch: true
    acknowledged_structural_mismatch: true
    attainability_status: WARN
    relative_error: 0.406
```

These fields are run metadata. They do not rewrite `pk.yml`, `targets.yml`, or `spec_pk1_*.yml`.

## Rules For Future Fixes

- Do not change PK numeric values without source text, conversion formula, units, and reviewer rationale.
- Treat `Dose/CL` AUC as an integration consistency target, not as independent literature validation.
- Treat `detected_structural_mismatch: true` as a computed fixture limitation, not as permission to silently recalibrate CL, V, or t1/2.
- Treat `acknowledged_structural_mismatch: true` as a human-reviewed fixture policy label, not as clinical validation.
- Keep external tool execution claims separate from parser/probe smoke checks.
