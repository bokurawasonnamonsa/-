@echo off
chcp 65001 >nul
cd /d "%~dp0."

if not exist "vps_deploy_local.secret" (
  echo ============================================================
  echo Run SAVE_VPS_SECRET_ONCE.bat once first.
  echo Then run this ONECLICK_VPS_DEPLOY.bat again.
  echo ============================================================
  echo.
  pause
  exit /b 2
)

echo [ONECLICK] VPS deploy to 160.251.140.31
pip install paramiko --quiet
if errorlevel 1 (
  echo pip install FAILED
  goto :DONE_BAD
)

python "%~dp0vps_deploy_with_password.py"
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo OK. Set Cloudflare A record: 3301-svs.jp -^> 160.251.140.31
) else (
  echo FAIL code %RC%. Check ConoHa security group: IN TCP 22, 80, 443 on this VM.
)
goto :DONE

:DONE_BAD
set RC=1

:DONE
echo.
echo Press any key to close this window.
pause >nul
exit /b %RC%
