# Minimal Albuterol IV Example

This is a tiny versioned IV fixture for checking the shape of downstream PK workflow outputs.

It is intentionally small:

- 2 subjects
- IV dosing
- 2 concentration time points per subject
- DM / VS / LB / EX / PC source CSVs under `sdtm_like/`
- regenerated analysis outputs under `workflow/analysis_inputs/`

Use it to understand output columns and to run `make examples-check`. It is not a clinical validation dataset.
