@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Adding .gitignore and .env.example ...
git add .gitignore .env.example
if errorlevel 1 (
  echo git add failed.
  pause
  exit /b 1
)

echo Committing ...
git commit -m "Track .env.example; unignore in gitignore"
if errorlevel 1 (
  echo Nothing to commit or commit failed.
  pause
  exit /b 1
)

echo Pushing ...
git push
if errorlevel 1 (
  echo git push failed.
  pause
  exit /b 1
)

echo Done.
pause
