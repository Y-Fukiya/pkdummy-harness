# Security Policy

## Supported Versions

Security fixes are handled on the default branch. Tagged releases are snapshots for reproducible fixture workflows.

## Reporting a Vulnerability

Please report security issues through GitHub's private vulnerability reporting or by opening a GitHub Security Advisory for this repository.

Do not include secrets, private clinical data, or proprietary datasets in public issues. This project should not require real patient data.

## Data Safety Scope

`pkdummy-harness` is intended for synthetic PK-like workflow fixtures. It is not a clinical decision support system and must not be used for dose selection, clinical inference, or regulatory model qualification.

If you find a problem that could cause users to mistake generated fixtures for validated clinical predictions, please report it as a safety-sensitive issue.
