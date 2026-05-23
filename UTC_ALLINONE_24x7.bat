@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\warn_local_tunnel.ps1" -Strict
if errorlevel 3 (
  echo.
  echo 本番は VPS です。DEPLOY_PRODUCTION.bat / VERIFY_PRODUCTION.bat を使用してください。
  echo ローカル常駐が必要な場合のみ: set UTC_ALLOW_LOCAL_TUNNEL=1
  pause
  exit /b 3
)

rem =========================================================
rem UTC all-in-one launcher + monitor (single file)
rem This file does: stop old -> start app+tunnel -> monitor -> auto-heal -> logging
rem =========================================================

set "BASE=%~dp0"
set "LOG_DIR=%BASE%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\utc_allinone.log"

set "PUBLIC_URL=https://3301-svs.jp/"
set "LOCAL_URL=http://127.0.0.1:8000/"
set "CHECK_INTERVAL_SEC=20"
set "MAX_FAIL_LOCAL=2"
set "MAX_FAIL_PUBLIC=3"

set "PYTHON_EXE=python"
set "CF_EXE=%BASE%cloudflared.exe"
if not exist "%CF_EXE%" set "CF_EXE=cloudflared"
set "CF_TOKEN=eyJhIjoiYmFkZGVkYzU1NDRlMDViNjQ5NTFmYTY1ZDc5ODQ4NDgiLCJ0IjoiM2YyYjAzNDktNzdmNy00NTc4LWE2MGMtMGJiZDJmMTg1ZjJjIiwicyI6IlkyUmtOMk5qTmpBdFpXTTVZaTAwWWpWakxUbGxNRGN0TURsaE5qUXhaV0ZqT0dFMyJ9"

set /a FAIL_LOCAL=0
set /a FAIL_PUBLIC=0

call :log "=== UTC_ALLINONE start ==="

rem Single-instance guard for this supervisor
tasklist /v | findstr /I "UTC_ALLINONE_SUPERVISOR" >nul 2>&1
if %errorlevel%==0 (
  echo Supervisor already running. Exiting.
  call :log "already running, exit"
  goto :eof
)

title UTC_ALLINONE_SUPERVISOR

call :stop_all
call :start_stack
call :quick_health

:main_loop
call :probe_status

if "!FAIL_LOCAL!"=="" set "FAIL_LOCAL=0"
if "!FAIL_PUBLIC!"=="" set "FAIL_PUBLIC=0"
if "!LOCAL!"=="200" (
  set /a FAIL_LOCAL=0
) else (
  ping -n 4 127.0.0.1 >nul
  call :probe_status
  if "!LOCAL!"=="200" (set /a FAIL_LOCAL=0) else (set /a FAIL_LOCAL=!FAIL_LOCAL!+1)
)
if "!PUBLIC!"=="200" (set /a FAIL_PUBLIC=0) else (set /a FAIL_PUBLIC=!FAIL_PUBLIC!+1)

call :log "health LOCAL=!LOCAL! PUBLIC=!PUBLIC! fail_local=!FAIL_LOCAL! fail_public=!FAIL_PUBLIC!"

if !FAIL_LOCAL! GEQ %MAX_FAIL_LOCAL% (
  call :log "trigger restart: local unhealthy"
  call :stop_all
  call :start_stack
  set /a FAIL_LOCAL=0
  set /a FAIL_PUBLIC=0
  goto :sleep
)

if "!LOCAL!"=="200" if !FAIL_PUBLIC! GEQ %MAX_FAIL_PUBLIC% (
  call :log "trigger restart: tunnel unhealthy"
  call :restart_tunnel_only
  set /a FAIL_PUBLIC=0
)

:sleep
ping -n %CHECK_INTERVAL_SEC% 127.0.0.1 >nul
goto :main_loop

:quick_health
call :probe_status
echo LOCAL=!LOCAL! PUBLIC=!PUBLIC!
call :log "quick_health LOCAL=!LOCAL! PUBLIC=!PUBLIC!"
goto :eof

:start_stack
call :log "start_stack begin"
start "watchdog_server" /min cmd /c "cd /d %BASE% && call watchdog_server_runner.bat"
ping -n 4 127.0.0.1 >nul
call :wait_local_ready
start "watchdog_tunnel_A" /min cmd /c "cd /d %BASE% && call watchdog_tunnel_runner.bat"
ping -n 8 127.0.0.1 >nul
call :quick_health
call :log "start_stack end"
goto :eof

:restart_tunnel_only
call :log "restart_tunnel_only begin"
taskkill /FI "WINDOWTITLE eq watchdog_tunnel_A*" /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1
ping -n 3 127.0.0.1 >nul
start "watchdog_tunnel_A" /min cmd /c "cd /d %BASE% && call watchdog_tunnel_runner.bat"
ping -n 8 127.0.0.1 >nul
call :quick_health
call :log "restart_tunnel_only end"
goto :eof

:stop_all
call :log "stop_all begin"
taskkill /FI "WINDOWTITLE eq UTC_APP_SERVER*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq UTC_CLOUDFLARED*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq UTC_AUTO_HEAL*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq watchdog_server*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq watchdog_tunnel_A*" /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1
ping -n 3 127.0.0.1 >nul
call :log "stop_all end"
goto :eof

:probe_status
set "LOCAL=000"
set "PUBLIC=000"
for /f %%A in ('curl.exe --connect-timeout 3 --max-time 8 -s -o NUL -w "%%{http_code}" "%LOCAL_URL%"') do set "LOCAL=%%A"
for /f %%A in ('curl.exe --connect-timeout 3 --max-time 8 -s -o NUL -w "%%{http_code}" "%PUBLIC_URL%"') do set "PUBLIC=%%A"
if "!LOCAL!"=="" set "LOCAL=000"
if "!PUBLIC!"=="" set "PUBLIC=000"
goto :eof

:wait_local_ready
for /l %%I in (1,1,15) do (
  for /f %%A in ('curl.exe --connect-timeout 3 --max-time 8 -s -o NUL -w "%%{http_code}" "%LOCAL_URL%"') do set "LOCAL=%%A"
  if "!LOCAL!"=="200" (
    call :log "local ready on attempt %%I"
    goto :eof
  )
  ping -n 3 127.0.0.1 >nul
)
call :log "local not ready after grace period"
goto :eof

:log
echo [%date% %time%] %~1>>"%LOG_FILE%"
goto :eof
