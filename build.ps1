# Mediagator - Windows build script
# Run from repo root in an elevated PowerShell session.
#
# Usage:
#   .\build.ps1                          # standard build (folder bundle)
#   .\build.ps1 -Clean                   # wipe dist/ and build/ first
#   .\build.ps1 -Installer               # also compile Inno Setup installer
#   .\build.ps1 -Installer -Release 1.0.5
#       Bumps version to 1.0.5, builds installer, commits, tags, pushes to
#       GitHub, creates a GitHub Release, and uploads the installer as an asset.
#       Requires: gh CLI (winget install GitHub.cli) authenticated with gh auth login
#
# Output: dist\Mediagator\Mediagator.exe

param(
    [switch]$Clean     = $false,
    [switch]$Onefile   = $false,
    [switch]$Installer = $false,
    [string]$Release   = ""        # pass a version string e.g. -Release 1.0.5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helper: bump a version string inside a file using simple string replace
# ---------------------------------------------------------------------------
function Update-Version {
    param([string]$FilePath, [string]$OldVer, [string]$NewVer)
    $content = Get-Content $FilePath -Raw
    $updated = $content -replace [regex]::Escape($OldVer), $NewVer
    Set-Content -Path $FilePath -Value $updated -Encoding UTF8 -NoNewline
}

# ---------------------------------------------------------------------------
# Determine the current and target version
# ---------------------------------------------------------------------------
$constantsFile = "src\config\constants.py"
$currentVersion = (Select-String -Path $constantsFile -Pattern 'APP_VERSION\s*=\s*"([\d.]+)"').Matches[0].Groups[1].Value

if ($Release -ne "") {
    $targetVersion = $Release.TrimStart("v")
} else {
    $targetVersion = $currentVersion
}

Write-Host "=== Mediagator Build ===" -ForegroundColor Cyan
Write-Host "Working directory : $(Get-Location)"
Write-Host "Current version   : $currentVersion"
if ($Release -ne "") {
    Write-Host "Release version   : $targetVersion" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 0. Version bump (only when -Release is specified)
# ---------------------------------------------------------------------------
if ($Release -ne "" -and $targetVersion -ne $currentVersion) {
    Write-Host ""
    Write-Host "[0] Bumping version $currentVersion -> $targetVersion ..." -ForegroundColor Yellow

    # constants.py
    Update-Version $constantsFile "APP_VERSION = `"$currentVersion`"" "APP_VERSION = `"$targetVersion`""

    # installer .iss
    $issFile = "installer\Mediagator.iss"
    Update-Version $issFile $currentVersion $targetVersion

    # this build.ps1 itself (hardcoded version strings in version_info section)
    Update-Version "build.ps1" $currentVersion $targetVersion

    Write-Host "      Version files updated."
}

# ---------------------------------------------------------------------------
# 1. Clean
# ---------------------------------------------------------------------------
if ($Clean) {
    Write-Host ""
    Write-Host "[1/4] Cleaning previous build artefacts..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist, build, __pycache__
    Write-Host "      Cleaned."
}

# Always remove runtime-generated folders that can have open file handles.
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "dist\Mediagator\logs"
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "dist\Mediagator\reports"

# ---------------------------------------------------------------------------
# 2. Install dependencies
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[2/4] Installing requirements..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
Write-Host "      Done."

# ---------------------------------------------------------------------------
# 3. Write version resource file
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[3/4] Writing version info..." -ForegroundColor Yellow
$vParts = $targetVersion -split "\."
while ($vParts.Count -lt 4) { $vParts += "0" }
$vTuple = "($($vParts[0]),$($vParts[1]),$($vParts[2]),$($vParts[3]))"
$v = "VSVersionInfo(`n" +
     "  ffi=FixedFileInfo(filevers=$vTuple,prodvers=$vTuple,mask=0x3f,flags=0x0,OS=0x40004,fileType=0x1,subtype=0x0,date=(0,0)),`n" +
     "  kids=[`n" +
     "    StringFileInfo([StringTable(u'040904B0',[`n" +
     "      StringStruct(u'CompanyName',u'Nathan'),`n" +
     "      StringStruct(u'FileDescription',u'Mediagator - Media Transfer and Organisation Tool'),`n" +
     "      StringStruct(u'FileVersion',u'$targetVersion'),`n" +
     "      StringStruct(u'InternalName',u'Mediagator'),`n" +
     "      StringStruct(u'LegalCopyright',u'Copyright 2026 Nathan. MIT License.'),`n" +
     "      StringStruct(u'OriginalFilename',u'Mediagator.exe'),`n" +
     "      StringStruct(u'ProductName',u'Mediagator'),`n" +
     "      StringStruct(u'ProductVersion',u'$targetVersion')])]),`n" +
     "    VarFileInfo([VarStruct(u'Translation',[1033,1200])])`n" +
     "  ]`n" +
     ")"
$v | Set-Content -Path "version_info.txt" -Encoding UTF8
Write-Host "      version_info.txt written."

# ---------------------------------------------------------------------------
# 4. PyInstaller folder bundle
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[4/4] Running PyInstaller..." -ForegroundColor Yellow
pyinstaller Mediagator.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed (exit $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "      Folder bundle ready: dist\Mediagator\" -ForegroundColor Green

# ---------------------------------------------------------------------------
# Optional: single-file portable .exe
# ---------------------------------------------------------------------------
if ($Onefile) {
    Write-Host ""
    Write-Host "[5] Building single-file portable .exe..." -ForegroundColor Yellow
    pyinstaller src/main.py --name Mediagator_portable --onefile --noconsole --icon assets/icon.ico --add-data "assets;assets" --noconfirm
    Write-Host "    Portable .exe: dist\Mediagator_portable.exe" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# Optional: Inno Setup installer
# ---------------------------------------------------------------------------
$installerExe = ""
if ($Installer) {
    Write-Host ""
    Write-Host "[6] Building Inno Setup installer..." -ForegroundColor Yellow

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
        $buildOut = "$env:LOCALAPPDATA\MediagatorBuild"
        New-Item -ItemType Directory -Force $buildOut | Out-Null
        & $isccPath installer\Mediagator.iss
        if ($LASTEXITCODE -eq 0) {
            $setupName = "Mediagator_Setup_$targetVersion.exe"
            $src = "$buildOut\$setupName"
            $dst = "dist\$setupName"
            if (Test-Path $src) {
                Copy-Item $src $dst -Force
                $installerExe = (Resolve-Path $dst).Path
                Write-Host "    Installer ready: $dst" -ForegroundColor Green
            } else {
                Write-Host "    Installer compiled (check $buildOut)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "    Inno Setup failed (exit $LASTEXITCODE)" -ForegroundColor Red
        }
    }
}

# ---------------------------------------------------------------------------
# Optional: GitHub Release
# Requires -Installer (need the .exe) and -Release <version>
# ---------------------------------------------------------------------------
if ($Release -ne "" -and $Installer) {
    Write-Host ""
    Write-Host "[7] Creating GitHub Release v$targetVersion ..." -ForegroundColor Yellow

    # Check gh is available
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Host "    gh CLI not found. Install: winget install GitHub.cli" -ForegroundColor Red
        Write-Host "    Skipping GitHub release step."
    } elseif ($installerExe -eq "") {
        Write-Host "    Installer .exe not found - cannot attach to release." -ForegroundColor Red
    } else {
        # Commit version bump and any other staged changes
        Write-Host "    Committing version bump..."
        git add -A
        $commitMsg = "Release v$targetVersion"
        git commit -m $commitMsg
        if ($LASTEXITCODE -ne 0) {
            Write-Host "    Nothing new to commit (or git error) - continuing." -ForegroundColor Yellow
        }

        # Tag
        Write-Host "    Tagging v$targetVersion ..."
        git tag -a "v$targetVersion" -m "Release v$targetVersion"

        # Push branch + tag
        Write-Host "    Pushing to GitHub..."
        git push origin main
        git push origin "v$targetVersion"

        # Create the GitHub Release and upload installer
        Write-Host "    Creating GitHub Release..."
        $releaseNotes = "## Mediagator v$targetVersion`n`nSee [CHANGELOG](https://github.com/nathanokh1/Mediagator/blob/main/CHANGELOG.md) for details."
        gh release create "v$targetVersion" `
            --title "Mediagator v$targetVersion" `
            --notes $releaseNotes `
            $installerExe

        if ($LASTEXITCODE -eq 0) {
            Write-Host "    GitHub Release v$targetVersion created with installer attached!" -ForegroundColor Green
            Write-Host "    https://github.com/nathanokh1/Mediagator/releases/tag/v$targetVersion" -ForegroundColor Cyan
        } else {
            Write-Host "    gh release create failed (exit $LASTEXITCODE)" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Cyan
Write-Host "Output: dist\Mediagator\Mediagator.exe"
if ($installerExe -ne "") {
    Write-Host "Installer: $installerExe"
}
