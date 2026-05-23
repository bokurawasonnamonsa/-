@echo off
setlocal

set "BASE_DIR=%~dp0"
set "LOG_DIR=%BASE_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "PY_CMD=python"
set "CF_CMD=cloudflared"
if exist "%BASE_DIR%cloudflared.exe" set "CF_CMD=%BASE_DIR%cloudflared.exe"

where python >nul 2>&1
if errorlevel 1 (
  where py >nul 2>&1
  if not errorlevel 1 set "PY_CMD=py -3"
)

echo =========================================
echo UTC 24x7 watchdog start
echo =========================================
echo Logs: %LOG_DIR%

(
  echo @echo off
  echo setlocal
  echo cd /d "%BASE_DIR%"
  echo :loop
  echo echo [%%date%% %%time%%] server start^>^>"%LOG_DIR%\watchdog_server.log"
  echo %PY_CMD% main.py ^>^>"%LOG_DIR%\server.log" 2^>^&1
  echo echo [%%date%% %%time%%] server exited, restart in 1s^>^>"%LOG_DIR%\watchdog_server.log"
  echo timeout /t 1 /nobreak ^>nul
  echo goto loop
) > "%BASE_DIR%watchdog_server_runner.bat"

(
  echo @echo off
  echo setlocal
  echo cd /d "%BASE_DIR%"
  echo :loop
  echo echo [%%date%% %%time%%] tunnel A start^>^>"%LOG_DIR%\watchdog_tunnel.log"
  echo "%CF_CMD%" --protocol http2 tunnel run --token eyJhIjoiYmFkZGVkYzU1NDRlMDViNjQ5NTFmYTY1ZDc5ODQ4NDgiLCJ0IjoiM2YyYjAzNDktNzdmNy00NTc4LWE2MGMtMGJiZDJmMTg1ZjJjIiwicyI6IlkyUmtOMk5qTmpBdFpXTTVZaTAwWWpWakxUbGxNRGN0TURsaE5qUXhaV0ZqT0dFMyJ9 ^>^>"%LOG_DIR%\cloudflared.log" 2^>^&1
  echo echo [%%date%% %%time%%] tunnel A exited, restart in 1s^>^>"%LOG_DIR%\watchdog_tunnel.log"
  echo timeout /t 1 /nobreak ^>nul
  echo goto loop
) > "%BASE_DIR%watchdog_tunnel_runner.bat"

(
  echo @echo off
  echo setlocal
  echo cd /d "%BASE_DIR%"
  echo :loop
  echo echo [%%date%% %%time%%] tunnel B start^>^>"%LOG_DIR%\watchdog_tunnel.log"
  echo "%CF_CMD%" --protocol http2 tunnel run --token eyJhIjoiYmFkZGVkYzU1NDRlMDViNjQ5NTFmYTY1ZDc5ODQ4NDgiLCJ0IjoiM2YyYjAzNDktNzdmNy00NTc4LWE2MGMtMGJiZDJmMTg1ZjJjIiwicyI6IlkyUmtOMk5qTmpBdFpXTTVZaTAwWWpWakxUbGxNRGN0TURsaE5qUXhaV0ZqT0dFMyJ9 ^>^>"%LOG_DIR%\cloudflared_2.log" 2^>^&1
  echo echo [%%date%% %%time%%] tunnel B exited, restart in 1s^>^>"%LOG_DIR%\watchdog_tunnel.log"
  echo timeout /t 1 /nobreak ^>nul
  echo goto loop
) > "%BASE_DIR%watchdog_tunnel_runner_2.bat"

start "UTC_Server_Watchdog" cmd /k "%BASE_DIR%watchdog_server_runner.bat"
start "Cloudflare_Tunnel_Watchdog" cmd /k "%BASE_DIR%watchdog_tunnel_runner.bat"
start "Cloudflare_Tunnel_Watchdog_2" cmd /k "%BASE_DIR%watchdog_tunnel_runner_2.bat"

echo.
echo Started.
echo Check logs: server.log / cloudflared.log / cloudflared_2.log / watchdog_*.log
pause

