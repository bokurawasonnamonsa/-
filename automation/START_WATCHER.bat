@echo off
echo Starting TactNode task watcher...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0watch_tasks.ps1"
pause
