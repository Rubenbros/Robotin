$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\ClaudeTelegramBot.lnk")
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$PSScriptRoot\start_bot_hidden.vbs`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Save()
Write-Host "Shortcut de auto-arranque creado correctamente."
