# Report Templates

This directory contains optional presentation templates for PK fixture reports.

| File | Role |
| --- | --- |
| `pk_fixture_report.qmd` | Quarto report body template used by `tools/render_pk_fixture_quarto.R` |
| `pk_fixture_reference_source.qmd` | Source used to generate the bundled Word reference document |
| `pk_fixture_reference.docx` | Optional Quarto `reference-doc` for Word styling |

Use the bundled reference document like this:

```bash
Rscript tools/render_pk_fixture_quarto.R \
  --analysis-dir outputs/<run>/workflow/analysis_inputs \
  --out-dir outputs/<run>/workflow/reports/pk_fixture_quarto \
  --title "<slug> PK fixture report" \
  --reference-doc templates/pk_fixture_reference.docx
```

The reference DOCX controls Word styles only. Statistical logic, data selection,
and plots remain in the harness outputs and Quarto source.
