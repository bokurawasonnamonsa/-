@echo off
chcp 65001 >nul
cd /d "%~dp0."
title UTC Web - PC auto (diagnose + wait + deploy)

echo ============================================================
echo This PC: logs/probes, wait for TCP 22, then deploy.
echo You only: ConoHa (Security Group + NIC) and VPS console if needed.
echo Close this window to stop waiting.
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pc_vps_auto.ps1"
set RC=%ERRORLEVEL%

echo.
echo Exit code %RC%
echo Log: logs\pc_vps_auto.log
echo Last probe: logs\last_tcp22_probe.txt
pause
exit /b %RC%
