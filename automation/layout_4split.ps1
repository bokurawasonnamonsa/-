# layout_4split.ps1
# Arrange Claude Code, Cursor, Codex, and Android Studio in a fixed 4-quadrant layout.
#
# Top-left:     Claude Code
# Top-right:    Cursor
# Bottom-left:  Codex
# Bottom-right: Android Studio

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinLayout {
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
}
"@

$SW_RESTORE = 9
$SWP_FLAGS = 0x0040 # SWP_SHOWWINDOW

function Set-WindowLayout($proc, $x, $y, $w, $h) {
    if (-not $proc -or $proc.MainWindowHandle -eq 0) { return }
    $hwnd = $proc.MainWindowHandle
    if ([WinLayout]::IsIconic($hwnd)) {
        [WinLayout]::ShowWindow($hwnd, $SW_RESTORE) | Out-Null
    }
    Start-Sleep -Milliseconds 150
    [WinLayout]::SetWindowPos($hwnd, [IntPtr]::Zero, $x, $y, $w, $h, $SWP_FLAGS) | Out-Null
    Write-Host "Positioned: $($proc.Name) -> ($x,$y) ${w}x${h}"
}

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$halfW = [int]($screen.Width / 2)
$halfH = [int]($screen.Height / 2)
$left = $screen.Left
$top = $screen.Top

$claude = Get-Process | Where-Object {
    $_.Name -ieq "claude" -and $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -match "Claude"
} | Select-Object -First 1

$cursor = Get-Process | Where-Object {
    $_.Name -ieq "Cursor" -and $_.MainWindowHandle -ne 0
} | Sort-Object MainWindowTitle -Descending | Select-Object -First 1

$codex = Get-Process | Where-Object {
    $_.Name -ieq "Codex" -and $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -match "Codex"
} | Select-Object -First 1

$studio = Get-Process | Where-Object {
    $_.Name -match "studio64|AndroidStudio|idea64" -and $_.MainWindowHandle -ne 0
} | Select-Object -First 1

Set-WindowLayout $claude $left $top $halfW $halfH
Set-WindowLayout $cursor ($left + $halfW) $top $halfW $halfH
Set-WindowLayout $codex $left ($top + $halfH) $halfW $halfH

if ($studio) {
    Set-WindowLayout $studio ($left + $halfW) ($top + $halfH) $halfW $halfH
} else {
    Write-Host "Android Studio is not running. Start it and run LAYOUT_4SPLIT.bat again."
}

Write-Host "4-split layout applied."
