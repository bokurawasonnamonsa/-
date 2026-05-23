@echo off
setlocal
set "BASE=%~dp0"
set "LOG_DIR=%BASE%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
cd /d "%BASE%"
:loop
echo [%date% %time%] server start>>"%LOG_DIR%\watchdog_server.log"
python main.py >>"%LOG_DIR%\server.log" 2>&1
echo [%date% %time%] server exited, restart in 1s>>"%LOG_DIR%\watchdog_server.log"
timeout /t 1 /nobreak >nul
goto loop
