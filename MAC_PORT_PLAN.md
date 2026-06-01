# Mediagator — macOS Port Plan

**Status:** Planning complete — implementation ready to begin  
**Last updated:** May 2026  
**Author:** Nathan  

This document is the single source of truth for porting Mediagator from Windows to macOS. Read this before writing any Mac-related code.

---

## Quick Reference: What Already Works

These require **zero changes** — they are already cross-platform:

- PyQt6 — widgets, signals, threads, dark theme
- Pillow / piexif — EXIF reading
- pymediainfo — video metadata (needs MediaInfo binary via Homebrew on Mac)
- psutil — RAM, disk usage, disk partition enumeration
- qdarkstyle — dark theme
- plyer — toast notifications (uses macOS Notification Center automatically)
- Transfer engine — copy / verify / delete logic is pure Python I/O
- EXIF date resolution, majority-year logic
- Duplicate detection
- HTML report generation
- SMTP email notifications
- All QThread workers and signal/slot architecture
- Phase manager, analyzer, folder node models

---

## Repository & Project Structure

**One repo, one Cursor project.** Do not create a separate repo or Cursor project for macOS. All Mac work happens in this repository on a dedicated branch.

### Branch strategy

```
main                    ← stable releases (both platforms)
feature/mac-port        ← all Mac port work goes here
```

Create the feature branch before starting any code:

```bash
git checkout -b feature/mac-port
git push -u origin feature/mac-port
```

### Final folder layout (target state after port)

```
MediaMitigator/
│
├── src/
│   ├── platform/                        ← NEW: all OS-specific logic
│   │   ├── __init__.py                  ← auto-routes based on sys.platform
│   │   ├── base.py                      ← abstract interface / Linux fallback
│   │   ├── windows.py                   ← PowerShell, UAC, Defender, drive letters
│   │   └── macos.py                     ← diskutil, TCC, /Volumes, open command
│   │
│   ├── core/                            ← no changes needed
│   ├── gui/                             ← mostly unchanged; drive UI adapts
│   ├── config/
│   │   └── constants.py                 ← APPDATA_DIR becomes platform-aware
│   ├── models/                          ← no changes needed
│   └── utils/                           ← no changes needed
│
├── build/
│   ├── windows/
│   │   ├── build.ps1                    ← move existing build.ps1 here
│   │   ├── Mediagator.spec              ← move existing spec here
│   │   └── installer/
│   │       └── Mediagator.iss           ← move existing .iss here
│   └── macos/
│       ├── build_mac.sh                 ← NEW
│       ├── Mediagator_mac.spec          ← NEW PyInstaller Mac spec
│       └── dmg_settings.py             ← NEW dmgbuild config
│
├── assets/
│   ├── icon.ico                         ← existing Windows icon
│   └── icon.icns                        ← NEW Mac icon (convert from .ico)
│
├── .github/
│   └── workflows/
│       ├── build-windows.yml            ← NEW CI for Windows builds
│       └── build-macos.yml             ← NEW CI for Mac .app/.dmg builds
│
├── requirements.txt                     ← shared (both platforms)
├── requirements-macos.txt              ← Mac-only if needed (e.g. dmgbuild)
├── MAC_PORT_PLAN.md                     ← this file
└── CHANGELOG.md
```

---

## Implementation Order

Work through these in sequence. Each step is self-contained and testable.

### Step 0 — Branch and scaffold

- [ ] `git checkout -b feature/mac-port`
- [ ] Create `src/platform/` folder with empty `__init__.py`, `base.py`, `windows.py`, `macos.py`
- [ ] Move `build.ps1`, `Mediagator.spec`, `installer/` into `build/windows/`
- [ ] Update any path references in `build.ps1` to reflect new location

### Step 1 — Platform abstraction module (`src/platform/`)

This is the foundation everything else depends on. Build it first.

**`base.py`** — define the interface (Linux fallback / sensible defaults):

