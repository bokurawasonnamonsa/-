# Pre/post deploy checks: secret, TCP/22, HTTP, local tunnel processes.
param([switch]$SkipDeploy)

$ErrorActionPreference = "Continue"
. (Join-Path $PSScriptRoot "scripts\load_production_config.ps1")
$cfg = Get-UtcProductionConfig
$root = Get-UtcRepoRoot
$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$report = Join-Path $logDir "qa_production_report.txt"

function W([string]$s) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $s"
    Add-Content -LiteralPath $report -Value $line -Encoding UTF8
    Write-Host $s
}

"" | Set-Content -LiteralPath $report -Encoding UTF8
W "======== QA PRODUCTION CHECK ========"
W "mode=$($cfg.mode) host=$($cfg.vps_host) url=$($cfg.public_url)"

# 1) Secret
$secret = Join-Path $root "vps_deploy_local.secret"
if (Test-Path -LiteralPath $secret) { W "OK  vps_deploy_local.secret exists" }
else { W "NG  vps_deploy_local.secret MISSING -> run SAVE_VPS_SECRET_ONCE.bat" }

# 2) Local tunnel should not run in VPS mode
$py = Get-Process python -ErrorAction SilentlyContinue
$cf = Get-Process cloudflared -ErrorAction SilentlyContinue
if ($py) { W "WARN local python running (count=$($py.Count)) -> STOP_LOCAL_PRODUCTION.bat" }
else { W "OK  no local python" }
if ($cf) { W "WARN cloudflared running (count=$($cf.Count)) -> STOP_LOCAL_PRODUCTION.bat" }
else { W "OK  no cloudflared" }

# 3) SSH port
function Test-Tcp([string]$h, [int]$p, [int]$ms) {
    $c = New-Object System.Net.Sockets.TcpClient
    try {
        $ar = $c.BeginConnect($h, $p, $null, $null)
        if (-not $ar.AsyncWaitHandle.WaitOne($ms)) { return $false }
        $c.EndConnect($ar)
        return $c.Connected
    } catch { return $false } finally { try { $c.Close() } catch {} }
}
$sshOk = Test-Tcp $cfg.vps_host ([int]$cfg.vps_ssh_port) 8000
if ($sshOk) { W "OK  TCP $($cfg.vps_host):$($cfg.vps_ssh_port)" }
else { W "NG  TCP $($cfg.vps_host):$($cfg.vps_ssh_port) closed" }

# 4) HTTP
$verify = Join-Path $root "VERIFY_PRODUCTION.ps1"
if (Test-Path -LiteralPath $verify) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $verify
    if ($LASTEXITCODE -eq 0) { W "OK  VERIFY_PRODUCTION passed" }
    else { W "NG  VERIFY_PRODUCTION failed (exit $LASTEXITCODE)" }
}

W "Report: $report"
W "Browser QA: use .cursor/rules/vps-production.mdc checklist on $($cfg.player_url)"
exit 0
