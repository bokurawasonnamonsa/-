# Waits until TCP SSH port responds, then runs one-shot deploy (ASCII only).
param(
    [string]$Server = "160.251.140.31",
    [int]$Port = 22,
    [int]$TcpTimeoutMs = 8000,
    [int]$WaitBetweenSec = 25
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root

function Test-TcpOpen {
    param([string]$ComputerName, [int]$SrvPort, [int]$Ms)
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $ar = $client.BeginConnect($ComputerName, $SrvPort, $null, $null)
        $ok = $ar.AsyncWaitHandle.WaitOne($Ms)
        if (-not $ok) { return $false }
        $client.EndConnect($ar)
        return $client.Connected
    } catch {
        return $false
    } finally {
        try { $client.Close() } catch {}
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $root "vps_deploy_local.secret"))) {
    Write-Host "ERROR: missing vps_deploy_local.secret — run SAVE_VPS_SECRET_ONCE.bat first."
    exit 2
}

$py = Join-Path $root "vps_deploy_with_password.py"
if (-not (Test-Path -LiteralPath $py)) {
    Write-Host "ERROR: vps_deploy_with_password.py not found."
    exit 2
}

Write-Host ""
Write-Host "Waiting for SSH port $Server`:${Port} (fix ConoHa NIC security group meanwhile) ..."
Write-Host "Ctrl+C to stop."
Write-Host ""

$attempt = 0
while ($true) {
    $attempt++
    if (Test-TcpOpen -ComputerName $Server -SrvPort $Port -Ms $TcpTimeoutMs) {
        Write-Host "[ok] TCP $Port is open (attempt $attempt)"
        break
    }
    Write-Host "[wait $attempt] $Server`:${Port} no response yet (${TcpTimeoutMs}ms probe). Retry in ${WaitBetweenSec}s ..."
    Start-Sleep -Seconds $WaitBetweenSec
}

Write-Host ""
Write-Host "Running deploy ..."
$proc = Start-Process -FilePath "python" -ArgumentList @("`"$py`"") -WorkingDirectory $root -Wait -PassThru -NoNewWindow
$code = $proc.ExitCode
Write-Host ""
if ($code -eq 0) {
    Write-Host "DEPLOY SUCCESS (exit $code)"
} else {
    Write-Host "DEPLOY FAILED (exit $code) — wrong password/user or remote script error."
}
exit $code
