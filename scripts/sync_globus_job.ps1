# Job de sync Globus (somente leitura Oracle) + opcional deteccao de reincidência.
# Agendado via register_sync_globus_task.ps1

param(
    [switch]$Full,
    [string]$Tipo = "",
    [switch]$DetectarReincidencia
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Py = Join-Path $Backend ".venv\Scripts\python.exe"
$LogDir = Join-Path $Root "logs"
$Log = Join-Path $LogDir ("sync_globus_{0:yyyyMMdd}.log" -f (Get-Date))

if (-not (Test-Path $Py)) { throw "venv nao encontrado: $Py" }
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log([string]$msg) {
    $line = "{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $msg
    Add-Content -Path $Log -Value $line
    Write-Host $line
}

Write-Log "START sync_globus full=$Full tipo=$Tipo"
Push-Location $Backend
try {
    $args = @("manage.py", "sync_globus")
    if ($Full) { $args += "--full" }
    if ($Tipo) { $args += @("--tipo", $Tipo) }

    & $Py @args 2>&1 | ForEach-Object { Write-Log "$_" }
    if ($LASTEXITCODE -ne 0) { throw "sync_globus exit $LASTEXITCODE" }

    if ($DetectarReincidencia) {
        Write-Log "START detectar_reincidencia"
        & $Py manage.py detectar_reincidencia 2>&1 | ForEach-Object { Write-Log "$_" }
        if ($LASTEXITCODE -ne 0) { throw "detectar_reincidencia exit $LASTEXITCODE" }
    }

    Write-Log "OK"
    exit 0
}
catch {
    Write-Log "ERRO: $_"
    exit 1
}
finally {
    Pop-Location
}
