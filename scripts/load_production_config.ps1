# Dot-source: . "$PSScriptRoot\load_production_config.ps1"
$ErrorActionPreference = "Stop"
$script:UtcRepoRoot = Split-Path -Parent $PSScriptRoot
$script:UtcProdConfigPath = Join-Path $UtcRepoRoot "config\production.json"

function Get-UtcProductionConfig {
    if (-not (Test-Path -LiteralPath $script:UtcProdConfigPath)) {
        throw "Missing config/production.json"
    }
    return (Get-Content -LiteralPath $script:UtcProdConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json)
}

function Get-UtcRepoRoot { return $script:UtcRepoRoot }
