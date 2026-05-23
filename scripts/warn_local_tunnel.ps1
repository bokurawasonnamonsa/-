# Warn or block local tunnel when production mode is VPS-only.
param([switch]$Strict)

. (Join-Path $PSScriptRoot "load_production_config.ps1")
$cfg = Get-UtcProductionConfig
if ($cfg.mode -ne "vps") { exit 0 }

if ($env:UTC_ALLOW_LOCAL_TUNNEL -eq "1") { exit 0 }

$msg = @"
[UTC] 本番は VPS 一本化です (config/production.json).
      ローカル cloudflared / python 本番起動は使わないでください。
      デプロイ: DEPLOY_PRODUCTION.bat
      検証: VERIFY_PRODUCTION.bat
      ローカル停止: STOP_LOCAL_PRODUCTION.bat
"@

Write-Host $msg
if ($Strict -or $cfg.local_tunnel_allowed -eq $false) {
    if ($Strict) { exit 3 }
}
exit 0
