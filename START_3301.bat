@echo off
setlocal
set "APP=C:\Users\Administrator\Desktop\utc_web"
set "LOG=%APP%\start_3301_result.log"
title START_3301

if not exist "%APP%" (
  echo ERROR: APP folder not found: %APP%
  pause
  exit /b 1
)
cd /d "%APP%"
echo [%date% %time%] START_3301 begin > "%LOG%"

echo [1] Stop old processes
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1

echo [2] Start app (8000)
start "utc_app" /min cmd /c "cd /d %APP% && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo [3] Wait app
timeout /t 3 >nul

echo [4] Start cloudflared tunnel
start "utc_tunnel" /min cmd /c "cd /d %APP% && .\cloudflared.exe tunnel run --token eyJhIjoiYmFkZGVkYzU1NDRlMDViNjQ5NTFmYTY1ZDc5ODQ4NDgiLCJ0IjoiM2YyYjAzNDktNzdmNy00NTc4LWE2MGMtMGJiZDJmMTg1ZjJjIiwicyI6IlkyUmtOMk5qTmpBdFpXTTVZaTAwWWpWakxUbGxNRGN0TURsaE5qUXhaV0ZqT0dFMyJ9"

echo [5] Wait tunnel
timeout /t 5 >nul

echo [6] Check status
for /f %%A in ('curl.exe -s -o NUL -w "%%{http_code}" http://127.0.0.1:8000/') do set LOCAL=%%A
for /f %%A in ('curl.exe -s -o NUL -w "%%{http_code}" https://3301-svs.jp/') do set PUBLIC=%%A

echo LOCAL=%LOCAL%
echo PUBLIC=%PUBLIC%
echo LOCAL=%LOCAL%>>"%LOG%"
echo PUBLIC=%PUBLIC%>>"%LOG%"
echo.
echo [7] Process list
powershell -NoProfile -Command "Get-Process python,cloudflared -ErrorAction SilentlyContinue | Select-Object Name,Id"
powershell -NoProfile -Command "Get-Process python,cloudflared -ErrorAction SilentlyContinue | Select-Object Name,Id | Out-File -FilePath '%LOG%' -Append"

echo.
echo Log saved: %LOG%
pause
endlocal
