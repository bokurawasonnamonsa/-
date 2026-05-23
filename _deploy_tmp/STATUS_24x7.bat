@echo off
setlocal
cd /d "%~dp0"

echo === process ===
powershell -NoProfile -Command "Get-Process python,cloudflared -ErrorAction SilentlyContinue | Select-Object ProcessName,Id,StartTime | Format-Table -AutoSize"

echo.
echo === health ===
powershell -NoProfile -Command "try { 'LOCAL=' + (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/).StatusCode } catch { 'LOCAL=ERR' }"
powershell -NoProfile -Command "try { 'PUBLIC=' + (Invoke-WebRequest -UseBasicParsing https://3301-svs.jp/).StatusCode } catch { 'PUBLIC=ERR' }"

echo.
echo === auto_heal tail ===
powershell -NoProfile -Command "if (Test-Path '.\logs\auto_heal.log') { Get-Content '.\logs\auto_heal.log' -Tail 12 } else { 'logs\auto_heal.log not found' }"

endlocal
