@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

REM Your repo: https://github.com/bokurawasonnamonsa/-
set "REPO=https://github.com/bokurawasonnamonsa/-.git"

git remote get-url origin >nul 2>&1
if errorlevel 1 (
  git remote add origin "%REPO%"
) else (
  echo Current origin:
  git remote get-url origin
)

echo Pushing to origin...
git push -u origin master
if errorlevel 1 (
  echo Trying branch main...
  git branch -M main
  git push -u origin main
)

echo.
echo Done.
pause
