Set fso = CreateObject("Scripting.FileSystemObject")
batPath = fso.GetParentFolderName(WScript.ScriptFullName) & "\start_bot.bat"

Set WshShell = CreateObject("WScript.Shell")
WshShell.Run chr(34) & batPath & chr(34), 0
Set WshShell = Nothing
Set fso = Nothing
