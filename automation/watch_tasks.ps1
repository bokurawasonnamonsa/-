# watch_tasks.ps1
# Unified watcher for the Claude -> Cursor -> Codex -> Claude loop.
#
# NEW file in cursor_tasks/   -> open in Cursor (Claude->Cursor trigger)
# CHANGED file: Status: Done  -> post to Codex  (Cursor->Codex trigger)

$watchDir = "$PSScriptRoot\..\commercial\codex_ops\cursor_tasks"
$watchDir = (Resolve-Path $watchDir).Path
$outDir   = "$PSScriptRoot\..\commercial\codex_ops\codex_ready"
$logFile = "$PSScriptRoot\watch_tasks.log"
$openedStateFile = "$PSScriptRoot\watch_opened_tasks.txt"
$doneStateFile = "$PSScriptRoot\watch_done_tasks.txt"

if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

. "$PSScriptRoot\send_to_app.ps1"

$cursorCmd = "C:\Users\jarauser0\AppData\Local\Programs\cursor\resources\app\bin\cursor.cmd"

Write-Host "[watch_tasks] Watching: $watchDir"
Write-Host "[watch_tasks] Codex instructions -> $outDir"
Write-Host "[watch_tasks] Press Ctrl+C to stop."

function Write-Log($message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $message
    Write-Host $line
    Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
}

function Test-StateLine($file, $line) {
    if (-not (Test-Path $file)) { return $false }
    return [bool](Select-String -LiteralPath $file -SimpleMatch $line -Quiet)
}

function Add-StateLine($file, $line) {
    if (-not (Test-StateLine $file $line)) {
        Add-Content -LiteralPath $file -Value $line -Encoding UTF8
    }
}

function Test-StateContains($file, $text) {
    if (-not (Test-Path $file)) { return $false }
    return [bool](Select-String -LiteralPath $file -SimpleMatch $text -Quiet)
}

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path   = $watchDir
$watcher.Filter = "*.md"
$watcher.NotifyFilter = [System.IO.NotifyFilters]::LastWrite -bor [System.IO.NotifyFilters]::FileName
$watcher.EnableRaisingEvents = $true

# ── helpers ──────────────────────────────────────────────────────────────────

function Test-TaskDone($content) {
    return ($content -match '(?im)^\s*\*\*Status:\*\*\s*Done\s*$' -or
            $content -match '(?im)^\s*Status:\s*Done\s*$')
}

function Test-TaskReady($content) {
    return ($content -match '(?im)^\s*\*\*Status:\*\*\s*(Ready|Todo|Doing|In Progress)\s*$' -or
            $content -match '(?im)^\s*Status:\s*(Ready|Todo|Doing|In Progress)\s*$')
}

function Escape-ToastText($text) {
    return [System.Security.SecurityElement]::Escape($text)
}

function Show-Notification($title, $body) {
    try {
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        $xml = [Windows.Data.Xml.Dom.XmlDocument]::new()
        $xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>$(Escape-ToastText $title)</text><text>$(Escape-ToastText $body)</text></binding></visual></toast>")
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("TactNode Watcher").Show($toast)
    } catch {
        Write-Host "[watch_tasks] Notification skipped: $($_.Exception.Message)"
    }
}

function Open-InCursor($path) {
    $stateLine = (Resolve-Path -LiteralPath $path).Path
    if (Test-StateLine $openedStateFile $stateLine) {
        Write-Log "Already opened in Cursor, skipping: $(Split-Path $path -Leaf)"
        return
    }
    Add-StateLine $openedStateFile $stateLine

    if (Test-Path $cursorCmd) {
        Start-Process "cmd.exe" -ArgumentList "/c `"$cursorCmd`" `"$path`"" -WindowStyle Hidden
        Write-Log "Opened in Cursor: $(Split-Path $path -Leaf)"
        Show-Notification "Cursor task ready" (Split-Path $path -Leaf)

        # Cursor の auto-cursor-tasks.mdc ルールがファイルを開いた瞬間に自動実行する。
        # UI送信は不要（誤送信の原因になるため廃止）。
    } else {
        Write-Log "cursor.cmd not found at: $cursorCmd"
    }
}

function Build-CodexMessage($taskFile) {
    $name    = [System.IO.Path]::GetFileNameWithoutExtension($taskFile)
    $content = Get-Content $taskFile -Raw
    $titleMatch = [regex]::Match($content, '^#\s+(.+)', 'Multiline')
    $title   = if ($titleMatch.Success) { $titleMatch.Groups[1].Value.Trim() } else { $name }

    $outFile = Join-Path $outDir "$name`_codex.md"
    @"
# Codex Instruction - $title

Cursor has marked the task as Done. Please perform the Codex-owned final steps.

## Source Task

commercial/codex_ops/cursor_tasks/$name.md

## Requested Codex Work

1. Review the Cursor changes and confirm they match the task.
2. Run the required build and verification commands.
3. If this is an Android release task, build the signed AAB.
4. Upload the AAB to Google Play internal testing when the task requires release.
5. Add release notes from the task file or from the latest BUILD_STATUS.md.
6. Publish the internal test release.
7. Update TASK_BOARD.md and relevant status docs after completion.
8. When complete, notify Claude with:

powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\jarauser0\Desktop\utc_web\automation\notify_claude.ps1" -Message "$title complete"

## Important

- Do not touch commercial/secrets/.
- Do not revert unrelated work.

---
Generated by automation/watch_tasks.ps1
"@ | Set-Content $outFile -Encoding UTF8

    $shortMsg = "Cursor task Done: $title`nRun steps from: commercial/codex_ops/codex_ready/$name`_codex.md`nAfter completion run: powershell -NoProfile -ExecutionPolicy Bypass -File `"C:\Users\jarauser0\Desktop\utc_web\automation\notify_claude.ps1`" -Message `"$title complete`""
    return @{ File = $outFile; Message = $shortMsg }
}

