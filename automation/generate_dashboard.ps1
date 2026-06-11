# generate_dashboard.ps1
# Builds automation/dashboard.html from the current task, release, and git state.

$ErrorActionPreference = "Continue"

$root = (Resolve-Path "$PSScriptRoot\..").Path
$outFile = Join-Path $PSScriptRoot "dashboard.html"
$taskDir = Join-Path $root "commercial\codex_ops\cursor_tasks"
$codexDir = Join-Path $root "commercial\codex_ops\codex_ready"
$buildMd = Join-Path $root "commercial\apps\command_clock\android\BUILD_STATUS.md"
$taskBoard = Join-Path $root "commercial\codex_ops\TASK_BOARD.md"
$gitExe = "C:\Program Files\Git\cmd\git.exe"

function Html($value) {
    if ($null -eq $value) { return "" }
    return [System.Net.WebUtility]::HtmlEncode([string]$value)
}

function Get-TaskStatus($content) {
    if ($content -match '(?im)^\s*\*\*Status:\*\*\s*(Done|In Progress|Ready|Todo|Blocked)') { return $Matches[1] }
    if ($content -match '(?im)^\s*Status:\s*(Done|In Progress|Ready|Todo|Blocked)') { return $Matches[1] }
    if ($content -match '(?im)\bStatus:\s*(Done|In Progress|Ready|Todo|Blocked)\b') { return $Matches[1] }
    return "Unknown"
}

function Get-TaskTitle($content, $fallback) {
    if ($content -match '(?m)^#\s+(.+)$') { return $Matches[1].Trim() }
    return $fallback
}

function Get-StatusClass($status) {
    switch ($status) {
        "Done" { return "done" }
        "In Progress" { return "active" }
        "Ready" { return "ready" }
        "Todo" { return "ready" }
        "Blocked" { return "blocked" }
        default { return "unknown" }
    }
}

function Get-Badge($status) {
    $class = Get-StatusClass $status
    return "<span class='badge $class'>$(Html $status)</span>"
}

function Get-TaskCards($dir, $limit) {
    $files = Get-ChildItem -LiteralPath $dir -Filter "*.md" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '\\_archive\\' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First $limit

    if (-not $files) {
        return "<p class='empty'>No task files found.</p>"
    }

    $items = New-Object System.Collections.Generic.List[string]
    foreach ($file in $files) {
        $content = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
        $status = Get-TaskStatus $content
        $class = Get-StatusClass $status
        $title = Get-TaskTitle $content $file.BaseName
        $date = $file.LastWriteTime.ToString("MM/dd HH:mm")
        $rel = $file.FullName.Substring($root.Length + 1)
        $items.Add("<div class='task $class'><div class='task-main'><span class='task-title'>$(Html $title)</span><span class='task-path'>$(Html $rel)</span></div>$(Get-Badge $status)<span class='task-date'>$date</span></div>")
    }
    return ($items -join "`n")
}

function Get-GitLogHtml() {
    if (-not (Test-Path $gitExe)) {
        return "<li class='empty'>Git executable not found.</li>"
    }
    try {
        $lines = & $gitExe -C $root log --oneline -8 2>$null
        if (-not $lines) { return "<li class='empty'>No git log output.</li>" }
        return (($lines | ForEach-Object { "<li>$(Html $_)</li>" }) -join "`n")
    } catch {
        return "<li class='empty'>Unable to read git log.</li>"
    }
}

function Get-LatestBuildInfo() {
    $info = [ordered]@{
        Version = "Unknown"
        Published = "Unknown"
        Track = "Internal testing"
        Status = "Unknown"
    }
    if (-not (Test-Path $buildMd)) { return $info }

    $content = Get-Content -LiteralPath $buildMd -Raw -ErrorAction SilentlyContinue
    if ($content -match '(?m)^##\s+Version\s+([0-9.]+)\s+(.+)$') {
        $info.Version = $Matches[1]
        $info.Status = $Matches[2].Trim()
    }
    if ($content -match '(?m)^-\s+Published:\s+(.+)$') {
        $info.Published = $Matches[1].Trim()
    }
    if ($content -match '(?m)^-\s+Internal test release:\s+`([^`]+)`') {
        $info.Track = $Matches[1].Trim()
    }
    return $info
}

function Get-TaskBoardSummary() {
    if (-not (Test-Path $taskBoard)) { return "<p class='empty'>TASK_BOARD.md not found.</p>" }
    $lines = Get-Content -LiteralPath $taskBoard -ErrorAction SilentlyContinue
    $selected = $lines | Where-Object {
        $_ -match '^- ' -and (
            $_ -match 'Command Clock' -or
            $_ -match 'workflow' -or
            $_ -match 'dashboard' -or
            $_ -match 'Store|Testing|Marketing'
        )
    } | Select-Object -First 10
    if (-not $selected) { return "<p class='empty'>No summary lines found.</p>" }
    return (($selected | ForEach-Object { "<li>$(Html ($_ -replace '^- ',''))</li>" }) -join "`n")
}

$build = Get-LatestBuildInfo
$cursorCards = Get-TaskCards $taskDir 10
$codexCards = Get-TaskCards $codexDir 10
$gitLog = Get-GitLogHtml
$boardSummary = Get-TaskBoardSummary
$now = Get-Date -Format "yyyy/MM/dd HH:mm:ss"

