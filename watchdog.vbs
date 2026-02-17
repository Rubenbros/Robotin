' Watchdog: verifica que el bot está corriendo, si no lo arranca
Set objShell = CreateObject("WScript.Shell")
Set objWMI = GetObject("winmgmts:\\.\root\cimv2")

' Buscar si hay un proceso python ejecutando bot.main
Set colProcesses = objWMI.ExecQuery("SELECT * FROM Win32_Process WHERE Name = 'python.exe'")

botRunning = False
For Each objProcess In colProcesses
    cmdLine = objProcess.CommandLine
    If Not IsNull(cmdLine) Then
        If InStr(LCase(cmdLine), "bot.main") > 0 Then
            botRunning = True
            Exit For
        End If
    End If
Next

If Not botRunning Then
    ' Bot no está corriendo, arrancarlo
    botDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
    objShell.CurrentDirectory = botDir
    objShell.Run Chr(34) & botDir & "\start_bot.bat" & Chr(34), 0
End If

Set objWMI = Nothing
Set objShell = Nothing