# ── event handlers ────────────────────────────────────────────────────────────

$script:processed     = @{}
$script:openedInCursor = @{}

# New file created -> open in Cursor (unless already Done)
$onCreate = {
    $path = $Event.SourceEventArgs.FullPath
    Start-Sleep -Milliseconds 800
    if (-not (Test-Path $path)) { return }

    $key = "created|$path"
    if ($script:openedInCursor[$key]) { return }

    try { $content = Get-Content $path -Raw -ErrorAction Stop } catch { return }
    if (Test-TaskDone $content) { return }  # already done, skip

    $script:openedInCursor[$key] = $true
    Open-InCursor $path
}

# File changed -> if Status: Done, send to Codex
$onChange = {
    $path = $Event.SourceEventArgs.FullPath
    Start-Sleep -Milliseconds 700
    if (-not (Test-Path $path)) { return }

    try { $content = Get-Content $path -Raw -ErrorAction Stop } catch { return }
    if (-not (Test-TaskDone $content)) {
        if (Test-TaskReady $content) {
            $openKey = "ready|$path"
            if (-not $script:openedInCursor[$openKey]) {
                $script:openedInCursor[$openKey] = $true
                Open-InCursor $path
            }
        }
        return
    }

    $item = Get-Item $path
    $key  = "done|$path|$($item.LastWriteTime.Ticks)"
    if ($script:processed[$key]) { return }
    if (Test-StateContains $doneStateFile "$path|$($item.LastWriteTime.Ticks)") { return }
    $script:processed[$key] = $true
    Add-StateLine $doneStateFile $key

    Write-Log "Done detected: $($Event.SourceEventArgs.Name)"
    $result = Build-CodexMessage $path
    Write-Log "Codex instruction: $($result.File)"

    $sent = Send-ToChat -ProcessName "Codex" -WindowTitlePattern "Codex" -Message $result.Message
    if (-not $sent) {
        Write-Log "Codex window not found. Instruction saved to codex_ready/."
    }
    Show-Notification "Cursor task done" "$($Event.SourceEventArgs.Name) -> Codex"
}

Register-ObjectEvent $watcher "Created" -Action $onCreate | Out-Null
Register-ObjectEvent $watcher "Changed" -Action $onChange | Out-Null

function Invoke-TaskSweep($label, $since) {
    Get-ChildItem -LiteralPath $watchDir -Filter "*.md" | Where-Object {
        $_.LastWriteTime -gt $since
    } | ForEach-Object {
    try {
        $content = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction Stop
        if (Test-TaskDone $content) {
            $doneKey = "done|$($_.FullName)|$($_.LastWriteTime.Ticks)"
            if (-not (Test-StateContains $doneStateFile "$($_.FullName)|$($_.LastWriteTime.Ticks)")) {
                Add-StateLine $doneStateFile $doneKey
                Write-Log "$label sweep picked Done task: $($_.Name)"
                $result = Build-CodexMessage $_.FullName
                Write-Log "Codex instruction: $($result.File)"
                $sent = Send-ToChat -ProcessName "Codex" -WindowTitlePattern "Codex" -Message $result.Message
                if (-not $sent) {
                    Write-Log "Codex window not found. Instruction saved to codex_ready/."
                }
                Show-Notification "Cursor task done" "$($_.Name) -> Codex"
            }
        } elseif (Test-TaskReady $content) {
            $key = "$label|$($_.FullName)"
            if (-not (Test-StateLine $openedStateFile $_.FullName) -and -not $script:openedInCursor[$key]) {
                $script:openedInCursor[$key] = $true
                Write-Log "$label sweep picked Ready task: $($_.Name)"
                Open-InCursor $_.FullName
            }
        }
    } catch {
        Write-Log "$label sweep skipped $($_.Name): $($_.Exception.Message)"
    }
    }
}

# Startup sweep: pick up recent Ready tasks created while the watcher was down.
Invoke-TaskSweep "Startup" (Get-Date).AddHours(-2)

# Initial dashboard generation
& "$PSScriptRoot\generate_dashboard.ps1" 2>$null

$script:dashTick = 0
try {
    while ($true) {
        Start-Sleep -Seconds 10
        Invoke-TaskSweep "Polling" (Get-Date).AddHours(-2)
        $script:dashTick++
        if ($script:dashTick % 3 -eq 0) {
            & "$PSScriptRoot\generate_dashboard.ps1" 2>$null
        }
    }
} finally {
    $watcher.EnableRaisingEvents = $false
    $watcher.Dispose()
}
