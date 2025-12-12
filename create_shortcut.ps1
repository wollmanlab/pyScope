# PowerShell script to create Windows shortcuts for all pyScope batch files
$WshShell = New-Object -comObject WScript.Shell
$basePath = "C:\GitRepos\pyScope"

# Function to convert PNG to ICO using Python with PIL/Pillow
function Convert-PngToIco {
    param(
        [string]$PngPath,
        [string]$IcoPath
    )
    
    # Find Python executable (same logic as batch files)
    $pythonExe = $null
    $condaEnvs = @(
        "C:\Users\wollmanlab\miniconda3\envs\pyscope_3.12\python.exe",
        "C:\Users\wollmanlab\miniconda3\envs\pycro_3.12\python.exe",
        "C:\Users\wollmanlab\.conda\envs\pyscope_3.12\python.exe",
        "C:\Users\wollmanlab\.conda\envs\pycro_3.12\python.exe"
    )
    
    foreach ($env in $condaEnvs) {
        if (Test-Path $env) {
            $pythonExe = $env
            break
        }
    }
    
    if (-not $pythonExe) {
        Write-Host "Python executable not found. Cannot convert PNG to ICO." -ForegroundColor Yellow
        return $false
    }
    
    try {
        # Create temporary Python script to convert PNG to ICO
        $tempScript = Join-Path $env:TEMP "convert_png_to_ico_$(Get-Random).py"
        # Use here-string with proper escaping
        $scriptContent = @"
from PIL import Image
import sys
import os

png_path = r'$($PngPath.Replace("'", "''"))'
ico_path = r'$($IcoPath.Replace("'", "''"))'

try:
    if not os.path.exists(png_path):
        print(f'Error: PNG file not found: {png_path}')
        sys.exit(1)
    
    img = Image.open(png_path)
    # Create ICO with multiple sizes for better compatibility
    img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print('Success')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"@
        $scriptContent | Out-File -FilePath $tempScript -Encoding UTF8
        
        # Run the conversion script
        $result = & $pythonExe $tempScript 2>&1
        $success = $LASTEXITCODE -eq 0 -or ($result -match "Success")
        
        # Cleanup
        Remove-Item $tempScript -ErrorAction SilentlyContinue
        
        if ($success -and (Test-Path $IcoPath)) {
            return $true
        }
        else {
            Write-Host "Conversion failed: $result" -ForegroundColor Yellow
            return $false
        }
    }
    catch {
        Write-Host "Error converting PNG to ICO: $_" -ForegroundColor Yellow
        return $false
    }
}

# Determine icon path and convert to ICO if needed
$pngPath = "$basePath\logo.png"
$icoPath = "$basePath\logo.ico"

if (Test-Path $pngPath) {
    # Convert PNG to ICO if ICO doesn't exist or PNG is newer
    if (-not (Test-Path $icoPath) -or (Get-Item $pngPath).LastWriteTime -gt (Get-Item $icoPath).LastWriteTime) {
        Write-Host "Converting logo.png to logo.ico..."
        if (Convert-PngToIco -PngPath $pngPath -IcoPath $icoPath) {
            Write-Host "Successfully created logo.ico" -ForegroundColor Green
        }
        else {
            Write-Host "Failed to convert PNG to ICO. Shortcut will be created without icon." -ForegroundColor Yellow
            $icoPath = $null
        }
    }
    else {
        Write-Host "Using existing pyScope.ico"
    }
}
else {
    Write-Host "pyScope.png not found. Shortcut will be created without icon." -ForegroundColor Yellow
    $icoPath = $null
}

# Define shortcuts to create
$shortcuts = @(
    @{
        Name = "pyScope"
        Target = "run_pyscope.bat"
        Description = "Run pyScope GUI"
        IconPath = $icoPath
    }
)

# Create each shortcut
foreach ($shortcutInfo in $shortcuts) {
    $Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\$($shortcutInfo.Name).lnk")
    $Shortcut.TargetPath = "$basePath\$($shortcutInfo.Target)"
    $Shortcut.WorkingDirectory = $basePath
    $Shortcut.Description = $shortcutInfo.Description
    if ($shortcutInfo.IconPath -and (Test-Path $shortcutInfo.IconPath)) {
        $Shortcut.IconLocation = $shortcutInfo.IconPath
        Write-Host "Icon set: $($shortcutInfo.IconPath)" -ForegroundColor Green
    }
    $Shortcut.Save()
    Write-Host "Shortcut created on Desktop: '$($shortcutInfo.Name).lnk'" -ForegroundColor Green
}

Write-Host ""
Write-Host "All shortcuts created successfully!"
Write-Host "You can now double-click any shortcut to run the corresponding pyScope component!"
