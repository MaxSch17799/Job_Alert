@echo off
setlocal
cd /d "%~dp0"
title Job Alert Manual Run

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

echo Running one manual scrape...
echo.

".venv\Scripts\python.exe" "run_job_alert.py"
set EXIT_CODE=%ERRORLEVEL%

echo.
if "%EXIT_CODE%"=="0" (
  echo Manual scrape finished.
) else (
  echo Manual scrape stopped with an error. Exit code: %EXIT_CODE%
)
pause
exit /b %EXIT_CODE%
