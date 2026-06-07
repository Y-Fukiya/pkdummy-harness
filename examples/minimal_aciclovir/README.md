# Minimal Aciclovir Example

This directory contains tiny versioned example artifacts for explaining the
fixture harness without committing full `outputs/` runs.

The example is intentionally small:

- 2 subjects
- 2 concentration time points per subject
- ADPC-like, NCA, and PopPK smoke-test CSVs
- one lightweight Markdown report

These files are educational fixtures only. They are not clinical validation
outputs and are not submission-ready SDTM or ADaM datasets.

To generate real demo outputs, run:

```bash
python3 tools/run_harness.py harness_examples/demo_set.yml
```
