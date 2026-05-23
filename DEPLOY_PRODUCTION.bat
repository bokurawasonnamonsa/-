@echo off

chcp 65001 >nul

cd /d "%~dp0."

title UTC - Deploy to VPS (production)



echo ============================================================

echo DEPLOY_PRODUCTION: VPS only (config\production.json)

echo Target: https://3301-svs.jp/

echo ============================================================

echo.



if not exist "config\production.json" (

  echo ERROR: missing config\production.json

  pause

  exit /b 2

)



if not exist "vps_deploy_local.secret" (

  echo ERROR: run SAVE_VPS_SECRET_ONCE.bat first.

  pause

  exit /b 2

)



echo [1/4] Stop local tunnel processes (PC must not serve production)

call "%~dp0STOP_LOCAL_PRODUCTION.bat"



echo.

echo [2/4] Pre-deploy QA

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0qa_production_check.ps1"

echo.



echo [3/4] Deploy to VPS (ZIP + remote setup + systemd restart)

pip install paramiko --quiet

if errorlevel 1 (

  echo pip install paramiko failed

  pause

  exit /b 1

)

python "%~dp0vps_deploy_with_password.py"

set DEPLOY_RC=%ERRORLEVEL%

if not "%DEPLOY_RC%"=="0" (

  echo.

  echo DEPLOY FAILED exit=%DEPLOY_RC%

  echo Log: logs\deploy_auto.log

  pause

  exit /b %DEPLOY_RC%

)



echo.

echo [4/4] Verify https://3301-svs.jp

timeout /t 5 >nul

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0VERIFY_PRODUCTION.ps1"

set VERIFY_RC=%ERRORLEVEL%



echo.

if "%VERIFY_RC%"=="0" (

  echo SUCCESS: production deploy + HTTP check OK.

  echo Open: https://3301-svs.jp/

) else (

  echo WARN: deploy OK but HTTP check failed. Check Cloudflare DNS / nginx on VPS.

)

pause

exit /b %VERIFY_RC%

