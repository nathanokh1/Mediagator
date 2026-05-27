"""
Mediagator — ProfileWidget.

Compact horizontal toolbar for saving and loading named scan profiles.
A profile stores: source folders, file-type extensions, destination path
and organisation mode — letting users one-click restore a common setup.

Author: Nathan
"""

from __future__ import annotations

import logging
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import pyqtSignal

logger = logging.getLogger(__name__)


class ProfileWidget(QWidget):
    """Single-row profile selector / save / delete panel.

    Signals:
        profile_loaded(dict): A saved profile dict was chosen; caller should
            apply source_folders, extensions, destination, org_mode.
        save_requested(str): User typed a name and clicked Save; caller
            should snapshot current state and persist under that name.
        delete_requested(str): User wants to remove the named profile.
    """

    profile_loaded   = pyqtSignal(dict)
    save_requested   = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, settings: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._build_ui()
        self.refresh(settings)

    # ── build ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        lbl = QLabel("📋  Profile:")
        lbl.setObjectName("hintLabel")
        lbl.setStyleSheet("font-size: 12px;")
        lay.addWidget(lbl)

        self._combo = QComboBox()
        self._combo.setMinimumWidth(180)
        self._combo.setStyleSheet("font-size: 12px;")
        lay.addWidget(self._combo)

        self._load_btn = QPushButton("Load")
        self._load_btn.setFixedHeight(28)
        self._load_btn.setMinimumWidth(60)
        self._load_btn.clicked.connect(self._on_load)
        lay.addWidget(self._load_btn)

        save_btn = QPushButton("Save As…")
        save_btn.setFixedHeight(28)
        save_btn.setMinimumWidth(80)
        save_btn.clicked.connect(self._on_save)
        lay.addWidget(save_btn)

        self._del_btn = QPushButton("Delete")
        self._del_btn.setFixedHeight(28)
        self._del_btn.setMinimumWidth(60)
        self._del_btn.clicked.connect(self._on_delete)
        lay.addWidget(self._del_btn)

        lay.addStretch()

    # ── public ─────────────────────────────────────────────────────────────

    def refresh(self, settings: dict) -> None:
        """Rebuild the combo from current settings (call after any profile change)."""
        self._settings = settings
        self._combo.blockSignals(True)
        current = self._combo.currentText()
        self._combo.clear()
        profiles = settings.get("profiles", {})
        for name in sorted(profiles.keys()):
            self._combo.addItem(name)
        # Try to restore previous selection
        idx = self._combo.findText(current)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)
        has_profiles = bool(profiles)
        self._load_btn.setEnabled(has_profiles)
        self._del_btn.setEnabled(has_profiles)
        self._combo.setEnabled(has_profiles)
        self._combo.blockSignals(False)

    # ── slots ──────────────────────────────────────────────────────────────

    def _on_load(self) -> None:
        name = self._combo.currentText()
        if not name:
            return
        profile = self._settings.get("profiles", {}).get(name)
        if profile:
            self.profile_loaded.emit(profile)
            logger.info("Profile loaded: %s", name)

    def _on_save(self) -> None:
        name, ok = QInputDialog.getText(
            self, "Save Profile", "Profile name:",
            text=self._combo.currentText() or "",
        )
        if not ok or not name.strip():
            return
        self.save_requested.emit(name.strip())

    def _on_delete(self) -> None:
        name = self._combo.currentText()
        if not name:
            return
        reply = QMessageBox.question(
            self, "Delete Profile",
            f'Delete profile "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(name)
