@echo off
setlocal

set "BASE_DIR=%~dp0"

echo =========================================
echo Restart ALL (server + tunnel + watchdog)
echo =========================================

rem Stop watchdog windows if running
taskkill /F /FI "WINDOWTITLE eq UTC_Server_Watchdog*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Cloudflare_Tunnel_Watchdog*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Cloudflare_Tunnel_Watchdog_2*" /T >nul 2>&1

rem Stop child processes as safety
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM cloudflared.exe >nul 2>&1

timeout /t 2 /nobreak >nul

rem Start watchdog stack again
start "" "%BASE_DIR%start_system_24x7.bat"

echo Restart command sent.
echo A new watchdog window should open.
pause

