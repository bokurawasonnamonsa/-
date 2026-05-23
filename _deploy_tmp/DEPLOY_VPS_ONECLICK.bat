@echo off
setlocal
cd /d "%~dp0"

set "VPS_IP=160.251.140.31"
set "VPS_USER=root"
set "ZIP_NAME=utc_web_deploy.zip"
set "REMOTE_ZIP=/tmp/utc_web.zip"
set "REMOTE_SCRIPT=/tmp/vps_setup_utc_web.sh"

echo =========================================
echo UTC VPS one-click deploy
echo Target: %VPS_USER%@%VPS_IP%
echo =========================================

echo [1/5] create deploy zip
powershell -NoProfile -Command "if (Test-Path '%ZIP_NAME%') { Remove-Item -Force '%ZIP_NAME%' }; Compress-Archive -Path * -DestinationPath '%ZIP_NAME%' -Force"
if errorlevel 1 (
  echo FAILED: zip creation
  exit /b 1
)

echo [2/5] upload app zip
scp -o StrictHostKeyChecking=accept-new "%ZIP_NAME%" %VPS_USER%@%VPS_IP%:%REMOTE_ZIP%
if errorlevel 1 (
  echo FAILED: scp app zip
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

echo.
echo DONE.
echo Next (manual): Cloudflare A record 3301-svs.jp -> %VPS_IP%
echo Recommended first: DNS only (gray cloud), then verify, then Proxy ON.
endlocal
