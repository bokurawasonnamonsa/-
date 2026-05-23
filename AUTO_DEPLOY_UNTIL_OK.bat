@echo off
chcp 65001 >nul
cd /d "%~dp0."

if not exist "vps_deploy_local.secret" (
  echo ============================================================
  echo Run SAVE_VPS_SECRET_ONCE.bat once first.
  echo ============================================================
  echo.
  pause
  exit /b 2
)

echo Retrying until success. Close window to stop.
echo Log: logs\deploy_auto.log
echo.

pip install paramiko --quiet
if errorlevel 1 (
  echo pip install FAILED
  echo.
  echo Press any key to close this window.
  pause >nul
  exit /b 1
)

set UTC_DEPLOY_UNTIL_OK=1
set UTC_DEPLOY_RETRY_SEC=45
REM set UTC_DEPLOY_MAX_MINUTES=480

python "%~dp0vps_deploy_with_password.py"
set "RC=%ERRORLEVEL%"
echo.
echo Exit code %RC%
echo Press any key to close this window.
pause >nul
exit /b %RC%
