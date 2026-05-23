@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "BASE=%~dp0"
set "LOG_DIR=%BASE%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\force_3301_up.log"

set "LOCAL_URL=http://127.0.0.1:8000/healthz"
set "PUBLIC_URL=https://3301-svs.jp/healthz"
set "CHECK_SEC=5"
set "MAX_FAIL_PUBLIC=3"
set "MAX_FAIL_LOCAL=3"
set /a FAIL_PUBLIC=0
set /a FAIL_LOCAL=0
set /a PUBLIC_COOLDOWN=0

set "CF=%BASE%cloudflared.exe"
if not exist "%CF%" set "CF=cloudflared"
set "TOKEN=eyJhIjoiYmFkZGVkYzU1NDRlMDViNjQ5NTFmYTY1ZDc5ODQ4NDgiLCJ0IjoiM2YyYjAzNDktNzdmNy00NTc4LWE2MGMtMGJiZDJmMTg1ZjJjIiwicyI6IlkyUmtOMk5qTmpBdFpXTTVZaTAwWWpWakxUbGxNRGN0TURsaE5qUXhaV0ZqT0dFMyJ9"

title FORCE_3301_UP
echo [%date% %time%] start>>"%LOG_FILE%"

call :stop_all
call :start_server
call :start_tunnel

:loop
set "L=000"
set "P=000"
for /f %%A in ('curl.exe --connect-timeout 3 --max-time 5 -s -o NUL -w "%%{http_code}" "%LOCAL_URL%"') do set "L=%%A"
for /f %%A in ('curl.exe --connect-timeout 3 --max-time 7 -s -o NUL -w "%%{http_code}" "%PUBLIC_URL%"') do set "P=%%A"
if "!L!"=="" set "L=000"
if "!P!"=="" set "P=000"
if "!FAIL_PUBLIC!"=="" set "FAIL_PUBLIC=0"
if "!FAIL_LOCAL!"=="" set "FAIL_LOCAL=0"
echo LOCAL=!L! PUBLIC=!P!
echo [%date% %time%] health LOCAL=!L! PUBLIC=!P! fail_local=!FAIL_LOCAL! fail_public=!FAIL_PUBLIC! cooldown=!PUBLIC_COOLDOWN!>>"%LOG_FILE%"

if "!L!"=="200" (
  set /a FAIL_LOCAL=0
) else (
  set /a FAIL_LOCAL+=1
)
if "!P!"=="200" (
  set /a FAIL_PUBLIC=0
) else (
  set /a FAIL_PUBLIC+=1
)

if !FAIL_LOCAL! GEQ %MAX_FAIL_LOCAL% (
  echo [%date% %time%] restart server+tunnel>>"%LOG_FILE%"
  call :restart_server_and_tunnel
  set /a FAIL_LOCAL=0
  set /a FAIL_PUBLIC=0
  set /a PUBLIC_COOLDOWN=3
  goto :wait
)

if !PUBLIC_COOLDOWN! GTR 0 (
  set /a PUBLIC_COOLDOWN-=1
) else (
  if !FAIL_PUBLIC! GEQ %MAX_FAIL_PUBLIC% (
    echo [%date% %time%] restart tunnel by public fail threshold>>"%LOG_FILE%"
    call :restart_tunnel
    set /a FAIL_PUBLIC=0
    set /a PUBLIC_COOLDOWN=4
  )
)

:wait
ping -n %CHECK_SEC% 127.0.0.1 >nul
goto :loop

:start_server
start "watchdog_server" /min cmd /c "cd /d %BASE% && call watchdog_server_runner.bat"
ping -n 4 127.0.0.1 >nul
goto :eof

:start_tunnel
start "watchdog_tunnel_A" /min cmd /c "cd /d %BASE% && call watchdog_tunnel_runner.bat"
ping -n 6 127.0.0.1 >nul
goto :eof

:restart_tunnel
taskkill /FI "WINDOWTITLE eq watchdog_tunnel_A*" /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1
ping -n 3 127.0.0.1 >nul
call :start_tunnel
goto :eof

:restart_server_and_tunnel
taskkill /FI "WINDOWTITLE eq watchdog_server*" /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1
call :restart_tunnel
call :start_server
goto :eof

:stop_all
taskkill /FI "WINDOWTITLE eq UTC_ALLINONE_SUPERVISOR*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq UTC_AUTO_HEAL*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq FORCE_TUNNEL*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq watchdog_server*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq watchdog_tunnel_A*" /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1
ping -n 3 127.0.0.1 >nul
goto :eof
