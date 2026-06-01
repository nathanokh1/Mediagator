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
        # src — all submodules listed explicitly so PyInstaller never misses one
        # when its static analyser fails to trace a dynamic or late import.
        'src.app',
        'src.config.constants',
        'src.config.settings',
        'src.core.analyzer',
        'src.core.date_resolver',
        'src.core.duplicate_detector',
        'src.core.hardware_profile',
        'src.core.phase_manager',
        'src.core.scanner',
        'src.core.smart_analyzer',
        'src.core.transfer_engine',
        'src.gui.main_window',
        'src.gui.update_dialog',
        'src.gui.wizard_state',
        'src.gui.steps.step_00_welcome',
        'src.gui.steps.step_01_drive_selection',
        'src.gui.steps.step_02_initial_scan',
        'src.gui.steps.step_03_destination',
        'src.gui.steps.step_04_folder_review',
        'src.gui.steps.step_05_transfer_settings',
        'src.gui.steps.step_06_pre_transfer',
        'src.gui.steps.step_07_progress',
        'src.gui.steps.step_08_report',
        'src.gui.widgets.drive_card_widget',
        'src.gui.widgets.drive_tree_widget',
        'src.gui.widgets.error_panel_widget',
        'src.gui.widgets.exclusion_list_widget',
        'src.gui.widgets.file_type_filter_widget',
        'src.gui.widgets.folder_tree_widget',
        'src.gui.widgets.profile_widget',
        'src.gui.widgets.progress_widget',
        'src.gui.widgets.scan_dashboard_widget',
        'src.models.folder_node',
        'src.models.scan_result',
        'src.models.transfer_phase',
        'src.models.transfer_plan',
        'src.utils.date_utils',
        'src.utils.exif_reader',
        'src.utils.file_utils',
        'src.utils.logger',
        'src.utils.notification',
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
