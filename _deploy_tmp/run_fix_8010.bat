@echo off
setlocal

set "APP=C:\Users\Administrator\Desktop\utc_web"
set "PORT=9010"

echo [1/6] Stop old Python and watchdog...
taskkill /IM python.exe /F >nul 2>&1
for %%P in (8112 7596 5612) do taskkill /PID %%P /F >nul 2>&1

echo [2/6] Disable system proxy...
netsh winhttp reset proxy >nul 2>&1
powershell -NoProfile -Command "Set-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' ProxyEnable 0" >nul 2>&1

echo [3/6] Clear debug log...
if exist "%APP%\gorei_debug.log" type nul > "%APP%\gorei_debug.log"

echo [4/6] Start server in background...
cd /d "%APP%"
start "utc_web_server_%PORT%" cmd /c "python -m uvicorn main:app --host 127.0.0.1 --port %PORT%"

echo [5/6] Wait for startup...
timeout /t 2 >nul

echo [6/6] Check and open browser...
powershell -NoProfile -Command ^
  "$ok = Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue; " ^
  "if(-not $ok){ Write-Host 'FAILED: server not listening on %PORT%'; exit 1 } ; " ^
  "Write-Host 'OK: listening on 127.0.0.1:%PORT%';"
if errorlevel 1 (
  echo.
  echo Server launch failed. Please run manually:
  echo   cd /d "%APP%"
  echo   python -m uvicorn main:app --host 127.0.0.1 --port %PORT%
  pause
  exit /b 1
)

start "" msedge --inprivate --disable-extensions "http://127.0.0.1:%PORT%/"
echo Done.
endlocal
