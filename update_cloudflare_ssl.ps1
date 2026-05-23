# Sets Cloudflare SSL mode for the zone (e.g. "full" = origin self-signed OK, not strict).
# Requires cloudflare_dns_config.ps1 next to this script (+ token with Zone:SSL Settings:Edit).

$ErrorActionPreference = "Stop"
$cfg = Join-Path $PSScriptRoot "cloudflare_dns_config.ps1"
if (-not (Test-Path -LiteralPath $cfg)) {
    Write-Host "ERROR: Missing cloudflare_dns_config.ps1"
    Write-Host "Copy cloudflare_dns_config.EXAMPLE.ps1 -> cloudflare_dns_config.ps1 and edit."
    exit 2
}
. $cfg

if (-not $CF_API_TOKEN -or $CF_API_TOKEN -like "paste*") {
    Write-Host "ERROR: Set CF_API_TOKEN in cloudflare_dns_config.ps1"
    exit 2
}

$mode = if ($CF_SSL_MODE) { $CF_SSL_MODE.Trim().ToLowerInvariant() } else { "full" }
$allowed = @("off", "flexible", "full", "strict")
if ($allowed -notcontains $mode) {
    Write-Host "ERROR: CF_SSL_MODE must be one of: $($allowed -join ', ')"
    exit 2
}

$headers = @{
    Authorization = "Bearer $CF_API_TOKEN"
    "Content-Type" = "application/json"
}

$zoneUri = "https://api.cloudflare.com/client/v4/zones?name=$([uri]::EscapeDataString($CF_ZONE_NAME))"
$zr = Invoke-RestMethod -Uri $zoneUri -Headers $headers -Method Get
if (-not $zr.success -or $zr.result.Count -lt 1) {
    Write-Host "ERROR: Zone not found or bad token: $($zr.errors | ConvertTo-Json)"
    exit 1
}
$zoneId = $zr.result[0].id

$patchUri = "https://api.cloudflare.com/client/v4/zones/$zoneId/settings/ssl"
$body = @{ value = $mode } | ConvertTo-Json

$pr = Invoke-RestMethod -Uri $patchUri -Headers $headers -Method Patch -Body $body
if (-not $pr.success) {
    Write-Host "ERROR: $($pr.errors | ConvertTo-Json)"
    exit 1
}
Write-Host "OK: SSL mode is now $($pr.result.value) for zone $CF_ZONE_NAME"
