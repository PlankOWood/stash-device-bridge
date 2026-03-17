@echo off

echo Starting motion controller...
start cmd /k python "%USERPROFILE%\.stash\plugins\device-bridge\controller\main.py"

timeout /t 2 >nul

echo Starting Stash...
start "" "%USERPROFILE%\Desktop\stash-win.exe"