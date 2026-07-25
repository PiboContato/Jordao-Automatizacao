$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupFolder "AgenteJordao_Startup.lnk"

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "c:\projetos\Jordao Automatizacao\iniciar_painel.bat"
$shortcut.WorkingDirectory = "c:\projetos\Jordao Automatizacao"
$shortcut.WindowStyle = 7 # Minimized
$shortcut.Save()

Write-Host "Atalho de inicialização automática criado com sucesso:"
Write-Host $shortcutPath