```python
import sys
from pathlib import Path

def get_settings_dir(app_name: str) -> Path:
    return Path.home() / f".{app_name.lower()}"

def get_drive_type(path: Path) -> str:
    return "Unknown"

def is_elevated() -> bool:
    return False

def add_av_exclusions(paths: list[Path]) -> bool:
    return False  # no-op

def remove_av_exclusions(paths: list[Path]) -> None:
    pass  # no-op

def get_system_folder_hints() -> set[str]:
    return set()

def get_system_root_hints() -> set[str]:
    return set()

def enumerate_volumes() -> list[dict]:
    """Return list of dicts with keys: name, mount_point, total_bytes, free_bytes"""
    import psutil
    volumes = []
    for p in psutil.disk_partitions(all=False):
        if not p.mountpoint:
            continue
        try:
            usage = psutil.disk_usage(p.mountpoint)
        except PermissionError:
            continue
        volumes.append({
            "name": Path(p.mountpoint).name or p.mountpoint,
            "mount_point": p.mountpoint,
            "total_bytes": usage.total,
            "free_bytes": usage.free,
        })
    return volumes
```

**`windows.py`** — move all existing Windows-specific logic here (from `hardware_profile.py`, `main.py`, `scanner.py`, `constants.py`):

- `get_settings_dir()` → `Path(os.environ["APPDATA"]) / app_name`
- `get_drive_type()` → PowerShell `Get-PhysicalDisk` (existing code from `hardware_profile.py`)
- `is_elevated()` → `ctypes.windll.shell32.IsUserAnAdmin()` (existing)
- `add_av_exclusions()` / `remove_av_exclusions()` → `Add-MpPreference` (existing)
- `get_system_folder_hints()` → returns `SYSTEM_FOLDER_HINTS` from `constants.py`
- `get_system_root_hints()` → returns `C_DRIVE_SYSTEM_ROOTS`
- `enumerate_volumes()` → drive-letter-based using existing `enumerate_drives()` logic

**`macos.py`** — new Mac implementations:

