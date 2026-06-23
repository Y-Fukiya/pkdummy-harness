PYTHON ?= python3

.PHONY: all validate test regen-check derived-drift-check calibrated-profiles-check regen-index-check codex-check cli-check examples-check downstream-check site-adapter-check external-validation-probe doctor acceptance-check release-check harness-check index excluded-summary clean

all: harness-check

validate:
	$(PYTHON) tools/validate_library.py .
	$(PYTHON) tools/codex_harness_check.py .

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest -q -p no:cacheprovider

regen-check:
	$(PYTHON) tools/regen_check.py .

derived-drift-check:
	$(PYTHON) tools/check_derived_drift.py . --strict

calibrated-profiles-check:
	$(PYTHON) tools/make_calibrated_oral_spec.py . --check

regen-index-check:
	$(PYTHON) tools/regen_index_check.py .

codex-check:
	$(PYTHON) tools/codex_harness_check.py .

cli-check:
	$(PYTHON) -m tools.pk_fixture_cli --help
	$(PYTHON) -m tools.pk_fixture_cli doctor --json

examples-check:
	$(PYTHON) tools/check_examples.py examples

downstream-check:
	$(PYTHON) tools/run_downstream_smoke.py --analysis-dir examples/minimal_aciclovir/workflow/analysis_inputs --out-dir outputs/downstream_smoke_check/minimal_aciclovir
	$(PYTHON) tools/run_downstream_smoke.py --analysis-dir examples/minimal_albuterol_iv/workflow/analysis_inputs --out-dir outputs/downstream_smoke_check/minimal_albuterol_iv

site-adapter-check:
	$(PYTHON) tools/make_site_adapters.py --analysis-dir examples/minimal_aciclovir/workflow/analysis_inputs --spec-yml external_validation/site_adapter_template.yml --out-dir outputs/site_adapter_check/minimal_aciclovir

external-validation-probe:
	$(PYTHON) tools/run_external_tool_validation.py --downstream-dir outputs/downstream_smoke_check/minimal_aciclovir --out-dir outputs/external_validation_probe/minimal_aciclovir

doctor:
	$(PYTHON) tools/doctor.py

acceptance-check: harness-check
	$(MAKE) doctor

release-check: acceptance-check
	@echo "release-check includes make acceptance-check"
	$(PYTHON) -m tools.pk_fixture_cli --help
	$(PYTHON) -m tools.pk_fixture_cli doctor --json

harness-check: clean validate test regen-check derived-drift-check calibrated-profiles-check cli-check examples-check downstream-check site-adapter-check external-validation-probe
	$(MAKE) clean
	$(PYTHON) tools/codex_harness_check.py .

index:
	$(PYTHON) tools/rebuild_index.py .
	$(PYTHON) tools/validate_library.py .
	$(PYTHON) tools/codex_harness_check.py .

excluded-summary:
	$(PYTHON) tools/summarize_excluded.py --excluded EXCLUDED.csv --out-md reports/excluded_summary.md

clean:
	find . -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
	find . -maxdepth 2 -type d -name '*.egg-info' -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '.DS_Store' -o -name '._*' \) -delete
