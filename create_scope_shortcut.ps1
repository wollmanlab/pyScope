# PowerShell script to create a Windows shortcut for Run Scope
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Run Scope.lnk")
$Shortcut.TargetPath = "C:\GitRepos\pyScope\run_scope.bat"
$Shortcut.WorkingDirectory = "C:\GitRepos\pyScope"
$Shortcut.Description = "Run pyScope continuous monitoring"
$Shortcut.Save()
Write-Host "Shortcut created on Desktop: 'Run Scope.lnk'"
Write-Host "You can now double-click the shortcut to run the scope!"

