@echo off
setlocal
cd /d "%~dp0"
title Job Alert UI

if not exist ".venv\Scripts\python.exe" (
  echo Job Alert is not set up yet.
  echo.
  echo Missing file:
  echo   .venv\Scripts\python.exe
  echo.
  echo Run the setup steps from README.md first.
  pause
  exit /b 1
)

echo Starting Job Alert UI...
echo Your browser should open automatically at http://127.0.0.1:5000
echo Keep this window open while you use the app.
echo Press Ctrl+C in this window to stop it.
echo.

".venv\Scripts\python.exe" "launch_ui.py"
set EXIT_CODE=%ERRORLEVEL%

if not "%EXIT_CODE%"=="0" (
  echo.
  echo Job Alert UI stopped with an error. Exit code: %EXIT_CODE%
  pause
)

exit /b %EXIT_CODE%
