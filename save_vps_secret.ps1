# Run from SAVE_VPS_SECRET_ONCE.bat. ASCII messages only.
$ErrorActionPreference = 'Stop'

function Fail([string]$msg) {
    Write-Host ""
    Write-Host "ERROR: $msg"
    exit 1
}

try {
    $root = Split-Path -Parent $MyInvocation.MyCommand.Path
    if (-not $root) { Fail "Could not get script folder." }
    Set-Location -LiteralPath $root

    Write-Host ""
    Write-Host "SSH password for the VPS (hidden input, then Enter):"
    $sec = Read-Host "Password" -AsSecureString
    if ($null -eq $sec) { Fail "No password read." }

    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }

    if ([string]::IsNullOrEmpty($plain)) { Fail "Password was empty. Run again and type the password." }

    # Paste mistakes: drop line breaks
    $plain = ($plain -replace "[\r\n]+", "").Trim()
    if ($plain.Length -eq 0) { Fail "Password was empty after cleanup." }

    Write-Host ""
    Write-Host "SSH user [blank = try root then ubuntu]:"
    $user = Read-Host "User (root/ubuntu)"

    $out = Join-Path $root "vps_deploy_local.secret"
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    if ([string]::IsNullOrWhiteSpace($user)) {
        [System.IO.File]::WriteAllText($out, $plain, $utf8NoBom)
    } else {
        $text = $plain + "`n" + $user.Trim()
        [System.IO.File]::WriteAllText($out, $text, $utf8NoBom)
    }

    Write-Host ""
    Write-Host "Saved: $out"
    Write-Host "Keep private. Do not commit to Git."
    exit 0
} catch {
    Write-Host ""
    Write-Host "ERROR (exception): $($_.Exception.Message)"
    exit 1
}
