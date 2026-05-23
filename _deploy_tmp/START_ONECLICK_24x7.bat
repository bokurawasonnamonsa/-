@echo off
setlocal
cd /d "%~dp0"

echo =========================================
echo UTC 24x7 one-click start
echo =========================================

echo [1/5] stop old processes
taskkill /FI "WINDOWTITLE eq UTC_AUTO_HEAL*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq watchdog_server*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq watchdog_tunnel_A*" /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1

echo [2/5] start watchdog server
start "watchdog_server" /min cmd /c "cd /d %~dp0 && call watchdog_server_runner.bat"

echo [3/5] start watchdog tunnel
start "watchdog_tunnel_A" /min cmd /c "cd /d %~dp0 && call watchdog_tunnel_runner.bat"

echo [4/5] wait startup
timeout /t 10 /nobreak >nul

echo [5/5] health check
powershell -NoProfile -Command "try { 'LOCAL=' + (Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/).StatusCode } catch { 'LOCAL=ERR' }"
powershell -NoProfile -Command "try { 'PUBLIC=' + (Invoke-WebRequest -UseBasicParsing https://3301-svs.jp/).StatusCode } catch { 'PUBLIC=ERR' }"

echo.
echo done. Use START_ONECLICK_24x7.bat only.
endlocal
