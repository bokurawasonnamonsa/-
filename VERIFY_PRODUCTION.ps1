# HTTP smoke test for VPS production (no browser).
param(
    [int]$TimeoutSec = 15,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "scripts\load_production_config.ps1")
$cfg = Get-UtcProductionConfig
$root = Get-UtcRepoRoot
$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$log = Join-Path $logDir "verify_production.log"

function Line([string]$s) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $s"
    Add-Content -LiteralPath $log -Value $line -Encoding UTF8
    Write-Host $s
}

function Test-Url([string]$url) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $TimeoutSec -MaximumRedirection 5
        return @{ Ok = $true; Code = [int]$r.StatusCode; Url = $url; Err = "" }
    } catch {
        $code = 0
        if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
        return @{ Ok = $false; Code = $code; Url = $url; Err = $_.Exception.Message }
    }
}

Line "======== VERIFY_PRODUCTION (mode=$($cfg.mode)) ========"
$targets = @(
    @{ Name = "top"; Url = $cfg.public_url },
    @{ Name = "player"; Url = $cfg.player_url }
)
if ($cfg.player_alt_url) {
    $targets += @{ Name = "player_alt"; Url = $cfg.player_alt_url }
}
if ($cfg.staff_url) {
    $targets += @{ Name = "staff"; Url = $cfg.staff_url }
}

$fail = 0
foreach ($t in $targets) {
    $res = Test-Url $t.Url
    if ($res.Ok -and $res.Code -ge 200 -and $res.Code -lt 400) {
        Line "OK  $($t.Name) $($res.Code) $($t.Url)"
    } else {
        Line "NG  $($t.Name) code=$($res.Code) $($t.Url) err=$($res.Err)"
        $fail++
    }
}

# Optional: confirm DNS resolves to VPS (informational)
try {
    $addrs = [System.Net.Dns]::GetHostAddresses($cfg.domain)
    $ips = ($addrs | ForEach-Object { $_.IPAddressToString }) -join ","
    Line "DNS $domain -> $ips (expected VPS $($cfg.vps_host))"
} catch {
    Line "DNS lookup failed for $($cfg.domain): $($_.Exception.Message)"
}

Line "======== result: fail=$fail ========"
if ($fail -gt 0) { exit 1 }
exit 0
