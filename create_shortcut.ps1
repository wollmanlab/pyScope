# PowerShell script to create a Windows shortcut
$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\Run Experiment.lnk")
$Shortcut.TargetPath = "C:\GitRepos\pyScope\run_experiment.bat"
$Shortcut.WorkingDirectory = "C:\GitRepos\pyScope"
$Shortcut.Description = "Run pyScope experiment"
$Shortcut.Save()

Write-Host "Shortcut created on Desktop: 'Run Experiment.lnk'"
Write-Host "You can now double-click the shortcut to run your experiment!"
