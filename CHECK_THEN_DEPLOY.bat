@echo off
chcp 65001 >nul
cd /d "%~dp0."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0utc_step_check.ps1"
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
  echo Check failed (code %RC%). Fix ConoHa or run SAVE_VPS_SECRET_ONCE.bat.
  pause
  exit /b %RC%
)
echo.
echo Check OK -> starting deploy...
call "%~dp0RUN_PC_AUTO_ALL.bat"
exit /b %ERRORLEVEL%
