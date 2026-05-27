# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Mediagator
# Run:  pyinstaller Mediagator.spec
#
# Requirements:
#   pip install pyinstaller
#
# Output:  dist/Mediagator/Mediagator.exe  (folder bundle)
#          dist/Mediagator_onefile.exe           (single .exe, slower start)

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[str(Path('.').resolve())],
    binaries=[],
    datas=[
        ('assets',          'assets'),          # icons, images
        ('src/config',      'src/config'),       # constants, settings defaults
    ],
    hiddenimports=[
        # PyQt6
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # Pillow
        'PIL._tkinter_finder',
        'PIL.Image',
        'PIL.ExifTags',
        # pymediainfo
        'pymediainfo',
        # piexif
        'piexif',
        # psutil
        'psutil',
        # qdarkstyle
        'qdarkstyle',
        'qdarkstyle.dark',
        'qdarkstyle.light',
        # plyer
        'plyer',
        'plyer.platforms.win.notification',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', '_tkinter',
        'matplotlib', 'numpy', 'scipy',
        'IPython', 'jupyter',
        'pytest', 'pytest_qt',
        'setuptools', 'pip',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Folder bundle (recommended — faster startup) ──────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Mediagator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
    uac_admin=False,        # elevation handled in-code by main.py (_try_elevate)
    version='version_info.txt' if Path('version_info.txt').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Mediagator',
)
