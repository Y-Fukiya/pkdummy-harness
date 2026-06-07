param(
    [string]$Python = "python",
    [string[]]$PythonArgs = @(),
    [switch]$SkipExternalProbe
)

$ErrorActionPreference = "Stop"

$AcceptanceCheck = Join-Path $PSScriptRoot "acceptance-check.ps1"

& $AcceptanceCheck -Python $Python -PythonArgs $PythonArgs -SkipExternalProbe:$SkipExternalProbe
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Release check: OK"
