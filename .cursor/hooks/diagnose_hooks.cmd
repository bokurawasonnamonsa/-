@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."
echo === UTC Web hook diagnose ===
echo Repo: %CD%
echo.

set "PAYLOAD={\"file_path\":\"%CD%\\player.html\",\"edits\":[]}"
echo %PAYLOAD%| .cursor\hooks\run_hook.cmd on_after_file_edit.py
echo afterFileEdit exit=%ERRORLEVEL%
echo.

set "PAYLOAD={\"command\":\"python scripts/production_auto_pipeline.py verify-only\"}"
echo %PAYLOAD%| .cursor\hooks\run_hook.cmd allow_production_shell.py
echo beforeShell exit=%ERRORLEVEL%
echo.

set "PAYLOAD={\"status\":\"completed\",\"loop_count\":0}"
echo %PAYLOAD%| .cursor\hooks\run_hook.cmd on_stop_production_loop.py
echo stop exit=%ERRORLEVEL%
echo.
echo Done. All should print {} and exit=0.
pause
