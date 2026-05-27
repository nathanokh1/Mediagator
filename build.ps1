# Mediagator — Windows build script
# Run from repo root in an elevated PowerShell session:
#   .\build.ps1
#
# Outputs:
#   dist\Mediagator\      — folder bundle (use with Inno Setup)
#   dist\Mediagator.exe   — single-file executable (optional)

param(
    [switch]$Clean    = $false,   # remove dist/ and build/ before building
    [switch]$Onefile  = $false,   # also produce a single-file .exe
    [switch]$Installer = $false   # run Inno Setup after building (requires ISCC on PATH)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=== Mediagator Build ===" -ForegroundColor Cyan
Write-Host "Working directory: $(Get-Location)"

# ── 1. Clean ────────────────────────────────────────────────────────────────
if ($Clean) {
    Write-Host "`n[1/4] Cleaning previous build artefacts..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist, build, __pycache__
    Write-Host "     Cleaned."
}

# ── 2. Install / upgrade dependencies ──────────────────────────────────────
Write-Host "`n[2/4] Installing requirements..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
Write-Host "     Done."

# ── 3. Generate version resource (optional, skip if pywin32 not available) ─
Write-Host "`n[3/4] Generating version info..." -ForegroundColor Yellow
$VersionContent = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1,0,0,0),
    prodvers=(1,0,0,0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Nathan'),
         StringStruct(u'FileDescription', u'Mediagator — Media Transfer & Organisation Tool'),
         StringStruct(u'FileVersion', u'1.0.0'),
         StringStruct(u'InternalName', u'Mediagator'),
         StringStruct(u'LegalCopyright', u'Copyright (C) 2026 Nathan. MIT License.'),
         StringStruct(u'OriginalFilename', u'Mediagator.exe'),
         StringStruct(u'ProductName', u'Mediagator'),
         StringStruct(u'ProductVersion', u'1.0.0')])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"@
$VersionContent | Set-Content -Path "version_info.txt" -Encoding UTF8
Write-Host "     version_info.txt written."

# ── 4. Run PyInstaller ──────────────────────────────────────────────────────
Write-Host "`n[4/4] Running PyInstaller (folder bundle)..." -ForegroundColor Yellow
pyinstaller Mediagator.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "     Folder bundle: dist\Mediagator\" -ForegroundColor Green

# ── Optional: single-file .exe ──────────────────────────────────────────────
if ($Onefile) {
    Write-Host "`n[5] Building single-file .exe..." -ForegroundColor Yellow
    pyinstaller src/main.py `
        --name Mediagator_portable `
        --onefile `
        --noconsole `
        --icon assets/icon.ico `
        --uac-admin `
        --add-data "assets;assets" `
        --noconfirm
    Write-Host "     Single-file: dist\Mediagator_portable.exe" -ForegroundColor Green
}

# ── Optional: Inno Setup installer ─────────────────────────────────────────
if ($Installer) {
    Write-Host "`n[6] Building Inno Setup installer..." -ForegroundColor Yellow
    $iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if (-not $iscc) {
        Write-Host "     ISCC.exe not found — skipping installer." -ForegroundColor Yellow
        Write-Host "     Install Inno Setup from https://jrsoftware.org/isinfo.php"
    } else {
        ISCC.exe installer\Mediagator.iss
        Write-Host "     Installer: dist\Mediagator_Setup.exe" -ForegroundColor Green
    }
}

Write-Host "`n=== Build complete ===" -ForegroundColor Cyan
Write-Host "Output: dist\Mediagator\Mediagator.exe"
