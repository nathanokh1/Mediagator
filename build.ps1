# Mediagator - Windows build script
# Run from repo root in an elevated PowerShell session:
#   .\build.ps1
#   .\build.ps1 -Clean          (wipe dist/ and build/ first)
#   .\build.ps1 -Clean -Onefile (also produce a single portable .exe)
#   .\build.ps1 -Installer      (also compile Inno Setup installer)
#
# Output: dist\Mediagator\Mediagator.exe

param(
    [switch]$Clean     = $false,
    [switch]$Onefile   = $false,
    [switch]$Installer = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== Mediagator Build ===" -ForegroundColor Cyan
Write-Host "Working directory: $(Get-Location)"

# 1. Clean
if ($Clean) {
    Write-Host ""
    Write-Host "[1/4] Cleaning previous build artefacts..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist, build, __pycache__
    Write-Host "      Cleaned."
}

# Always remove runtime-generated folders from a previous dist before rebuilding.
# These can have open file handles (e.g. app.log) that cause PyInstaller to fail.
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "dist\Mediagator\logs"
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "dist\Mediagator\reports"

# 2. Install dependencies
Write-Host ""
Write-Host "[2/4] Installing requirements..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
Write-Host "      Done."

# 3. Write version resource file
Write-Host ""
Write-Host "[3/4] Writing version info..." -ForegroundColor Yellow
$v = "VSVersionInfo(`n" +
     "  ffi=FixedFileInfo(filevers=(1,0,0,0),prodvers=(1,0,0,0),mask=0x3f,flags=0x0,OS=0x40004,fileType=0x1,subtype=0x0,date=(0,0)),`n" +
     "  kids=[`n" +
     "    StringFileInfo([StringTable(u'040904B0',[`n" +
     "      StringStruct(u'CompanyName',u'Nathan'),`n" +
     "      StringStruct(u'FileDescription',u'Mediagator - Media Transfer and Organisation Tool'),`n" +
     "      StringStruct(u'FileVersion',u'1.0.0'),`n" +
     "      StringStruct(u'InternalName',u'Mediagator'),`n" +
     "      StringStruct(u'LegalCopyright',u'Copyright 2026 Nathan. MIT License.'),`n" +
     "      StringStruct(u'OriginalFilename',u'Mediagator.exe'),`n" +
     "      StringStruct(u'ProductName',u'Mediagator'),`n" +
     "      StringStruct(u'ProductVersion',u'1.0.0')])]),`n" +
     "    VarFileInfo([VarStruct(u'Translation',[1033,1200])])`n" +
     "  ]`n" +
     ")"
$v | Set-Content -Path "version_info.txt" -Encoding UTF8
Write-Host "      version_info.txt written."

# 4. PyInstaller folder bundle
Write-Host ""
Write-Host "[4/4] Running PyInstaller..." -ForegroundColor Yellow
pyinstaller Mediagator.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "      Folder bundle ready: dist\Mediagator\" -ForegroundColor Green

# Optional: single-file portable .exe
if ($Onefile) {
    Write-Host ""
    Write-Host "[5] Building single-file portable .exe..." -ForegroundColor Yellow
    pyinstaller src/main.py --name Mediagator_portable --onefile --noconsole --icon assets/icon.ico --uac-admin --add-data "assets;assets" --noconfirm
    Write-Host "    Portable .exe: dist\Mediagator_portable.exe" -ForegroundColor Green
}

# Optional: Inno Setup installer
if ($Installer) {
    Write-Host ""
    Write-Host "[6] Building Inno Setup installer..." -ForegroundColor Yellow

    # Look for ISCC.exe: system PATH first, then standard install locations
    $isccPath = $null
    $candidates = @(
        "ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        "C:\Program Files\Inno Setup 5\ISCC.exe"
    )
    foreach ($c in $candidates) {
        if (Get-Command $c -ErrorAction SilentlyContinue) { $isccPath = $c; break }
        if (Test-Path $c) { $isccPath = $c; break }
    }

    if (-not $isccPath) {
        Write-Host "    ISCC.exe not found - skipping." -ForegroundColor Yellow
        Write-Host "    Download Inno Setup from https://jrsoftware.org/isinfo.php"
    } else {
        Write-Host "    Using: $isccPath"
        & $isccPath installer\Mediagator.iss
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    Installer ready: dist\Mediagator_Setup_1.0.0.exe" -ForegroundColor Green
        } else {
            Write-Host "    Inno Setup failed (exit $LASTEXITCODE)" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Cyan
Write-Host "Output: dist\Mediagator\Mediagator.exe"
