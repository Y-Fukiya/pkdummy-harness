PYTHON ?= python3

.PHONY: all validate test regen-check regen-index-check codex-check harness-check index excluded-summary clean

all: harness-check

validate:
	$(PYTHON) tools/validate_library.py .
	$(PYTHON) tools/codex_harness_check.py .

test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m pytest -q -p no:cacheprovider

regen-check:
	$(PYTHON) tools/regen_check.py .

regen-index-check:
	$(PYTHON) tools/regen_index_check.py .

codex-check:
	$(PYTHON) tools/codex_harness_check.py .

harness-check: clean validate test regen-check
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
	find . -type f \( -name '*.pyc' -o -name '.DS_Store' -o -name '._*' \) -delete
