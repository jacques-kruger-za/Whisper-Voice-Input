Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strProjectDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strProjectDir

' Use the project's venv Python 3.12 explicitly
strPythonW = strProjectDir & "\venv\Scripts\pythonw.exe"

If FSO.FileExists(strPythonW) Then
    WshShell.Run """" & strPythonW & """ -m src.main", 0, False
Else
    MsgBox "Python venv not found!" & vbCrLf & vbCrLf & _
           "Expected: " & strPythonW & vbCrLf & vbCrLf & _
           "Run setup: python -m venv venv && venv\Scripts\pip install -r requirements.txt", _
           vbCritical, "Whisper Voice Input"
End If
