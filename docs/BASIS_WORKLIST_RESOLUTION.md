# Oral CL basis worklist — resolution

All nine oral drugs whose source clearance used a mL/min-family unit have been
re-labelled `clearance_basis: systemic`. In drug labels a mL/min(/kg, /1.73 m2)
or L/min clearance is a systemic (plasma/renal) clearance, not apparent CL/F
(which is conventionally reported in L/h). Provenance is `unit_inferred`: the
call is made from the source *unit*, not verified against full label text. To
upgrade to human-verified, set `clearance_basis_source: confirmed`.

Effect: `CL_systemic` now equals the source value (previously it was the inverted
`CL_abs*F`); `CL_apparent = CL/F` is populated. The spec is untouched, so the
fixture profile is unchanged — only the metadata labelling is corrected. These
remain fixture values, not clinically calibrated PK.

| Drug | raw source CL | F | CL_systemic (L/h) | CL_apparent = CL/F (L/h) |
| --- | --- | ---: | ---: | ---: |
| aciclovir | 327 mL/min/1.73 m2 | 0.1 | 19.62 | 196.2 |
| alprazolam | 0.7-1.5 mL/min/kg | 0.9 | 6.3 | 7 |
| cimetidine | 500 mL/min | 0.65 | 30 | 46.15 |
| felodipine | 1-1.5 L/min | 0.15 | 90 | 600 |
| itraconazole | 278 mL/min | 0.55 | 16.68 | 30.33 |
| montelukast | 30.8 mL/min | 0.615 | 1.848 | 3.005 |
| omeprazole | 624 mL/min (range 59-828 mL/min) | 0.555 | 43.56 | 78.49 |
| triazolam | 526 mL/min | 0.44 | 31.56 | 71.73 |
| verapamil | R-verapamil: 340 mL/min, S-verapamil: 664 mL/min (3週間連続投与後) | 0.275 | 30.12 | 109.5 |
