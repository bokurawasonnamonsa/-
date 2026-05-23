@echo off
setlocal EnableExtensions
if "%~1"=="" exit /b 1

set "HOOK_DIR=%~dp0"
set "REPO=%HOOK_DIR%..\.."
cd /d "%REPO%" 2>nul
if errorlevel 1 exit /b 1

set "SCRIPT=%HOOK_DIR%%~1"
if not exist "%SCRIPT%" exit /b 1

set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "PYTHONWARNINGS=ignore"

if defined UTC_PYTHON (
  "%UTC_PYTHON%" -u "%SCRIPT%"
  exit /b %ERRORLEVEL%
)

where py >nul 2>&1
if not errorlevel 1 (
  py -3 -u "%SCRIPT%"
  exit /b %ERRORLEVEL%
)

if exist "%LocalAppData%\Programs\Python\Python314\python.exe" (
  "%LocalAppData%\Programs\Python\Python314\python.exe" -u "%SCRIPT%"
  exit /b %ERRORLEVEL%
)

where python >nul 2>&1
if not errorlevel 1 (
  for /f "delims=" %%P in ('where python 2^>nul ^| findstr /i /v WindowsApps') do (
    "%%P" -u "%SCRIPT%"
    exit /b !ERRORLEVEL!
  )
)

exit /b 9009
