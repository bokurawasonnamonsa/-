@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo === Push to GitHub ===
echo New repo: open https://github.com/new  create EMPTY repo no README
echo.

git remote get-url origin >nul 2>&1
if errorlevel 1 goto ADD_REMOTE

echo Current remote origin:
git remote get-url origin
echo.
set /p GO="Push now? Y/N: "
if /i not "!GO!"=="Y" exit /b 0
goto DO_PUSH

:ADD_REMOTE
set "REPO_URL="
set /p REPO_URL="Paste HTTPS URL for example https://github.com/user/repo.git : "
if "!REPO_URL!"=="" (
  echo ERROR: URL was empty.
  pause
  exit /b 1
)
git remote add origin "!REPO_URL!"
if errorlevel 1 (
  echo ERROR: git remote add failed.
  pause
  exit /b 1
)

:DO_PUSH
echo.
echo Pushing...
git push -u origin master
if errorlevel 1 (
  echo.
  echo If push failed try main branch:
  echo   git branch -M main
  echo   git push -u origin main
  pause
  exit /b 1
)

echo.
echo Done.
pause
