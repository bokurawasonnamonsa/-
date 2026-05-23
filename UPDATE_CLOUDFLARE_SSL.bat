@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_cloudflare_ssl.ps1"
exit /b %ERRORLEVEL%
