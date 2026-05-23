@echo off
setlocal
cd /d "%~dp0"

REM Target VPS (override: set DEPLOY_VPS_IP=... before run)
if not defined DEPLOY_VPS_IP set "DEPLOY_VPS_IP=160.251.140.31"
REM ConoHaは root ではなく ubuntu のことがあります（ダメなら: set DEPLOY_VPS_USER=ubuntu）
if not defined DEPLOY_VPS_USER set "DEPLOY_VPS_USER=root"

set "VPS_IP=%DEPLOY_VPS_IP%"
set "VPS_USER=%DEPLOY_VPS_USER%"
set "ZIP_NAME=utc_web_deploy.zip"
set "REMOTE_ZIP=/tmp/utc_web.zip"
set "REMOTE_SCRIPT=/tmp/vps_setup_utc_web.sh"
set "STAGE=%TEMP%\utc_web_deploy_stage"

echo =========================================
echo UTC VPS one-click deploy
echo Target: %VPS_USER%@%VPS_IP%
echo =========================================

echo [1/5] create deploy zip (staging, no locked logs/binaries)
if exist "%STAGE%" rmdir /s /q "%STAGE%" 2>nul
mkdir "%STAGE%" 2>nul
REM %~dp0 の末尾 \ と " の組でパスが壊れるのを避ける
robocopy "%~dp0." "%STAGE%" /E /R:2 /W:2 /NFL /NDL /NJH /NJS ^
  /XD logs .git __pycache__ _deploy_tmp .cursor ^
  /XF utc_web_deploy.zip cloudflared.exe ngrok.exe
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
  echo FAILED: robocopy staging (code %RC%^)
  exit /b 1
)

powershell -NoProfile -Command ^
  "$z=Join-Path (Get-Location) '%ZIP_NAME%'; if (Test-Path $z) { Remove-Item -Force $z }; Compress-Archive -Path (Join-Path $env:TEMP 'utc_web_deploy_stage\\*') -DestinationPath $z -Force"
if errorlevel 1 (
  echo FAILED: zip creation
  exit /b 1
)

echo [2/5] upload app zip
scp -o StrictHostKeyChecking=accept-new "%ZIP_NAME%" %VPS_USER%@%VPS_IP%:%REMOTE_ZIP%
if errorlevel 1 (
  echo FAILED: scp app zip  Try: set DEPLOY_VPS_USER=ubuntu
  exit /b 1
)

echo [3/5] upload setup script
scp -o StrictHostKeyChecking=accept-new "vps_setup_utc_web.sh" %VPS_USER%@%VPS_IP%:%REMOTE_SCRIPT%
if errorlevel 1 (
  echo FAILED: scp setup script
  exit /b 1
)

echo [4/5] run remote setup
ssh -o StrictHostKeyChecking=accept-new %VPS_USER%@%VPS_IP% "chmod +x %REMOTE_SCRIPT% && bash %REMOTE_SCRIPT%"
if errorlevel 1 (
  echo FAILED: remote setup
  exit /b 1
)

echo [5/5] local cleanup
del /q "%ZIP_NAME%" >nul 2>&1
rmdir /s /q "%STAGE%" 2>nul

echo.
echo DONE.
echo Next: Cloudflare DNS の A レコードを %VPS_IP% に向ける（@ と www を確認）
endlocal
