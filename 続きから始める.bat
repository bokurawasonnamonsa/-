@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo First time on this PC: clone the repo once, then use this file inside the folder.
echo   git clone https://github.com/bokurawasonnamonsa/-.git
echo.
echo ===== Continue work (pull + Cursor) =====
echo Folder: %CD%
echo.

echo [1/3] git pull ...
git pull
if errorlevel 1 (
  echo.
  echo ERROR: git pull failed. Check network, login, or remote URL.
  pause
  exit /b 1
)
echo OK
echo.

echo [2/3] GEMINI_API_KEY check ...
if defined GEMINI_API_KEY (
  echo OK: GEMINI_API_KEY is set in this CMD session.
) else (
  echo WARNING: GEMINI_API_KEY is empty in this window.
  echo If AI features fail, set it once:
  echo   setx GEMINI_API_KEY "your-key-here"
  echo Then restart Cursor and terminals.
)
echo.

echo [3/3] Opening Cursor in this folder ...
set "CURSOR_EXE=%LOCALAPPDATA%\Programs\cursor\Cursor.exe"
if exist "%CURSOR_EXE%" (
  start "" "%CURSOR_EXE%" "%CD%"
  goto OPENED
)
where cursor >nul 2>&1
if not errorlevel 1 (
  start "" cursor "%CD%"
  goto OPENED
)
echo Cursor CLI not found. Opening folder in Explorer - open it manually in Cursor.
explorer "%CD%"
:OPENED

echo.
echo Done. In Cursor: start a new chat and use @ to attach files or this folder.
pause
