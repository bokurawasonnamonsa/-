@echo off
chcp 65001 >nul
cd /d "%~dp0"
(
echo === START %DATE% %TIME% ===
git config --global user.name "鎌田諒"
git config --global user.email "bokurawasonnamonsa@gmail.com"
echo GLOBAL user.name:
git config --global user.name
echo GLOBAL user.email:
git config --global user.email
git add -A 2>&1
git commit -m "Initial commit" 2>&1
echo ---
git status 2>&1
git remote -v 2>&1
echo === END ===
) > "%~dp0_cursor_git_run.log" 2>&1
