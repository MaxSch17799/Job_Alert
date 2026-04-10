@echo off
setlocal
cd /d "%~dp0"

if exist "Start Job Alert UI.vbs" (
  wscript.exe //nologo "Start Job Alert UI.vbs"
  exit /b 0
)

if not exist ".venv\Scripts\pythonw.exe" (
  powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('Job Alert is not set up yet.`n`nMissing file:`n.venv\\Scripts\\pythonw.exe', 'Job Alert UI') | Out-Null"
  exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "launch_ui.py"
exit /b 0
