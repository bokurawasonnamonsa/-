# send_to_app.ps1
# UI Automation helper: focus a window and send text to its chat input.

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32UI {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, uint dwData, UIntPtr dwExtraInfo);
}
public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
"@

function Send-ToChat {
    param(
        [string]$ProcessName,
        [string]$WindowTitlePattern,
        [string]$Message
    )

    # Prefer an exact process-name match so a browser tab titled "Codex" is not selected
    # before the native Codex app.
    $proc = Get-Process | Where-Object {
        $_.Name -ieq $ProcessName -and $_.MainWindowHandle -ne 0
    } | Sort-Object MainWindowTitle -Descending | Select-Object -First 1

    if (-not $proc) {
        $proc = Get-Process | Where-Object {
            $_.MainWindowTitle -match $WindowTitlePattern -and $_.MainWindowHandle -ne 0
        } | Select-Object -First 1
    }

    if (-not $proc) {
        Write-Host "[send_to_app] Window not found: $ProcessName / $WindowTitlePattern"
        return $false
    }

    Write-Host "[send_to_app] Found window: $($proc.MainWindowTitle)"

    # Bring window to foreground
    [Win32UI]::ShowWindow($proc.MainWindowHandle, 9) | Out-Null  # SW_RESTORE
    Start-Sleep -Milliseconds 300
    [Win32UI]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 500

    # Click the chat input area. In the 4-split layout, focus often stays on the
    # previous pane unless we explicitly click before pasting.
    $rect = New-Object RECT
    [Win32UI]::GetWindowRect($proc.MainWindowHandle, [ref]$rect) | Out-Null
    $clickX = [int](($rect.Left + $rect.Right) / 2)
    $clickY = [int]($rect.Bottom - 55)
    [Win32UI]::SetCursorPos($clickX, $clickY) | Out-Null
    Start-Sleep -Milliseconds 150
    [Win32UI]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    [Win32UI]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 250

    # Replace any stale text already sitting in the input.
    [System.Windows.Forms.SendKeys]::SendWait("^a")
    Start-Sleep -Milliseconds 150

    # Set clipboard and paste.
    [System.Windows.Forms.Clipboard]::SetText($Message)
    Start-Sleep -Milliseconds 200
    [System.Windows.Forms.SendKeys]::SendWait("^v")
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.SendKeys]::SendWait("^{ENTER}")

    Write-Host "[send_to_app] Message sent to $($proc.Name) via click $clickX,$clickY"
    return $true
}
