# Minimal CDA1 (monoclonal antibody) IV Example

A tiny versioned IV fixture for a **long-half-life monoclonal antibody** (CDA1,
an anti-*C. difficile* toxin A mAb; fixture terminal t1/2 ~ 24 days). It exists
to show the *shape* of downstream PK workflow outputs for a biologic, which
differs from the hours-scale small-molecule examples (`minimal_aciclovir`,
`minimal_albuterol_iv`): the sampling schedule spans days to weeks
(0, 1 h, 1, 7, 14, 28, 56, 84 days) so the slow terminal decline is visible.

- Route: intravenous
- Subjects: 2 (trimmed for a minimal, versioned fixture)
- Concentration rows: 16 (8 timepoints x 2 subjects)
- Concentrations decline from ~20,400 ng/mL at dose to ~1,800 ng/mL by day 84
  (~3.5 terminal half-lives).

`sdtm_like/` is the source of truth; `workflow/analysis_inputs/` is regenerated
from it by `make_analysis_inputs` and checked for drift by
`python -m tools.check_examples`.

This is a workflow fixture, not a clinical validation report and not real CDA1
pharmacokinetics.
