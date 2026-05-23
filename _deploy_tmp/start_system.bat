@echo off
echo =========================================
echo  UTC司令塔システム 起動スクリプト (Cloudflare完全体版)
echo =========================================

:: サーバー(main.py)を別ウィンドウで起動
echo [1/2] サーバーを起動しています...
start cmd /k "title UTC_Server && cd /d %~dp0 && python main.py"

:: 少し待つ（サーバーが立ち上がる余裕を作る）
timeout /t 3 /nobreak >nul

:: 合言葉（トークン）を使って本番用トンネルを起動！
echo [2/2] Cloudflare(通信トンネル)を起動しています...
start cmd /k "title Cloudflare_Tunnel && cd /d %~dp0 && cloudflared tunnel run --token eyJhIjoiYmFkZGVkYzU1NDRlMDViNjQ5NTFmYTY1ZDc5ODQ4NDgiLCJ0IjoiM2YyYjAzNDktNzdmNy00NTc4LWE2MGMtMGJiZDJmMTg1ZjJjIiwicyI6IlkyUmtOMk5qTmpBdFpXTTVZaTAwWWpWakxUbGxNRGN0TURsaE5qUXhaV0ZqT0dFMyJ9"

echo.
echo 起動処理が完了しました！
echo （サーバーとCloudflareの2つの黒い画面が開いたままになります）
pause