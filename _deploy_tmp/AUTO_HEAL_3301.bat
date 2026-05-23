@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "BASE=%~dp0"
set "LOG_DIR=%BASE%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\auto_heal.log"

set "PUBLIC_URL=https://3301-svs.jp/"
set "LOCAL_URL=http://127.0.0.1:8000/"
set "CHECK_INTERVAL_SEC=20"
set "MAX_FAIL_LOCAL=2"
set "MAX_FAIL_PUBLIC=3"
set "PUBLIC_RESTART_COOLDOWN_TICKS=9"
set /a FAIL_LOCAL=0
set /a FAIL_PUBLIC=0
set /a PUBLIC_COOLDOWN=0

echo [%date% %time%] AUTO_HEAL start>>"%LOG_FILE%"
echo =========================================
echo UTC AUTO HEAL (24x7) started
echo LOG: %LOG_FILE%
echo =========================================

call :restart_stack

:health_loop
set "LOCAL=000"
set "PUBLIC=000"
for /f %%A in ('curl.exe --connect-timeout 3 --max-time 5 -s -o NUL -w "%%{http_code}" "%LOCAL_URL%"') do set LOCAL=%%A
for /f %%A in ('curl.exe --connect-timeout 3 --max-time 5 -s -o NUL -w "%%{http_code}" "%PUBLIC_URL%"') do set PUBLIC=%%A

if "%LOCAL%"=="200" if "%PUBLIC%"=="200" (
  set /a FAIL_LOCAL=0
  set /a FAIL_PUBLIC=0
  echo [%date% %time%] OK LOCAL=%LOCAL% PUBLIC=%PUBLIC%>>"%LOG_FILE%"
) else (
  if "%LOCAL%"=="200" (
    set /a FAIL_LOCAL=0
  ) else (
    set /a FAIL_LOCAL+=1
  )
  if "%PUBLIC%"=="200" (
    set /a FAIL_PUBLIC=0
  ) else (
    set /a FAIL_PUBLIC+=1
  )
  echo [%date% %time%] NG LOCAL=%LOCAL% PUBLIC=%PUBLIC% fail_local=!FAIL_LOCAL! fail_public=!FAIL_PUBLIC!>>"%LOG_FILE%"

  rem 優先: ローカル異常はフル再起動
  if !FAIL_LOCAL! GEQ %MAX_FAIL_LOCAL% (
    echo [%date% %time%] restart trigger (full stack)>>"%LOG_FILE%"
    call :restart_stack
    set /a FAIL_LOCAL=0
    set /a FAIL_PUBLIC=0
    goto :after_restart
  )

  rem ローカル正常かつ公開だけ異常: トンネルのみ再起動（ループ回数クールダウン）
  if "%LOCAL%"=="200" if !FAIL_PUBLIC! GEQ %MAX_FAIL_PUBLIC% (
    if !PUBLIC_COOLDOWN! LEQ 0 (
      echo [%date% %time%] restart trigger (tunnel only)>>"%LOG_FILE%"
      call :restart_tunnel_only
      set /a FAIL_PUBLIC=0
      set /a PUBLIC_COOLDOWN=%PUBLIC_RESTART_COOLDOWN_TICKS%
    ) else (
      echo [%date% %time%] tunnel restart skipped by cooldown ticks=!PUBLIC_COOLDOWN!>>"%LOG_FILE%"
    )
  )
)

:after_restart
if !PUBLIC_COOLDOWN! GTR 0 set /a PUBLIC_COOLDOWN-=1
ping -n %CHECK_INTERVAL_SEC% 127.0.0.1 >nul
goto health_loop

:restart_stack
echo [%date% %time%] stack restart begin>>"%LOG_FILE%"
taskkill /FI "WINDOWTITLE eq watchdog_server*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq watchdog_tunnel_A*" /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1
taskkill /IM python.exe /F >nul 2>&1
ping -n 2 127.0.0.1 >nul

start "watchdog_server" /min cmd /c "cd /d %BASE% && watchdog_server_runner.bat"
start "watchdog_tunnel_A" /min cmd /c "cd /d %BASE% && watchdog_tunnel_runner.bat"

for /l %%I in (1,1,15) do (
  set "L=000"
  set "P=000"
  for /f %%A in ('curl.exe --connect-timeout 3 --max-time 5 -s -o NUL -w "%%{http_code}" "%LOCAL_URL%"') do set L=%%A
  for /f %%A in ('curl.exe --connect-timeout 3 --max-time 5 -s -o NUL -w "%%{http_code}" "%PUBLIC_URL%"') do set P=%%A
  if "!L!"=="200" if "!P!"=="200" (
    echo [%date% %time%] stack restart success LOCAL=!L! PUBLIC=!P!>>"%LOG_FILE%"
    goto :eof
  )
  ping -n 3 127.0.0.1 >nul
)
echo [%date% %time%] stack restart timeout>>"%LOG_FILE%"
goto :eof

:restart_tunnel_only
echo [%date% %time%] tunnel restart begin>>"%LOG_FILE%"
taskkill /FI "WINDOWTITLE eq watchdog_tunnel_A*" /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1
ping -n 2 127.0.0.1 >nul
start "watchdog_tunnel_A" /min cmd /c "cd /d %BASE% && watchdog_tunnel_runner.bat"
for /l %%I in (1,1,15) do (
  set "P=000"
  for /f %%A in ('curl.exe --connect-timeout 3 --max-time 5 -s -o NUL -w "%%{http_code}" "%PUBLIC_URL%"') do set P=%%A
  if "!P!"=="200" (
    echo [%date% %time%] tunnel restart success PUBLIC=!P!>>"%LOG_FILE%"
    goto :eof
  )
  ping -n 3 127.0.0.1 >nul
)
echo [%date% %time%] tunnel restart timeout>>"%LOG_FILE%"
goto :eof
