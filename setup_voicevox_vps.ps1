$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot "vps_deploy_local.secret"))) {
    Write-Host "ERROR: missing vps_deploy_local.secret"
    Write-Host "Run SAVE_VPS_SECRET_ONCE.bat first."
    exit 2
}

python "$PSScriptRoot\voicevox_setup_vps.py"
exit $LASTEXITCODE
