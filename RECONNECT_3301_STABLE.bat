@echo off
setlocal
set "APP=%~dp0"
cd /d "%APP%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%APP%scripts\warn_local_tunnel.ps1" -Strict
if errorlevel 3 (
  echo.
  echo 本番は VPS です。ローカル起動は使わず DEPLOY_PRODUCTION.bat を実行してください。
  echo どうしてもローカル検証する場合: set UTC_ALLOW_LOCAL_TUNNEL=1
  pause
  exit /b 3
)

echo [1] Stop old processes
taskkill /IM cloudflared.exe /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1

echo [2] Start watchdog server
start "watchdog_server" cmd /k "cd /d %APP% && watchdog_server_runner.bat"

echo [3] Start watchdog tunnel A
start "watchdog_tunnel_A" cmd /k "cd /d %APP% && watchdog_tunnel_runner.bat"

echo [4] Wait startup
timeout /t 6 >nul

echo [5] Health check (retry up to 30s)
set "LOCAL=000"
set "PUBLIC=000"
for /l %%I in (1,1,15) do (
  for /f %%A in ('curl.exe -s -o NUL -w "%%{http_code}" http://127.0.0.1:8000/') do set LOCAL=%%A
  for /f %%A in ('curl.exe -s -o NUL -w "%%{http_code}" https://3301-svs.jp/') do set PUBLIC=%%A
  if "%LOCAL%"=="200" if "%PUBLIC%"=="200" goto :HEALTH_OK
  timeout /t 2 >nul
)
:HEALTH_OK
echo LOCAL=%LOCAL%
echo PUBLIC=%PUBLIC%

echo [6] Process check
powershell -NoProfile -Command "Get-Process python,cloudflared -ErrorAction SilentlyContinue | Select-Object Name,Id"

echo.
echo Done.
pause
endlocal
