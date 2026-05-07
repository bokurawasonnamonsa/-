@echo off
setlocal

echo =========================================
echo Restart server only (watchdog will revive)
echo =========================================

taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo Done. Server process was restarted.
echo Check logs\server.log if needed.
pause

