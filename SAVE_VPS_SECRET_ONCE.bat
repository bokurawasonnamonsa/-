@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Saving VPS password to vps_deploy_local.secret (local only, not for Git)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0save_vps_secret.ps1"
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" (
  echo.
  echo PowerShell exited with code %ERR%
)
echo.
pause
