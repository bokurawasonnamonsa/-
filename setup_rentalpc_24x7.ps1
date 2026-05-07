$ErrorActionPreference = "Stop"

function Assert-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script in an elevated (Administrator) PowerShell."
    }
}

function Ensure-Command([string]$name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "Command not found: $name"
    }
}

Assert-Admin
Set-Location $PSScriptRoot

Write-Host "=== UTC 24x7 setup start ===" -ForegroundColor Cyan

Ensure-Command "python"
$cloudflaredExe = Join-Path $PSScriptRoot "cloudflared.exe"
if (Test-Path $cloudflaredExe) {
    Write-Host "Using bundled cloudflared: $cloudflaredExe"
} else {
    Ensure-Command "cloudflared"
    $cloudflaredExe = "cloudflared"
}

$versionText = (& $cloudflaredExe --version | Select-Object -First 1)
Write-Host "cloudflared version: $versionText"

Write-Host "[1/5] Configure power settings..."
powercfg /hibernate off | Out-Null
powercfg /change standby-timeout-ac 0 | Out-Null
powercfg /change monitor-timeout-ac 0 | Out-Null
powercfg /change disk-timeout-ac 0 | Out-Null

Write-Host "[2/5] Create logs directory..."
$logDir = Join-Path $PSScriptRoot "logs"
if (-not (Test-Path $logDir)) {
    New-Item -Path $logDir -ItemType Directory | Out-Null
}

Write-Host "[3/5] Run connectivity checks..."
Test-Connection one.one.one.one -Count 4 -ErrorAction Continue | Out-Host
Test-Connection region1.v2.argotunnel.com -Count 4 -ErrorAction Continue | Out-Host

Write-Host "[4/5] Register scheduled task..."
$taskName = "UTC_24x7_AutoStart"
$batchPath = Join-Path $PSScriptRoot "start_system_24x7.bat"
if (-not (Test-Path $batchPath)) {
    throw "Missing file: $batchPath"
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$batchPath`""
$triggerBoot = New-ScheduledTaskTrigger -AtStartup
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1)

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger @($triggerBoot, $triggerLogon) `
    -Settings $settings `
    -RunLevel Highest `
    -User "SYSTEM" | Out-Null

Write-Host "[5/5] Start watchdog batch..."
Start-Process -FilePath $batchPath

Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Green
Write-Host "Scheduled task: $taskName"
Write-Host "Logs: $logDir"
Write-Host "To stop: disable task '$taskName' in Task Scheduler."

