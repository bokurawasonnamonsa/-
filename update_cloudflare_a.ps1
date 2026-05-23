# Updates one A record on Cloudflare. Requires cloudflare_dns_config.ps1 (gitignored).
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

$headers = @{
    Authorization = "Bearer $CF_API_TOKEN"
    "Content-Type"  = "application/json"
}

$zoneUri = "https://api.cloudflare.com/client/v4/zones?name=$([uri]::EscapeDataString($CF_ZONE_NAME))"
$zr = Invoke-RestMethod -Uri $zoneUri -Headers $headers -Method Get
if (-not $zr.success -or $zr.result.Count -lt 1) {
    Write-Host "ERROR: Zone not found or bad token: $($zr.errors | ConvertTo-Json)"
    exit 1
}
$zoneId = $zr.result[0].id

$recNameEsc = [uri]::EscapeDataString($CF_RECORD_NAME)
$listUri = "https://api.cloudflare.com/client/v4/zones/$zoneId/dns_records?type=A&name=$recNameEsc"
$lr = Invoke-RestMethod -Uri $listUri -Headers $headers -Method Get
if (-not $lr.success -or $lr.result.Count -lt 1) {
    Write-Host "ERROR: No A record named '$CF_RECORD_NAME'. Create it once in dashboard, then re-run."
    exit 1
}
$rec = $lr.result[0]
$id = $rec.id
$body = @{
    type    = "A"
    name    = $rec.name
    content = $CF_TARGET_IP
    ttl     = $rec.ttl
    proxied = $rec.proxied
} | ConvertTo-Json

$patchUri = "https://api.cloudflare.com/client/v4/zones/$zoneId/dns_records/$id"
$pr = Invoke-RestMethod -Uri $patchUri -Headers $headers -Method Patch -Body $body
if (-not $pr.success) {
    Write-Host "ERROR: $($pr.errors | ConvertTo-Json)"
    exit 1
}
Write-Host "OK: A record $($pr.result.name) -> $($pr.result.content) proxied=$($pr.result.proxied)"
