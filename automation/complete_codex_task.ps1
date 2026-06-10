param(
    [Parameter(Mandatory=$true)]
    [string]$TaskName,

    [string]$Details = ""
)

$repoRoot = Resolve-Path "$PSScriptRoot\.."
$logFile = Join-Path $PSScriptRoot "codex_completion.log"
$notify = Join-Path $PSScriptRoot "notify_claude.ps1"

if ([string]::IsNullOrWhiteSpace($Details)) {
    $message = "$TaskName complete"
} else {
    $message = "$TaskName complete. $Details"
}

$line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8

& powershell -NoProfile -ExecutionPolicy Bypass -File $notify -Message $message

if ($LASTEXITCODE -ne 0) {
    Write-Error "Claude notification failed for: $TaskName"
    exit $LASTEXITCODE
}

Write-Host "[complete_codex_task] $message"