- `get_settings_dir()` → `Path.home() / "Library" / "Application Support" / app_name`
- `get_drive_type()` → `diskutil info <mount_point>` and parse `Solid State: Yes/No`
- `is_elevated()` → `return False` (macOS doesn't use admin elevation for this)
- `add_av_exclusions()` → `return False` (no-op; macOS has no AV exclusion API)
- `remove_av_exclusions()` → no-op
- `get_system_folder_hints()` → Mac-specific set (see constants section below)
- `get_system_root_hints()` → Mac volume root system folders
- `enumerate_volumes()` → `/Volumes/` based, filter out system volumes

**`__init__.py`** — runtime routing:

```python
import sys

if sys.platform == "win32":
    from src.platform.windows import *
elif sys.platform == "darwin":
    from src.platform.macos import *
else:
    from src.platform.base import *
```

### Step 2 — Update `constants.py`

Replace the hardcoded `APPDATA_DIR` with a platform call:

```python
# OLD (Windows-only):
APPDATA_DIR: Path = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME

# NEW (cross-platform):
from src.platform import get_settings_dir
APPDATA_DIR: Path = get_settings_dir(APP_NAME)
```

Add Mac-specific exclusion sets (keep Windows ones too — the platform module picks the right ones):

```python
# Mac system folders to exclude from scanning
MAC_SYSTEM_FOLDER_HINTS: set[str] = {
    "library", "system", "applications", "private", "usr", "bin", "sbin",
    ".ds_store", ".spotlight-v100", ".trashes", ".fseventsd",
    ".temporaryitems", "cores", "developer", "opt",
}

MAC_VOLUME_SYSTEM_ROOTS: set[str] = {
    "system", "library", "usr", "bin", "sbin", "private",
    "applications", "cores", "developer", "opt",
}

# Default exclusions also need Mac entries in the shared set:
DEFAULT_EXCLUSIONS: set[str] = {
    # ... existing Windows entries ...
    # Mac additions:
    ".trashes", ".spotlight-v100", ".fseventsd", ".temporaryitems",
}
```

Remove `C_DRIVE_SYSTEM_ROOTS` from `constants.py` — it moves into `src/platform/windows.py`.

### Step 3 — Update `hardware_profile.py`

Replace all platform-specific calls with platform module imports:

```python
# OLD:
from src.core.hardware_profile import _get_drive_type, _is_admin, add_defender_exclusions

# NEW:
from src.platform import get_drive_type, is_elevated, add_av_exclusions, remove_av_exclusions
```

The `detect_hardware()` function itself stays in `hardware_profile.py` — it just calls the platform module instead of doing PowerShell directly. The `wmic` RAM fallback can be dropped entirely since `psutil` already works on all platforms.

### Step 4 — Update `scanner.py`

**Drive enumeration** (`enumerate_drives()`):  
Replace with a call to `src.platform.enumerate_volumes()`. The returned dict maps cleanly to `DriveInfo`. On Mac, `DriveInfo.letter` gets populated with the volume name (e.g., `"Seagate"`) instead of a drive letter.

**`classify_folder()` — drive root detection:**

```python
# OLD (Windows-specific):
is_drive_root_child = (folder.parent == Path(folder.drive + "\\"))
if is_drive_root_child and folder.drive.upper().startswith("C"):
    if name in C_DRIVE_SYSTEM_ROOTS:
        return "system"

# NEW (cross-platform):
from src.platform import get_system_root_hints
is_volume_root_child = (folder.parent == Path(folder.anchor) or
                        str(folder.parent) == "/Volumes")
if is_volume_root_child:
    if name in get_system_root_hints():
        return "system"
```

**`drives_scanned` field in `ScanResult`:**

```python
# OLD (returns empty strings on Mac):
drives_scanned=sorted({str(f.drive) for f in self._scan_folders})

# NEW:
drives_scanned=sorted({str(f.anchor) for f in self._scan_folders})
```

### Step 5 — Update `main.py`

The `_try_elevate()` function already has a guard (`ctypes.windll` is caught by the `except Exception`), but clean it up:

```python
def _try_elevate() -> None:
    if sys.platform != "win32":
        return
    # ... existing UAC code ...
```

### Step 6 — Update `update_dialog.py`

The download and launch flow needs Mac asset support:

```python
# Determine which asset to download based on platform
if sys.platform == "win32":
    filename = f"Mediagator_Setup_{self._version}.exe"
elif sys.platform == "darwin":
    filename = f"Mediagator_{self._version}.dmg"

# Launch the downloaded file:
if sys.platform == "win32":
    ctypes.windll.shell32.ShellExecuteW(None, "runas", path, None, None, 1)
elif sys.platform == "darwin":
    subprocess.Popen(["open", path])  # macOS 'open' handles .dmg automatically
```

The GitHub API response needs to return a `.dmg` asset. Publish both assets in each GitHub Release.

### Step 7 — Drive selection UI adaptations

**`step_01_drive_selection.py`** and **`drive_card_widget.py`**:

- Labels showing `"Drive E:"` should show volume name on Mac (e.g., `"Seagate"`)
- `DriveInfo.letter` is used extensively in these widgets — either add a `DriveInfo.display_name` property that returns the letter on Windows and the volume name on Mac, or rename the field
- Drive icons: on Mac, mounted volumes look like disks, not drive letters — consider using the same icons but updating the label format

**`drive_tree_widget.py`**:

- Root nodes built from drive letters need to use mount points on Mac
- `Path("E:\\")` → `Path("/Volumes/Seagate")`

### Step 8 — macOS build setup

**Convert icon** (`assets/icon.icns`):

```bash
# On a Mac, from the assets/ folder:
mkdir icon.iconset
sips -z 16 16     icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32     icon.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out icon.iconset/icon_32x32.png
sips -z 64 64     icon.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256   icon.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out icon.iconset/icon_256x256.png
sips -z 512 512   icon.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png
iconutil -c icns icon.iconset
```

**`build/macos/Mediagator_mac.spec`** (PyInstaller):

```python
# Key differences from Windows spec:
# - icon uses .icns not .ico
# - no version_info.txt
# - target_arch='universal2' for Intel + Apple Silicon
a = Analysis(['../../src/main.py'], ...)
exe = EXE(a.scripts, ...)
app = BUNDLE(exe,
    name='Mediagator.app',
    icon='../../assets/icon.icns',
    bundle_identifier='com.nathanokh.mediagator',
    info_plist={
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # allow dark mode
    }
)
```

**`build/macos/build_mac.sh`**:

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/../.."

pip install -r requirements.txt
pip install -r requirements-macos.txt

pyinstaller build/macos/Mediagator_mac.spec --clean

# Create DMG
python -m dmgbuild -s build/macos/dmg_settings.py "Mediagator" dist/Mediagator.dmg

echo "Build complete: dist/Mediagator.dmg"
```

**`requirements-macos.txt`**:

```
dmgbuild==1.6.1
```

### Step 9 — Notarization (requires Apple Developer account)

```bash
# Sign the .app
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Nathan <TEAM_ID>" \
  --entitlements build/macos/entitlements.plist \
  dist/Mediagator.app

# Sign the .dmg
codesign --sign "Developer ID Application: Nathan <TEAM_ID>" dist/Mediagator.dmg

# Submit for notarization
xcrun notarytool submit dist/Mediagator.dmg \
  --apple-id your@email.com \
  --team-id TEAM_ID \
  --password APP_SPECIFIC_PASSWORD \
  --wait

# Staple the ticket
xcrun stapler staple dist/Mediagator.dmg
```

**`build/macos/entitlements.plist`** — required for disk access:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" ...>
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.files.all</key>
    <true/>
</dict>
</plist>
```

### Step 10 — GitHub Actions CI

**`.github/workflows/build-macos.yml`**:

```yaml
name: Build macOS
on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt -r requirements-macos.txt
      - run: bash build/macos/build_mac.sh
      - uses: actions/upload-artifact@v4
        with:
          name: Mediagator-macOS
          path: dist/Mediagator.dmg
```

---

## macOS-Specific Default Exclusions

Add these to `DEFAULT_EXCLUSIONS` in `constants.py` (they are safe to include cross-platform since Windows will never see folders named `.trashes`):

```python
".trashes",
".spotlight-v100",
".fseventsd",
".temporaryitems",
".ds_store",
```

Add to Mac-only `SYSTEM_FOLDER_HINTS` (via `src/platform/macos.py`):

```python
{
    "library", "system", "applications", "private", "usr", "bin",
    "sbin", "cores", "developer", "opt", ".android", ".gradle",
}
```

---

## Mac Hardware Notes

- **Apple Silicon (M-series):** PyInstaller supports `target_arch='universal2'` to build a single binary that runs natively on both Intel and Apple Silicon Macs. Use this.
- **Full Disk Access:** The app must be granted Full Disk Access in System Settings → Privacy & Security to scan external drives and the user's home folder. This is handled by TCC — no code change needed, but the app should detect when it lacks access and show an inline warning banner pointing the user to System Settings.
- **Volumes:** External drives mount at `/Volumes/DriveName`. SD cards, USB drives, and network shares also appear here.
- **SMB/network shares:** `psutil.disk_partitions()` returns these too. Filter by `fstype` if you want to exclude network drives.

---

## Testing Checklist (do on a Mac before releasing)

- [ ] App launches without errors on macOS 13 Ventura or later
- [ ] Dark mode works correctly
- [ ] External drives appear in Drive Selection step with volume names
- [ ] Scanning a drive finds media files
- [ ] EXIF dates resolve correctly
- [ ] Transfer (copy/verify/delete) works on macOS APFS and ExFAT volumes
- [ ] Settings save to `~/Library/Application Support/Mediagator/`
- [ ] Toast notifications appear in macOS Notification Center
- [ ] App launches from `.app` bundle without terminal
- [ ] Gatekeeper does not block the app (notarization required)
- [ ] Full Disk Access prompt appears or is gracefully detected as missing
- [ ] Update dialog downloads `.dmg` asset correctly

---

## Developer Setup on Mac

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install MediaInfo (required by pymediainfo)
brew install mediainfo

# Install Python 3.12
brew install python@3.12

# Clone the repo and switch to the mac branch
git clone https://github.com/nathanokh1/Mediagator.git
cd Mediagator
git checkout feature/mac-port

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-macos.txt

# Run the app
python src/main.py
```

---

## Key Decisions Summary

| Decision | Choice | Reason |
|---|---|---|
| Repo structure | Single repo | Shared bugs, shared features, no sync overhead |
| Branch strategy | `feature/mac-port` off `main` | Standard git flow |
| Platform abstraction | `src/platform/` module | Clean separation, no `if sys.platform` scattered everywhere |
| Mac settings path | `~/Library/Application Support/Mediagator/` | macOS convention |
| Drive display | Volume name (e.g. "Seagate") | Drive letters don't exist on Mac |
| SSD detection | `diskutil info` shell command | macOS equivalent of WMI |
| Admin/elevation | Not needed on Mac | TCC handles disk permissions |
| AV exclusions | No-op on Mac | No equivalent API |
| Distribution | Notarized `.dmg` | Industry standard for indie Mac apps |
| Packaging | PyInstaller `universal2` | Covers Intel and Apple Silicon in one binary |
| Icon | `.icns` (convert existing `.ico`) | Required by macOS |
| Auto-update | Download `.dmg` + `open` command | macOS equivalent of `.exe` + ShellExecute |
