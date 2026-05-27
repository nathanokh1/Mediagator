"""
Mediagator — Step 1: Drive Selection.

Full layout (scrollable):
  • Expandable drive → folder tree with smart pre-check
  • File Type Filter — grouped checkboxes with presets (Photos/Videos/RAW/All)
  • Folder Exclusion List — names to always skip during scanning

Settings (selected folders, extensions, exclusions) persist to
%APPDATA%/Mediagator/settings.json.

Author: Nathan
"""

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QScrollArea,
)
from PyQt6.QtCore import pyqtSignal, Qt

from src.gui.wizard_state import WizardState
from src.gui.widgets.drive_tree_widget import DriveTreeWidget
from src.gui.widgets.exclusion_list_widget import ExclusionListWidget
from src.gui.widgets.file_type_filter_widget import FileTypeFilterWidget
from src.gui.widgets.profile_widget import ProfileWidget
from src.core.scanner import enumerate_drives
from src.config.settings import save_settings
from src.config.constants import DEFAULT_SELECTED_EXTENSIONS

logger = logging.getLogger(__name__)


class DriveSelectionStep(QWidget):
    """Step 1 — pick folders, file types and exclusions.

    Signals:
        next_requested: User clicked Next.
    """

    next_requested = pyqtSignal()

    def __init__(self, state: WizardState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._build_ui()
        self._load_drives()
        self._restore_saved_extensions()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Scrollable content ────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(14)

        # Title
        title = QLabel("Select Folders & File Types to Scan")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # ── Saved Profiles ─────────────────────────────────────────────
        self._profile_widget = ProfileWidget(self._state.settings)
        self._profile_widget.profile_loaded.connect(self._on_profile_load)
        self._profile_widget.save_requested.connect(self._on_profile_save)
        self._profile_widget.delete_requested.connect(self._on_profile_delete)
        layout.addWidget(self._profile_widget)

        subtitle = QLabel(
            "Expand each drive to choose folders, then click the ones you want to scan.  "
            "Use <b>Smart Select</b> to auto-check likely media folders.  "
            "<span style='color:#4caf50'>📷 Media</span> — personal photos/videos.  "
            "<span style='color:#616161'>⚙ System</span> — OS/app folders, skip these."
        )
        subtitle.setWordWrap(True)
        subtitle.setTextFormat(Qt.TextFormat.RichText)
        subtitle.setObjectName("hintLabel")
        subtitle.setStyleSheet("font-size: 12px;")
        layout.addWidget(subtitle)

        # ── Drive / Folder tree ────────────────────────────────────────
        drives_group = QGroupBox("Drives & Folders")
        drives_layout = QVBoxLayout(drives_group)

        # Toolbar
        toolbar = QHBoxLayout()
        for label, slot in (
            ("✓ Smart Select", "_on_smart_select"),
            ("Select All",     "_on_select_all"),
            ("Deselect All",   "_on_deselect_all"),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(getattr(self, slot))
            toolbar.addWidget(btn)
        toolbar.addStretch()
        self._selection_label = QLabel("0 folders selected")
        self._selection_label.setObjectName("hintLabel")
        self._selection_label.setStyleSheet("font-size: 11px;")
        toolbar.addWidget(self._selection_label)
        drives_layout.addLayout(toolbar)

        self._tree = DriveTreeWidget()
        self._tree.setMinimumHeight(260)
        self._tree.selection_changed.connect(self._on_folder_selection_changed)
        drives_layout.addWidget(self._tree)
        layout.addWidget(drives_group)

        # Legend
        legend = QHBoxLayout()
        legend_items = [
            ("#4caf50", "📷 Media — likely personal photos/videos"),
            (None,      "📁 Folder — unknown, will be scanned"),
            ("#888888", "⚙ System — OS/app folder, skipped by default"),
        ]
        for colour, text in legend_items:
            lbl = QLabel()
            if colour:
                lbl.setText(f"<span style='color:{colour}'>{text}</span>")
                lbl.setTextFormat(Qt.TextFormat.RichText)
            else:
                lbl.setText(text)
                lbl.setObjectName("hintLabel")
            legend.addWidget(lbl)
            legend.addSpacing(16)
        legend.addStretch()
        layout.addLayout(legend)

        # ── File type filter ───────────────────────────────────────────
        self._file_filter = FileTypeFilterWidget()
        self._file_filter.extensions_changed.connect(self._on_extensions_changed)
        layout.addWidget(self._file_filter)

        # ── Exclusion list ─────────────────────────────────────────────
        exclusions = self._state.settings.get("exclusion_list", [])
        self._exclusion_widget = ExclusionListWidget(exclusions=exclusions)
        self._exclusion_widget.exclusions_changed.connect(self._on_exclusions_changed)
        layout.addWidget(self._exclusion_widget)

        layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        # ── Fixed navigation bar ───────────────────────────────────────
        nav_bar = QWidget()
        nav_bar.setObjectName("navBar")
        nav_bar.setFixedHeight(56)
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(24, 0, 24, 0)

        self._status_label = QLabel("")
        self._status_label.setObjectName("hintLabel")
        self._status_label.setStyleSheet("font-size: 11px;")
        nav_layout.addWidget(self._status_label)
        nav_layout.addStretch()

        self._next_btn = QPushButton("Next →")
        self._next_btn.setObjectName("primaryBtn")
        self._next_btn.setMinimumWidth(130)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self._on_next)
        nav_layout.addWidget(self._next_btn)
        root.addWidget(nav_bar)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_drives(self) -> None:
        drives = enumerate_drives()
        self._state.available_drives = drives
        self._tree.populate(drives)

    def _restore_saved_extensions(self) -> None:
        """Restore previously saved extension selection from settings."""
        saved = self._state.settings.get("selected_extensions", [])
        if saved:
            self._file_filter.set_selected_extensions(set(saved))
            self._state.selected_extensions = set(saved)
        else:
            self._state.selected_extensions = set(DEFAULT_SELECTED_EXTENSIONS)

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_smart_select(self) -> None:
        self._tree.select_all_media()

    def _on_select_all(self) -> None:
        self._tree.check_all()

    def _on_deselect_all(self) -> None:
        self._tree.uncheck_all()

    def _on_folder_selection_changed(self, folders: list[Path]) -> None:
        self._state.selected_scan_folders = folders
        self._update_status()
        self._persist_settings()

    def _on_extensions_changed(self, extensions: set[str]) -> None:
        self._state.selected_extensions = extensions
        self._update_status()
        self._persist_settings()

    def _on_exclusions_changed(self, exclusions: list[str]) -> None:
        self._state.settings["exclusion_list"] = exclusions
        save_settings(self._state.settings)

    def _update_status(self) -> None:
        folders = len(self._state.selected_scan_folders)
        exts = len(self._state.selected_extensions)
        self._status_label.setText(
            f"{folders} folder{'s' if folders != 1 else ''} selected  •  "
            f"{exts} file type{'s' if exts != 1 else ''} included"
        )
        self._next_btn.setEnabled(folders > 0 and exts > 0)
        if folders == 0:
            self._next_btn.setText("Select a folder")
        elif exts == 0:
            self._next_btn.setText("Select a file type")
        else:
            self._next_btn.setText("Next →")

    def _persist_settings(self) -> None:
        self._state.settings["selected_scan_folders"] = [
            str(f) for f in self._state.selected_scan_folders
        ]
        self._state.settings["selected_extensions"] = sorted(
            self._state.selected_extensions
        )
        save_settings(self._state.settings)

    # ------------------------------------------------------------------
    # Profile handlers
    # ------------------------------------------------------------------

    def _on_profile_save(self, name: str) -> None:
        """Snapshot current state under *name* and persist."""
        profile = {
            "source_folders": [str(f) for f in self._state.selected_scan_folders],
            "extensions":     sorted(self._state.selected_extensions),
            "destination":    str(self._state.destination_root) if self._state.destination_root else None,
            "org_mode":       self._state.org_mode or None,
        }
        profiles = self._state.settings.setdefault("profiles", {})
        profiles[name] = profile
        save_settings(self._state.settings)
        self._profile_widget.refresh(self._state.settings)
        logger.info("Profile saved: %s", name)

    def _on_profile_load(self, profile: dict) -> None:
        """Restore state from a saved *profile* dict."""
        # Extensions
        exts = set(profile.get("extensions", []))
        if exts:
            self._state.selected_extensions = exts
            self._file_filter.set_selected_extensions(exts)

        # Source folders — restore state and visually check matching tree items
        folders = [Path(f) for f in profile.get("source_folders", []) if Path(f).exists()]
        self._state.selected_scan_folders = folders
        self._tree.check_paths(folders)

        # Destination + org mode (silently restore; user sees it when they reach step 3)
        dest = profile.get("destination")
        if dest and Path(dest).exists():
            self._state.destination_root = Path(dest)
        org = profile.get("org_mode")
        if org:
            self._state.org_mode = org

        self._update_status()
        self._persist_settings()
        logger.info("Profile loaded: %d folders, %d extensions", len(folders), len(exts))

    def _on_profile_delete(self, name: str) -> None:
        profiles = self._state.settings.get("profiles", {})
        profiles.pop(name, None)
        save_settings(self._state.settings)
        self._profile_widget.refresh(self._state.settings)
        logger.info("Profile deleted: %s", name)

    def _on_next(self) -> None:
        if self._state.selected_scan_folders and self._state.selected_extensions:
            self.next_requested.emit()

    def refresh(self) -> None:
        """Called when the step becomes visible."""
        self._profile_widget.refresh(self._state.settings)
