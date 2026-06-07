param(
    [string]$Python = "python",
    [string[]]$PythonArgs = @(),
    [switch]$SkipExternalProbe
)

$ErrorActionPreference = "Stop"

function Invoke-PythonStep {
    param(
        [string]$Name,
        [string[]]$StepArgs
    )
    Write-Host "==> $Name"
    & $Python @PythonArgs @StepArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed with exit code ${LASTEXITCODE}: $Name"
    }
}

function Clear-HarnessJunk {
    Write-Host "==> clean transient files"
    Get-ChildItem -Path "." -Recurse -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @("__pycache__", ".pytest_cache") -or $_.Name -like "*.egg-info" } |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path "." -Recurse -File -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq ".DS_Store" -or $_.Name -like "._*" -or $_.Extension -eq ".pyc" } |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

Clear-HarnessJunk

Invoke-PythonStep -Name "validate_library" -StepArgs @("tools/validate_library.py", ".")
Invoke-PythonStep -Name "codex_harness_check" -StepArgs @("tools/codex_harness_check.py", ".")

$env:PYTHONDONTWRITEBYTECODE = "1"
# Equivalent to: python -m pytest -q -p no:cacheprovider
Invoke-PythonStep -Name "pytest" -StepArgs @("-m", "pytest", "-q", "-p", "no:cacheprovider")

Invoke-PythonStep -Name "regen_check" -StepArgs @("tools/regen_check.py", ".")

# Equivalent to: python -m tools.pk_fixture_cli --help
Invoke-PythonStep -Name "pk-fixture help" -StepArgs @("-m", "tools.pk_fixture_cli", "--help")
# Equivalent to: python -m tools.pk_fixture_cli doctor --json
Invoke-PythonStep -Name "pk-fixture doctor json" -StepArgs @("-m", "tools.pk_fixture_cli", "doctor", "--json")

Invoke-PythonStep -Name "examples_check" -StepArgs @("tools/check_examples.py", "examples")
Invoke-PythonStep -Name "downstream_smoke minimal_aciclovir" -StepArgs @(
    "tools/run_downstream_smoke.py",
    "--analysis-dir", "examples/minimal_aciclovir/workflow/analysis_inputs",
    "--out-dir", "outputs/downstream_smoke_check/minimal_aciclovir"
)
Invoke-PythonStep -Name "downstream_smoke minimal_albuterol_iv" -StepArgs @(
    "tools/run_downstream_smoke.py",
    "--analysis-dir", "examples/minimal_albuterol_iv/workflow/analysis_inputs",
    "--out-dir", "outputs/downstream_smoke_check/minimal_albuterol_iv"
)
Invoke-PythonStep -Name "site_adapter minimal_aciclovir" -StepArgs @(
    "tools/make_site_adapters.py",
    "--analysis-dir", "examples/minimal_aciclovir/workflow/analysis_inputs",
    "--spec-yml", "external_validation/site_adapter_template.yml",
    "--out-dir", "outputs/site_adapter_check/minimal_aciclovir"
)

if ($SkipExternalProbe) {
    Write-Host "==> external validation probe skipped"
} else {
    Invoke-PythonStep -Name "external_validation_probe minimal_aciclovir" -StepArgs @(
        "tools/run_external_tool_validation.py",
        "--downstream-dir", "outputs/downstream_smoke_check/minimal_aciclovir",
        "--out-dir", "outputs/external_validation_probe/minimal_aciclovir"
    )
}

Clear-HarnessJunk
Invoke-PythonStep -Name "final codex_harness_check" -StepArgs @("tools/codex_harness_check.py", ".")

Write-Host "PowerShell harness check: OK"
