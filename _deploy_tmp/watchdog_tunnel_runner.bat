@echo off
setlocal
set "BASE=%~dp0"
set "LOG_DIR=%BASE%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "CF=%BASE%cloudflared.exe"
if not exist "%CF%" set "CF=cloudflared"
cd /d "%BASE%"
:loop
tasklist /FI "IMAGENAME eq cloudflared.exe" | find /I "cloudflared.exe" >nul
if %errorlevel%==0 (
  echo [%date% %time%] cloudflared already running, skip launch>>"%LOG_DIR%\watchdog_tunnel.log"
  timeout /t 2 /nobreak >nul
  goto loop
)
echo [%date% %time%] tunnel A start>>"%LOG_DIR%\watchdog_tunnel.log"
"%CF%" --protocol http2 --edge-ip-version 4 tunnel run --token eyJhIjoiYmFkZGVkYzU1NDRlMDViNjQ5NTFmYTY1ZDc5ODQ4NDgiLCJ0IjoiM2YyYjAzNDktNzdmNy00NTc4LWE2MGMtMGJiZDJmMTg1ZjJjIiwicyI6IlkyUmtOMk5qTmpBdFpXTTVZaTAwWWpWakxUbGxNRGN0TURsaE5qUXhaV0ZqT0dFMyJ9 >>"%LOG_DIR%\cloudflared.log" 2>&1
echo [%date% %time%] tunnel A exited, restart in 1s>>"%LOG_DIR%\watchdog_tunnel.log"
timeout /t 1 /nobreak >nul
goto loop
