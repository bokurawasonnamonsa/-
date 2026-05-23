@echo off

chcp 65001 >nul

cd /d "%~dp0."

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0VERIFY_PRODUCTION.ps1"

set RC=%ERRORLEVEL%

echo.

if "%RC%"=="0" (echo HTTP check OK) else (echo HTTP check FAILED)

pause

exit /b %RC%

