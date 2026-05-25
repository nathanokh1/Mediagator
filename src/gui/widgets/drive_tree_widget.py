"""
MediaMitigator — DriveTreeWidget.

Expandable tree showing drives → folders → subfolders (unlimited depth)
with smart pre-check classification and async folder size loading.

Classification:
  📷 Media  (green, auto-checked)   — Photos, DCIM, Videos, etc.
  📁 Folder (white, auto-checked)   — unknown user folder
  ⚙ System  (grey, auto-unchecked)  — Windows, Program Files, etc.

Lazy loading: folders show a "⟳ Loading…" placeholder when first
expanded; actual children are fetched in a QThread and inserted live.

Author: Nathan
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QAbstractItemView,
    QMenu, QHeaderView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtWidgets import QTreeWidgetItem as _QTWItem  # alias for slot signatures
from PyQt6.QtGui import QColor, QFont, QBrush, QAction

from src.models.scan_result import DriveInfo
from src.core.scanner import get_top_level_folders, get_subfolders, classify_folder
from src.utils.file_utils import human_readable_size

logger = logging.getLogger(__name__)

_COL_NAME = 0
_COL_TYPE = 1
_COL_SIZE = 2

_COLOUR_MEDIA   = QColor("#4caf50")
_COLOUR_UNKNOWN = QColor("#e0e0e0")
_COLOUR_SYSTEM  = QColor("#616161")

_BADGE = {"media": "📷 Media", "unknown": "📁 Folder", "system": "⚙ System"}
_COLOUR = {"media": _COLOUR_MEDIA, "unknown": _COLOUR_UNKNOWN, "system": _COLOUR_SYSTEM}

_PLACEHOLDER_TEXT = "⟳  Loading…"
_ROLE_KIND  = Qt.ItemDataRole.UserRole          # "drive:<letter>" or classification str
_ROLE_PATH  = Qt.ItemDataRole.UserRole + 1      # Path object


# ---------------------------------------------------------------------------
# Background worker: list subfolders + quick size estimate
# ---------------------------------------------------------------------------

class _FolderLoader(QThread):
    """Load immediate children of a folder in the background.

    Signals:
        loaded(Path, list): (parent_path, [(child_path, classification), ...])
    """

    loaded = pyqtSignal(object, list)

    def __init__(self, folder: Path) -> None:
        super().__init__()
        self._folder = folder

    def run(self) -> None:
        children = get_subfolders(self._folder)
        self.loaded.emit(self._folder, children)


class _SizeLoader(QThread):
    """Quickly estimate the size of direct media files inside a folder.

    Only counts files one level deep (non-recursive) for speed.

    Signals:
        size_ready(Path, int): (folder_path, size_in_bytes)
    """

    size_ready = pyqtSignal(object, int)

    def __init__(self, folder: Path) -> None:
        super().__init__()
        self._folder = folder

    def run(self) -> None:
        from src.config.constants import MEDIA_EXTENSIONS
        total = 0
        try:
            with os.scandir(str(self._folder)) as it:
                for entry in it:
                    if entry.is_file(follow_symlinks=False):
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in MEDIA_EXTENSIONS:
                            try:
                                total += entry.stat().st_size
                            except OSError:
                                pass
        except (PermissionError, FileNotFoundError):
            pass
        self.size_ready.emit(self._folder, total)


# ---------------------------------------------------------------------------
# Main widget
# ---------------------------------------------------------------------------

class DriveTreeWidget(QTreeWidget):
    """Infinite-depth expandable drive-folder tree with smart pre-check.

    Signals:
        selection_changed(list[Path]): Checked folder paths (leaf items).
    """

    selection_changed = pyqtSignal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._drive_items: dict[str, QTreeWidgetItem] = {}
        self._folder_items: dict[Path, QTreeWidgetItem] = {}
        self._loading = False
        self._pending_loaders: list[QThread] = []

        self.setHeaderLabels(["Name / Path", "Type", "Direct Media Size"])
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.header().resizeSection(1, 100)
        self.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.header().resizeSection(2, 140)

        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemChanged.connect(self._on_item_changed)
        self.setAlternatingRowColors(True)
        self.setAnimated(True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(self, drives: list[DriveInfo]) -> None:
        """Build the top two levels (drives + their immediate child folders).

        Args:
            drives: Drives from :func:`enumerate_drives`.
        """
        self._loading = True
        self.clear()
        self._drive_items.clear()
        self._folder_items.clear()

        for drive in drives:
            drive_item = self._make_drive_item(drive)
            self.addTopLevelItem(drive_item)
            self._drive_items[drive.letter] = drive_item

            folders = get_top_level_folders(drive.root_path)
            for folder_path, classification in folders:
                child = self._make_folder_item(folder_path, classification)
                drive_item.addChild(child)
                self._folder_items[folder_path] = child
                # Add placeholder so the expand arrow appears
                self._add_placeholder(child)
                # Kick off async size load
                self._start_size_loader(folder_path, child)

            has_media = any(c == "media" for _, c in folders)
            if has_media:
                drive_item.setExpanded(True)

        self._loading = False
        self._sync_drive_states()
        self._emit_selection()

    def get_selected_folders(self) -> list[Path]:
        """Return all checked folder paths (any depth).

        Returns:
            List of :class:`Path` objects for checked folder rows.
        """
        result: list[Path] = []
        for path, item in self._folder_items.items():
            if item.checkState(_COL_NAME) == Qt.CheckState.Checked:
                result.append(path)
        return result

    def select_all_media(self) -> None:
        """Check media/unknown, uncheck system folders."""
        self._loading = True
        for path, item in self._folder_items.items():
            kind = item.data(_COL_NAME, _ROLE_KIND) or ""
            new_state = (
                Qt.CheckState.Unchecked
                if kind == "system"
                else Qt.CheckState.Checked
            )
            item.setCheckState(_COL_NAME, new_state)
        self._loading = False
        self._sync_drive_states()
        self._emit_selection()

    def check_all(self) -> None:
        self._set_all(Qt.CheckState.Checked)

    def uncheck_all(self) -> None:
        self._set_all(Qt.CheckState.Unchecked)

    # ------------------------------------------------------------------
    # Item builders
    # ------------------------------------------------------------------

    def _make_drive_item(self, drive: DriveInfo) -> QTreeWidgetItem:
        used_pct = int(drive.usage_percent)
        free_str = human_readable_size(drive.free_bytes)
        total_str = human_readable_size(drive.total_bytes)
        label = drive.label.split("\\")[-1] or "Local Disk"
        display = f"  Drive {drive.letter}:  —  {label}"

        item = QTreeWidgetItem([display, "Drive", f"Free {free_str} / {total_str}  ({used_pct}% used)"])
        item.setCheckState(_COL_NAME, Qt.CheckState.Checked)
        item.setFlags(
            item.flags()
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsAutoTristate
        )
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        item.setFont(_COL_NAME, font)
        item.setForeground(_COL_NAME, QBrush(QColor("#ff9800")))
        item.setData(_COL_NAME, _ROLE_KIND, f"drive:{drive.letter}")
        return item

    def _make_folder_item(self, folder: Path, classification: str) -> QTreeWidgetItem:
        badge = _BADGE.get(classification, _BADGE["unknown"])
        colour = _COLOUR.get(classification, _COLOUR["unknown"])

        item = QTreeWidgetItem([f"  {folder.name}", badge, "…"])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

        default = (
            Qt.CheckState.Unchecked
            if classification == "system"
            else Qt.CheckState.Checked
        )
        item.setCheckState(_COL_NAME, default)
        item.setForeground(_COL_NAME, QBrush(colour))
        item.setForeground(_COL_TYPE, QBrush(colour))
        item.setData(_COL_NAME, _ROLE_KIND, classification)
        item.setData(_COL_NAME, _ROLE_PATH, folder)
        item.setToolTip(_COL_NAME, str(folder))
        return item

    @staticmethod
    def _add_placeholder(parent_item: QTreeWidgetItem) -> None:
        """Add a loading placeholder so the expand arrow appears."""
        ph = QTreeWidgetItem([_PLACEHOLDER_TEXT, "", ""])
        ph.setFlags(Qt.ItemFlag.ItemIsEnabled)
        ph.setForeground(_COL_NAME, QBrush(QColor("#555")))
        parent_item.addChild(ph)

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

    @pyqtSlot(_QTWItem)
    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Trigger child load when a folder row is expanded.

        Args:
            item: Expanded tree item.
        """
        # Skip drive headers
        kind = item.data(_COL_NAME, _ROLE_KIND) or ""
        if isinstance(kind, str) and kind.startswith("drive:"):
            return

        folder: Path | None = item.data(_COL_NAME, _ROLE_PATH)
        if not folder:
            return

        # Only load if the only child is the placeholder
        if item.childCount() != 1:
            return
        ph = item.child(0)
        if not ph or ph.text(_COL_NAME) != _PLACEHOLDER_TEXT:
            return

        loader = _FolderLoader(folder)
        loader.loaded.connect(self._on_children_loaded)
        self._pending_loaders.append(loader)
        loader.start()

    @pyqtSlot(object, list)
    def _on_children_loaded(self, parent_path: Path, children: list) -> None:
        """Replace the placeholder with actual child items.

        Args:
            parent_path: Path whose children were loaded.
            children: ``[(child_path, classification), ...]``
        """
        parent_item = self._folder_items.get(parent_path)
        if not parent_item:
            return

        self._loading = True
        # Remove placeholder
        parent_item.takeChildren()

        if not children:
            parent_item.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator
            )
        else:
            parent_state = parent_item.checkState(_COL_NAME)
            for child_path, classification in children:
                child_item = self._make_folder_item(child_path, classification)
                parent_item.addChild(child_item)
                self._folder_items[child_path] = child_item
                # If parent is fully checked or fully unchecked, inherit that
                # state — override the smart default so Deselect/Select All
                # is respected for newly expanded levels.
                if parent_state == Qt.CheckState.Unchecked:
                    child_item.setCheckState(_COL_NAME, Qt.CheckState.Unchecked)
                elif parent_state == Qt.CheckState.Checked:
                    # Keep the smart default (media=checked, system=unchecked)
                    pass
                # PartiallyChecked → keep smart default for the new children
                self._add_placeholder(child_item)
                self._start_size_loader(child_path, child_item)

        self._loading = False
        self._sync_drive_states()
        self._emit_selection()

    # ------------------------------------------------------------------
    # Async size loading
    # ------------------------------------------------------------------

    def _start_size_loader(self, folder: Path, item: QTreeWidgetItem) -> None:
        """Start an async size calculation for a folder item.

        Args:
            folder: Folder to measure.
            item: Tree item to update when done.
        """
        loader = _SizeLoader(folder)
        loader.size_ready.connect(self._on_size_ready)
        self._pending_loaders.append(loader)
        loader.start()

    @pyqtSlot(object, int)
    def _on_size_ready(self, folder: Path, size: int) -> None:
        """Update the size column for a folder item.

        Args:
            folder: Folder whose size was computed.
            size: Size in bytes.
        """
        item = self._folder_items.get(folder)
        if not item:
            return
        if size > 0:
            item.setText(_COL_SIZE, human_readable_size(size))
        else:
            item.setText(_COL_SIZE, "—")

    # ------------------------------------------------------------------
    # Check-state synchronisation
    # ------------------------------------------------------------------

    @pyqtSlot(_QTWItem, int)
    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._loading or column != _COL_NAME:
            return

        state = item.checkState(_COL_NAME)
        # Cascade to children for ANY item (drive header or folder row),
        # but only when the state is fully checked or fully unchecked —
        # skip PartiallyChecked which is set programmatically during sync.
        if state != Qt.CheckState.PartiallyChecked:
            self._loading = True
            self._cascade_check(item, state)
            self._loading = False

        self._sync_drive_states()
        self._emit_selection()

    def _cascade_check(self, item: QTreeWidgetItem, state: Qt.CheckState) -> None:
        """Recursively set check state on all descendants.

        Args:
            item: Parent item.
            state: Target check state.
        """
        for i in range(item.childCount()):
            child = item.child(i)
            if child and child.text(_COL_NAME) != _PLACEHOLDER_TEXT:
                child.setCheckState(_COL_NAME, state)
                self._cascade_check(child, state)

    def _sync_drive_states(self) -> None:
        """Update drive header check states from their checked children."""
        self._loading = True
        for drive_item in self._drive_items.values():
            total = drive_item.childCount()
            if total == 0:
                continue
            checked = sum(
                1 for i in range(total)
                if (ch := drive_item.child(i)) and
                ch.text(_COL_NAME) != _PLACEHOLDER_TEXT and
                ch.checkState(_COL_NAME) == Qt.CheckState.Checked
            )
            real = sum(
                1 for i in range(total)
                if (ch := drive_item.child(i)) and
                ch.text(_COL_NAME) != _PLACEHOLDER_TEXT
            )
            if real == 0:
                continue
            if checked == 0:
                drive_item.setCheckState(_COL_NAME, Qt.CheckState.Unchecked)
            elif checked == real:
                drive_item.setCheckState(_COL_NAME, Qt.CheckState.Checked)
            else:
                drive_item.setCheckState(_COL_NAME, Qt.CheckState.PartiallyChecked)
        self._loading = False

    def _set_all(self, state: Qt.CheckState) -> None:
        """Set every folder item in the tree to *state*.

        Walks the full visible tree (not just _folder_items) so that all
        loaded levels are covered, then records the desired state on each
        drive item so newly lazy-loaded children inherit it on expansion.
        """
        self._loading = True
        for drive_item in self._drive_items.values():
            drive_item.setCheckState(_COL_NAME, state)
            self._cascade_check(drive_item, state)
        self._loading = False
        self._sync_drive_states()
        self._emit_selection()

    def _emit_selection(self) -> None:
        self.selection_changed.emit(self.get_selected_folders())

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _show_context_menu(self, pos) -> None:
        item = self.itemAt(pos)
        if not item or item.text(_COL_NAME) == _PLACEHOLDER_TEXT:
            return
        kind = item.data(_COL_NAME, _ROLE_KIND) or ""
        if isinstance(kind, str) and kind.startswith("drive:"):
            return

        path: Path | None = item.data(_COL_NAME, _ROLE_PATH)
        if not path:
            return

        menu = QMenu(self)
        open_act = QAction("Open in Windows Explorer", self)
        open_act.triggered.connect(lambda: self._open_explorer(path))
        menu.addAction(open_act)
        menu.exec(self.viewport().mapToGlobal(pos))

    @staticmethod
    def _open_explorer(path: Path) -> None:
        import subprocess
        try:
            subprocess.Popen(["explorer", str(path)])
        except Exception:
            pass
