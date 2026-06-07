param(
    [string]$Python = "python",
    [string[]]$PythonArgs = @(),
    [switch]$SkipExternalProbe
)

$ErrorActionPreference = "Stop"

$HarnessCheck = Join-Path $PSScriptRoot "harness-check.ps1"

# Equivalent to: ./harness-check.ps1
& $HarnessCheck -Python $Python -PythonArgs $PythonArgs -SkipExternalProbe:$SkipExternalProbe
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "==> doctor"
& $Python @PythonArgs "tools/doctor.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "PowerShell acceptance check: OK"
