Option Explicit

Dim shell, fso, rootPath, pythonwPath, launcherPath
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

rootPath = fso.GetParentFolderName(WScript.ScriptFullName)
pythonwPath = fso.BuildPath(rootPath, ".venv\Scripts\pythonw.exe")
launcherPath = fso.BuildPath(rootPath, "launch_ui.py")

If Not fso.FileExists(pythonwPath) Then
  MsgBox "Job Alert is not set up yet." & vbCrLf & vbCrLf & "Missing file:" & vbCrLf & pythonwPath, vbExclamation, "Job Alert UI"
  WScript.Quit 1
End If

shell.Run """" & pythonwPath & """ """ & launcherPath & """", 0, False
