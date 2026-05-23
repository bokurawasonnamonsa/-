@echo off
setlocal
cd /d "%~dp0"

echo [1/3] stop old auto-heal window
taskkill /FI "WINDOWTITLE eq UTC_AUTO_HEAL*" /F >nul 2>&1

echo [2/3] start AUTO_HEAL_3301
start "UTC_AUTO_HEAL" /min "%~dp0AUTO_HEAL_3301.bat"

echo [3/3] quick health check (wait 6s)
timeout /t 6 /nobreak >nul
powershell -NoProfile -Command "try { 'LOCAL=' + (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/).StatusCode } catch { 'LOCAL=ERR' }"
powershell -NoProfile -Command "try { 'PUBLIC=' + (Invoke-WebRequest -UseBasicParsing https://3301-svs.jp/).StatusCode } catch { 'PUBLIC=ERR' }"

echo.
echo started. close this window.
endlocal
