@echo off
setlocal
set "APP=C:\Users\Administrator\Desktop\utc_web"
set "LOG=%APP%\logs\server.log"

if not exist "%APP%" (
  echo ERROR: folder not found: %APP%
  pause
  exit /b 1
)

if not exist "%LOG%" (
  echo ERROR: server log not found: %LOG%
  pause
  exit /b 1
)

echo === Mobile WS check ===
echo Open 3301-svs.jp from mobile now.
echo If connected, "WebSocket /ws" lines should appear below.
echo Press Ctrl+C to stop watching.
echo.

powershell -NoProfile -Command "Get-Content '%LOG%' -Wait -Tail 40"

endlocal
