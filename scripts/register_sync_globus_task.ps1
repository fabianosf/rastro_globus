# Registra tarefa agendada Windows para sync_globus diario (06:30).
# Executar PowerShell como Administrador na primeira vez:
#   .\scripts\register_sync_globus_task.ps1

param(
    [string]$TaskName = "RastroGlobus-SyncGlobus",
    [string]$Time = "06:30",
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Job = Join-Path $Root "scripts\sync_globus_job.ps1"

if ($Unregister) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Tarefa removida: $TaskName"
    exit 0
}

if (-not (Test-Path $Job)) { throw "Script nao encontrado: $Job" }

$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$Job`" -DetectarReincidencia"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "OK: tarefa '$TaskName' diaria as $Time"
Write-Host "Job: $Job"
Write-Host "Logs: $Root\logs\sync_globus_YYYYMMDD.log"
Write-Host "Teste manual: powershell -File `"$Job`""
