@echo off
setlocal
cd /d "%~dp0"

echo [1] kill old processes
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM cloudflared.exe /F >nul 2>&1

echo [2] start app :8000 (main.py)
start "utc_app" /min cmd /c "cd /d %~dp0 && python main.py"

echo [3] wait app
timeout /t 3 >nul

echo [4] start tunnel (named tunnel token)
start "utc_tunnel" /min cmd /c "cd /d %~dp0 && .\cloudflared.exe tunnel run --token eyJhIjoiYmFkZGVkYzU1NDRlMDViNjQ5NTFmYTY1ZDc5ODQ4NDgiLCJ0IjoiM2YyYjAzNDktNzdmNy00NTc4LWE2MGMtMGJiZDJmMTg1ZjJjIiwicyI6IlkyUmtOMk5qTmpBdFpXTTVZaTAwWWpWakxUbGxNRGN0TURsaE5qUXhaV0ZqT0dFMyJ9"

echo [5] wait tunnel
timeout /t 3 >nul

echo [6] health check
for /f %%A in ('curl.exe -s -o NUL -w "%%{http_code}" http://127.0.0.1:8000/') do set LOCAL=%%A
for /f %%A in ('curl.exe -s -o NUL -w "%%{http_code}" https://3301-svs.jp/') do set PUBLIC=%%A

echo LOCAL  : %LOCAL%
echo PUBLIC : %PUBLIC%
echo.
if "%LOCAL%"=="200" if "%PUBLIC%"=="200" (
  echo OK: service restored.
) else (
  echo NG: check tunnel/domain settings.
)
endlocal
