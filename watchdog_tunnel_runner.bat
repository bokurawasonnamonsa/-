@echo off
setlocal
cd /d "C:\Users\Administrator\Desktop\utc_web\"
:loop
echo [%date% %time%] tunnel A start>>"C:\Users\Administrator\Desktop\utc_web\logs\watchdog_tunnel.log"
"C:\Users\Administrator\Desktop\utc_web\cloudflared.exe" --protocol http2 tunnel run --token eyJhIjoiYmFkZGVkYzU1NDRlMDViNjQ5NTFmYTY1ZDc5ODQ4NDgiLCJ0IjoiM2YyYjAzNDktNzdmNy00NTc4LWE2MGMtMGJiZDJmMTg1ZjJjIiwicyI6IlkyUmtOMk5qTmpBdFpXTTVZaTAwWWpWakxUbGxNRGN0TURsaE5qUXhaV0ZqT0dFMyJ9 >>"C:\Users\Administrator\Desktop\utc_web\logs\cloudflared.log" 2>&1
echo [%date% %time%] tunnel A exited, restart in 1s>>"C:\Users\Administrator\Desktop\utc_web\logs\watchdog_tunnel.log"
timeout /t 1 /nobreak >nul
goto loop
