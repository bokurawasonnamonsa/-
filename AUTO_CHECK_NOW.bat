@echo off
chcp 65001 >nul
cd /d "%~dp0."
echo Running connection + file checks...
echo Log: logs\utc_step_check.log
echo Summary: logs\utc_steps_summary.txt
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0utc_step_check.ps1"
set RC=%ERRORLEVEL%
echo.
echo Exit: 0=all OK deploy ready^| 1=TCP22 NG^| 2=TCP OK no secret file
pause
exit /b %RC%
