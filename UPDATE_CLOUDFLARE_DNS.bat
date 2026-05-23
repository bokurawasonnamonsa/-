@echo off
chcp 65001 >nul
cd /d "%~dp0."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_cloudflare_a.ps1"
echo.
pause
exit /b %ERRORLEVEL%
