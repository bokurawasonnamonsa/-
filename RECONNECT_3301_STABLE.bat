@echo off
setlocal
set "APP=C:\Users\Administrator\Desktop\utc_web"

if not exist "%APP%" (
  echo ERROR: folder not found: %APP%
  pause
  exit /b 1
)

cd /d "%APP%"

echo [1] Stop old processes
taskkill /IM cloudflared.exe /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1

echo [2] Start watchdog server
start "watchdog_server" cmd /k "cd /d %APP% && watchdog_server_runner.bat"

echo [3] Start watchdog tunnel A
start "watchdog_tunnel_A" cmd /k "cd /d %APP% && watchdog_tunnel_runner.bat"

echo [4] Start watchdog tunnel B
start "watchdog_tunnel_B" cmd /k "cd /d %APP% && watchdog_tunnel_runner_2.bat"

echo [5] Wait startup
timeout /t 6 >nul

echo [6] Health check
for /f %%A in ('curl.exe -s -o NUL -w "%%{http_code}" http://127.0.0.1:8000/') do set LOCAL=%%A
for /f %%A in ('curl.exe -s -o NUL -w "%%{http_code}" https://3301-svs.jp/') do set PUBLIC=%%A
echo LOCAL=%LOCAL%
echo PUBLIC=%PUBLIC%

echo [7] Process check
powershell -NoProfile -Command "Get-Process python,cloudflared -ErrorAction SilentlyContinue | Select-Object Name,Id"

echo.
echo Done.
pause
endlocal
