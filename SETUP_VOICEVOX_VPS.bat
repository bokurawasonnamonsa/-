@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_voicevox_vps.ps1"
exit /b %ERRORLEVEL%
