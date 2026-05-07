@echo off
setlocal
cd /d "C:\Users\Administrator\Desktop\utc_web\"
:loop
echo [%date% %time%] server start>>"C:\Users\Administrator\Desktop\utc_web\logs\watchdog_server.log"
python main.py >>"C:\Users\Administrator\Desktop\utc_web\logs\server.log" 2>&1
echo [%date% %time%] server exited, restart in 1s>>"C:\Users\Administrator\Desktop\utc_web\logs\watchdog_server.log"
timeout /t 1 /nobreak >nul
goto loop