$html = @"
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="15">
  <title>TactNode Labs Agent Dashboard</title>
  <style>
    :root {
      --bg: #0d1117;
      --panel: #161b22;
      --panel2: #0f1620;
      --line: #30363d;
      --text: #e6edf3;
      --muted: #8b949e;
      --blue: #58a6ff;
      --green: #22c55e;
      --orange: #f97316;
      --purple: #a855f7;
      --red: #f85149;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--text); font-family: "Segoe UI", "Yu Gothic", "Meiryo", sans-serif; font-size: 13px; letter-spacing: 0; }
    header { padding: 14px 16px; border-bottom: 1px solid var(--line); background: #0b1118; display: flex; justify-content: space-between; gap: 12px; align-items: center; }
    h1 { margin: 0; font-size: 18px; color: var(--blue); }
    h2 { margin: 0 0 10px; font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); }
    main { padding: 14px; display: grid; gap: 12px; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-width: 0; }
    .panel.cursor { border-color: rgba(249,115,22,.65); }
    .panel.codex { border-color: rgba(34,197,94,.65); }
    .panel.release { border-color: rgba(88,166,255,.65); }
    .panel.git { border-color: rgba(168,85,247,.65); }
    .kpi { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
    .kpi-card { background: var(--panel2); border: 1px solid var(--line); border-radius: 7px; padding: 10px; }
    .kpi-label { color: var(--muted); font-size: 11px; margin-bottom: 4px; }
    .kpi-value { font-size: 18px; font-weight: 800; color: var(--green); overflow-wrap: anywhere; }
    .task { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 8px; align-items: center; background: var(--panel2); border-left: 3px solid var(--line); border-radius: 6px; padding: 7px 8px; margin-bottom: 6px; }
    .task.ready { border-left-color: var(--orange); }
    .task.active { border-left-color: var(--blue); }
    .task.done { border-left-color: var(--green); }
    .task.blocked { border-left-color: var(--red); }
    .task-title { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 700; }
    .task-path { display: block; color: var(--muted); font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }
    .task-date { color: var(--muted); font-size: 10px; white-space: nowrap; }
    .badge { border-radius: 999px; padding: 2px 7px; font-size: 10px; font-weight: 800; white-space: nowrap; border: 1px solid var(--line); color: var(--muted); }
    .badge.ready { color: var(--orange); border-color: rgba(249,115,22,.45); background: rgba(249,115,22,.1); }
    .badge.active { color: var(--blue); border-color: rgba(88,166,255,.45); background: rgba(88,166,255,.1); }
    .badge.done { color: var(--green); border-color: rgba(34,197,94,.45); background: rgba(34,197,94,.1); }
    .badge.blocked { color: var(--red); border-color: rgba(248,81,73,.45); background: rgba(248,81,73,.1); }
    .git-list, .summary-list { list-style: none; margin: 0; padding: 0; }
    .git-list li, .summary-list li { border-bottom: 1px solid #21262d; padding: 6px 0; color: #cad1d9; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .git-list li { font-family: Consolas, monospace; font-size: 11px; }
    .flow { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 10px; }
    .flow span { background: var(--panel2); border: 1px solid var(--line); border-radius: 7px; padding: 7px 10px; font-size: 11px; font-weight: 700; }
    .arrow { color: var(--muted); }
    .empty { color: var(--muted); font-style: italic; }
    .stamp { color: var(--muted); font-size: 11px; white-space: nowrap; }
    @media (max-width: 900px) { .grid, .kpi { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>TactNode Labs Agent Dashboard</h1>
    <div class="stamp">Last generated: $(Html $now) / auto refresh: 15s</div>
  </header>
  <main>
    <section class="panel release">
      <h2>Latest Release</h2>
      <div class="kpi">
        <div class="kpi-card"><div class="kpi-label">Version</div><div class="kpi-value">$(Html $build.Version)</div></div>
        <div class="kpi-card"><div class="kpi-label">Track</div><div class="kpi-value">$(Html $build.Track)</div></div>
        <div class="kpi-card"><div class="kpi-label">Published</div><div class="kpi-value">$(Html $build.Published)</div></div>
      </div>
      <div class="flow">
        <span>Claude: plan</span><b class="arrow">→</b><span>Cursor: implement</span><b class="arrow">→</b><span>Codex: verify/build/upload</span><b class="arrow">→</b><span>Play Console: internal test</span>
      </div>
    </section>
    <section class="grid">
      <div class="panel cursor"><h2>Cursor Tasks</h2>$cursorCards</div>
      <div class="panel codex"><h2>Codex Ready Queue</h2>$codexCards</div>
    </section>
    <section class="grid">
      <div class="panel git"><h2>Recent Commits</h2><ul class="git-list">$gitLog</ul></div>
      <div class="panel"><h2>Task Board Summary</h2><ul class="summary-list">$boardSummary</ul></div>
    </section>
  </main>
</body>
</html>
"@

$html | Set-Content -LiteralPath $outFile -Encoding UTF8
Write-Host "[dashboard] Generated: $outFile"
