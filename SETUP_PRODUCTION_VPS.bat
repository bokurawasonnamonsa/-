@echo off

chcp 65001 >nul

cd /d "%~dp0."

title UTC - VPS production setup (one-time)



echo ============================================================

echo 本番: VPS 一本化 (3301-svs.jp)

echo ============================================================

echo.

echo [Step 1] VPS SSH password (local file, not Git)

if not exist "vps_deploy_local.secret" (

  echo   -> Run SAVE_VPS_SECRET_ONCE.bat now.

  echo.

  call "%~dp0SAVE_VPS_SECRET_ONCE.bat"

) else (

  echo   OK: vps_deploy_local.secret exists

)

echo.

echo [Step 2] Cloudflare A record -> VPS IP

if not exist "cloudflare_dns_config.ps1" (

  echo   -> Copy cloudflare_dns_config.EXAMPLE.ps1 to cloudflare_dns_config.ps1

  echo   -> Set CF_API_TOKEN and CF_TARGET_IP=%DEPLOY_VPS_IP%

  echo   -> Then run UPDATE_CLOUDFLARE_DNS.bat

  echo.

) else (

  echo   OK: cloudflare_dns_config.ps1 exists

  echo   -> Run UPDATE_CLOUDFLARE_DNS.bat to sync A record

)

echo.

echo [Step 3] Stop local PC tunnel (avoid double production)

call "%~dp0STOP_LOCAL_PRODUCTION.bat"

echo.

echo [Step 4] Pre-flight QA

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0qa_production_check.ps1"

echo.

echo [Step 5] First deploy (optional)

set /p DO_DEPLOY="Run DEPLOY_PRODUCTION.bat now? [y/N]: "

if /i "%DO_DEPLOY%"=="y" call "%~dp0DEPLOY_PRODUCTION.bat"

echo.

echo Done. Daily use: DEPLOY_PRODUCTION.bat then refresh https://3301-svs.jp

pause

