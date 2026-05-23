@echo off
chcp 65001 >nul
cd /d "%~dp0."

if not exist "vps_deploy_local.secret" (
  echo Missing vps_deploy_local.secret — run SAVE_VPS_SECRET_ONCE.bat first.
  echo.
  pause
  exit /b 2
)

echo ============================================================
echo FULL AUTO on this PC:
echo   1^) Wait until port 22 on 160.251.140.31 answers
echo   2^) Run deploy (ZIP + upload + remote setup)
echo ConoHa: attach security group to THIS VPS NIC in the meantime.
echo Close this window (^+C twice in PowerShell) to stop waiting.
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0wait_ssh_then_deploy.ps1"
set RC=%ERRORLEVEL%

echo.
echo Exit code %RC%
pause
exit /b %RC%
