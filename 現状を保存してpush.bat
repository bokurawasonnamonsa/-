@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ===== Save current work and push to GitHub =====
echo.

git add -A
if errorlevel 1 (
  echo git add failed.
  pause
  exit /b 1
)

echo --- git status ---
git status --short
echo.

set /p MSG="Commit message (Enter = use default): "
if "!MSG!"=="" set "MSG=Update: save work in progress"

git commit -m "!MSG!"
if errorlevel 1 (
  echo No new changes to commit, or commit failed. Trying push anyway...
) else (
  echo Committed.
)
echo.

git push
if errorlevel 1 (
  echo push failed.
  pause
  exit /b 1
)

echo.
echo Done. On another PC: run 続きから始める.bat
pause
