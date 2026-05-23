@echo off
setlocal

echo =========================================
echo Apply stability settings (Windows)
echo =========================================

echo [1/4] Disable sleep/hibernate on AC
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /h off

echo [2/4] Keep monitor on (optional for ops)
powercfg /change monitor-timeout-ac 0

echo [3/4] Prefer high performance policy
powercfg /setactive SCHEME_MIN >nul 2>&1
if errorlevel 1 (
  echo High performance plan not found, keeping current plan.
)

echo [4/4] Flush DNS cache
ipconfig /flushdns

echo done.
endlocal
