@echo off
setlocal
cd /d "%~dp0"

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LAUNCHER=%STARTUP_DIR%\UTC_AutoHeal_3301.cmd"
set "APP_DIR=%~dp0"
set "APP_DIR=%APP_DIR:~0,-1%"

if not exist "%STARTUP_DIR%" (
  echo startup folder not found: "%STARTUP_DIR%"
  exit /b 1
)

(
  echo @echo off
  echo chcp 65001 ^>nul
  echo set "APP_DIR=%APP_DIR%"
  echo if not exist "%%APP_DIR%%\AUTO_HEAL_3301.bat" exit /b 1
  echo cd /d "%%APP_DIR%%"
  echo start "UTC_AUTO_HEAL" /min "%%APP_DIR%%\AUTO_HEAL_3301.bat"
) > "%LAUNCHER%"

echo installed:
echo %LAUNCHER%
echo.
echo apply now: logoff/login or run START_24x7.bat

endlocal
