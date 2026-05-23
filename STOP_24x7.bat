@echo off
setlocal
cd /d "%~dp0"

echo stop AUTO_HEAL window
taskkill /FI "WINDOWTITLE eq UTC_AUTO_HEAL*" /F >nul 2>&1

echo stop python/cloudflared
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1

echo done.
endlocal
