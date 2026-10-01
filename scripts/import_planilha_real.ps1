# Importa BASE GERAL real (dry-run + load).
# Uso:
#   .\scripts\import_planilha_real.ps1
#   .\scripts\import_planilha_real.ps1 -Path "C:\caminho\GARANTIA-2026.xlsx"
#   .\scripts\import_planilha_real.ps1 -Path "..." -SkipLoad   # so dry-run

param(
    [string]$Path = "",
    [switch]$SkipLoad
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Incoming = Join-Path $Root "docs\ops\incoming"
$Py = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
    throw "Python venv nao encontrado: $Py"
}

if (-not $Path) {
    $found = Get-ChildItem -Path $Incoming -File -Include *.xlsx, *.xls -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $found) {
        $found = Get-ChildItem -Path $Incoming -File -Filter *.xlsx -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
    }
    if (-not $found) {
        Write-Host @"
BLOQUEADO: nenhum .xlsx em docs\ops\incoming\

Coloque o arquivo oficial BASE GERAL (ex.: GARANTIA-2026.xlsx) nessa pasta e rode de novo:
  .\scripts\import_planilha_real.ps1

Ou informe o caminho:
  .\scripts\import_planilha_real.ps1 -Path 'D:\dados\GARANTIA-2026.xlsx'
"@
        exit 2
    }
    $Path = $found.FullName
}

if (-not (Test-Path $Path)) {
    throw "Arquivo nao encontrado: $Path"
}

Write-Host "=== Dry-run ==="
Write-Host "Arquivo: $Path"
Push-Location $Backend
try {
    & $Py manage.py import_planilha $Path --dry-run
    if ($LASTEXITCODE -ne 0) { throw "dry-run falhou (exit $LASTEXITCODE)" }

    if ($SkipLoad) {
        Write-Host "SkipLoad: import real nao executado."
        exit 0
    }

    Write-Host "=== Load ==="
    & $Py manage.py import_planilha $Path
    if ($LASTEXITCODE -ne 0) { throw "import falhou (exit $LASTEXITCODE)" }

    & $Py manage.py shell -c "from apps.core.models import HistoricoGarantiaMensal; print('historico_rows', HistoricoGarantiaMensal.objects.count())"
}
finally {
    Pop-Location
}

Write-Host "OK: planilha processada."
