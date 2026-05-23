# This PC does everything except your ConoHa/VPS browser console steps.
# Log: logs/pc_vps_auto.log
param(
    [string]$Server = $(if ($env:UTC_VPS_HOST) { $env:UTC_VPS_HOST } else { "160.251.140.31" }),
    [int]$Port = 22,
    [int]$ProbeMs = 8000,
    [int]$WaitSec = 30,
    [int]$MaxProbes = 0
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $root "logs"
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$log = Join-Path $logDir "pc_vps_auto.log"
$last = Join-Path $logDir "last_tcp22_probe.txt"

function W([string]$m) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $m"
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
    Write-Host $m
}

function Test-TcpOpen([string]$h, [int]$p, [int]$ms) {
    $c = New-Object System.Net.Sockets.TcpClient
    try {
        $ar = $c.BeginConnect($h, $p, $null, $null)
        if (-not $ar.AsyncWaitHandle.WaitOne($ms)) { return $false }
        $c.EndConnect($ar)
        return $c.Connected
    } catch {
        return $false
    } finally {
        try { $c.Close() } catch {}
    }
}

function Resolve-Target([string]$h) {
    try {
        $a = [System.Net.Dns]::GetHostAddresses($h)
        if ($a -and $a.Length -gt 0) {
            return ($a[0].IPAddressToString)
        }
    } catch {}
    return ""
}

# Clear accidental retry env from other batches
$env:UTC_DEPLOY_UNTIL_OK = ""

W "======== PC AUTO: start ========"
W "You: ConoHa Security Group (IN 22,80,443) + attach to THIS VPS NIC; fix in console if needed."
W "This script: probe TCP, log, wait until open, then run python deploy once."
W "Target: ${Server}:${Port}"

$secret = Join-Path $root "vps_deploy_local.secret"
if (-not (Test-Path -LiteralPath $secret)) {
    W "FAIL: vps_deploy_local.secret missing. Run SAVE_VPS_SECRET_ONCE.bat first."
    Set-Content -LiteralPath $last -Value "NO_SECRET" -Encoding UTF8
    exit 2
}

$ip = Resolve-Target $Server
if ($ip) { W "DNS resolves $Server -> $ip" } else { W "DNS: could not resolve (using hostname as-is for TCP)" }

$attempt = 0
while ($true) {
    $attempt++
    $ok = Test-TcpOpen -h $Server -p $Port -ms $ProbeMs
    $state = if ($ok) { "OPEN" } else { "timeout_or_refused" }
    W "probe #$attempt : TCP $Server`:$Port => $state (${ProbeMs}ms)"
    Set-Content -LiteralPath $last -Value "$(Get-Date -Format o) $state" -Encoding UTF8
    if ($ok) { break }
    if ($MaxProbes -gt 0 -and $attempt -ge $MaxProbes) {
        W "STOP: MaxProbes=$MaxProbes reached; port still closed. Exit 3."
        exit 3
    }
    W "waiting ${WaitSec}s ... (edit ConoHa NIC / SG in browser; optional: tcpdump on VPS console)"
    Start-Sleep -Seconds $WaitSec
}

W "TCP OPEN. Deploying..."
$py = Join-Path $root "vps_deploy_with_password.py"
if (-not (Test-Path -LiteralPath $py)) {
    W "FAIL: vps_deploy_with_password.py not found."
    exit 2
}

$proc = Start-Process -FilePath "python" -ArgumentList "`"$py`"" -WorkingDirectory $root -Wait -PassThru -NoNewWindow
$code = $proc.ExitCode
W "deploy finished: exit code $code"

if ($code -eq 0) {
    W "OK: deploy success. Cloudflare A @ -> $Server if not yet (or UPDATE_CLOUDFLARE_DNS.bat with token file)."
    Set-Content -LiteralPath $last -Value "$(Get-Date -Format o) DEPLOY_OK" -Encoding UTF8
} else {
    W "NG: deploy failed (wrong password/user or remote error). See console output above + $log"
    Set-Content -LiteralPath $last -Value "$(Get-Date -Format o) DEPLOY_FAIL_$code" -Encoding UTF8
}

W "Full log: $log"
W "======== PC AUTO: end ========"
exit $code
