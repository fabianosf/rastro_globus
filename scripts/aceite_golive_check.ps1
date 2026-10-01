# Checklist tecnico de go-live.
# Uso: .\scripts\aceite_golive_check.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Py = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
    Write-Host "[FAIL] venv ausente" -ForegroundColor Red
    exit 1
}

Push-Location $Backend
try {
    & $Py manage.py aceite_golive
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
