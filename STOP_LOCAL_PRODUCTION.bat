@echo off

chcp 65001 >nul

cd /d "%~dp0."

title UTC - Stop local production processes



echo Stopping local python / cloudflared (VPS is production)...

taskkill /FI "WINDOWTITLE eq watchdog_server*" /F >nul 2>&1

taskkill /FI "WINDOWTITLE eq watchdog_tunnel_A*" /F >nul 2>&1

taskkill /FI "WINDOWTITLE eq UTC_ALLINONE_SUPERVISOR*" /F >nul 2>&1

taskkill /FI "WINDOWTITLE eq UTC_APP_SERVER*" /F >nul 2>&1

taskkill /FI "WINDOWTITLE eq UTC_CLOUDFLARED*" /F >nul 2>&1

taskkill /IM cloudflared.exe /F >nul 2>&1

taskkill /IM python.exe /F >nul 2>&1

echo Done. Production URL: https://3301-svs.jp/ (VPS)

timeout /t 2 >nul

