# One-shot checks: TCP/22 + secret file. Log: logs/utc_step_check.log
param(
    [string]$Server = $(if ($env:UTC_VPS_HOST) { $env:UTC_VPS_HOST } else { "160.251.140.31" }),
    [int]$Port = 22,
    [int]$TimeoutMs = 10000
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory $logDir | Out-Null }
$log = Join-Path $logDir "utc_step_check.log"

function Line($s) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $s" | Add-Content -LiteralPath $log -Encoding UTF8
    Write-Host $s
}

function TestTcp([string]$h, [int]$p, [int]$ms) {
    $c = New-Object System.Net.Sockets.TcpClient
    try {
        $ar = $c.BeginConnect($h, $p, $null, $null)
        if (-not $ar.AsyncWaitHandle.WaitOne($ms)) { return $false }
        $c.EndConnect($ar)
        return $c.Connected
    } catch { return $false } finally { try { $c.Close() } catch {} }
}

Line "======== utc_step_check ========="
Line "Step 1: TCP ${Server}:${Port} (timeout ${TimeoutMs} ms)"

$open = TestTcp $Server $Port $TimeoutMs
if ($open) {
    Line "RESULT TCP: OPEN -> next: RUN_PC_AUTO_ALL.bat OR ONECLICK_VPS_DEPLOY.bat"
} else {
    Line "RESULT TCP: CLOSED/TIMEOUT -> ConoHa: SG on NIC OR support ticket"
}

$secret = Join-Path $root "vps_deploy_local.secret"
if (Test-Path -LiteralPath $secret) {
    Line "Step 2: vps_deploy_local.secret: FOUND"
} else {
    Line "Step 2: vps_deploy_local.secret: MISSING -> SAVE_VPS_SECRET_ONCE.bat first"
}

Line "Step 3 Cloudflare DNS: manually check A record 3301-svs.jp -> $Server"

Line "Summary file: logs/utc_steps_summary.txt"
$sum = Join-Path $logDir "utc_steps_summary.txt"
@(
    "TCP_22_OPEN=$open",
    "SECRET_EXISTS=$(Test-Path -LiteralPath $secret)",
    "NEXT=$(if ($open -and (Test-Path -LiteralPath $secret)) { 'RUN_PC_AUTO_ALL.bat' } elseif (-not $open) { 'ConoHa_NIC_SG_or_support' } else { 'SAVE_VPS_SECRET_ONCE.bat' })"
) | Set-Content -LiteralPath $sum -Encoding UTF8

if (-not $open) { exit 1 }
if (-not (Test-Path -LiteralPath $secret)) { exit 2 }
exit 0
