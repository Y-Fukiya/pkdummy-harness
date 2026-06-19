# Summary

<!-- What changed and why? -->

## Scope

- [ ] Documentation only
- [ ] Tooling / CI / packaging
- [ ] Parser, unit conversion, or generation logic
- [ ] PK library data (`drugs/*`, `INDEX.csv`, `EXCLUDED.csv`, `pk_library.yml`)
- [ ] External validation / site adapter

## PK Data Governance

- [ ] No PK values changed
- [ ] PK values changed, and source/raw/parsed/derived alignment is documented
- [ ] CL/V basis and route handling are unchanged or explicitly explained
- [ ] 70 kg, BSA 1.73 m2, and per-kg unit assumptions are unchanged or tested

## Validation

- [ ] `make validate`
- [ ] `make harness-check`
- [ ] Package build / install smoke, if packaging changed
- [ ] External tool validation, if relevant

## Safety Boundary

- [ ] Generated data are still described as workflow fixtures only
- [ ] No private clinical data, secrets, proprietary datasets, license files, or facility SOPs are included
