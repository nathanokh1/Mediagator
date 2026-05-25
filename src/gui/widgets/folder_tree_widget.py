"""
MediaMitigator — FolderTreeWidget.

QTreeWidget subclass for displaying and managing source folders
before transfer.

Author: Nathan
"""

import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction

from src.models.folder_node import FolderNode, FolderStatus
from src.utils.file_utils import human_readable_size

_COL_NAME = 0
_COL_FILES = 1
_COL_SIZE = 2
_COL_DEST = 3
_COL_STATUS = 4

_STATUS_COLORS = {
    FolderStatus.READY: "#4caf50",
    FolderStatus.MULTI_YEAR: "#ff9800",
    FolderStatus.DUPLICATE_ROOT: "#2196f3",
    FolderStatus.EXCLUDED: "#9e9e9e",
    FolderStatus.COMPLETED: "#4caf50",
    FolderStatus.FAILED: "#f44336",
    FolderStatus.SKIPPED: "#9e9e9e",
}


class FolderTreeWidget(QTreeWidget):
    """Hierarchical tree of transfer-eligible folders.

    Signals:
        selection_changed(set[Path]): Emits the set of checked folder paths.
    """

    selection_changed = pyqtSignal(set)

    def __init__(self, parent=None) -> None:
        """Initialise the tree widget."""
        super().__init__(parent)
        self.setHeaderLabels(["Folder Name", "Files", "Size", "Destination", "Status"])
        self.setColumnWidth(_COL_NAME, 260)
        self.setColumnWidth(_COL_FILES, 60)
        self.setColumnWidth(_COL_SIZE, 80)
        self.setColumnWidth(_COL_DEST, 300)
        self.setColumnWidth(_COL_STATUS, 100)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.itemChanged.connect(self._on_item_changed)
        self._nodes: dict[int, FolderNode] = {}

    def populate(self, nodes: list[FolderNode]) -> None:
        """Populate the tree with a flat list of :class:`FolderNode`.

        Args:
            nodes: Folder nodes from the scan result.
        """
        self.blockSignals(True)
        self.clear()
        self._nodes.clear()
        for node in nodes:
            item = self._make_item(node)
            self.addTopLevelItem(item)
        self.blockSignals(False)

    def _make_item(self, node: FolderNode) -> QTreeWidgetItem:
        """Build a QTreeWidgetItem from a FolderNode.

        Args:
            node: Source folder node.

        Returns:
            Populated tree row.
        """
        dest_str = str(node.destination_path) if node.destination_path else "—"
        item = QTreeWidgetItem([
            node.name,
            str(node.file_count),
            human_readable_size(node.total_size_bytes),
            dest_str,
            node.status.value,
        ])
        check_state = Qt.CheckState.Checked if node.is_checked else Qt.CheckState.Unchecked
        item.setCheckState(_COL_NAME, check_state)
        item.setData(_COL_NAME, Qt.ItemDataRole.UserRole, id(node))
        color = _STATUS_COLORS.get(node.status, "#ffffff")
        item.setForeground(_COL_STATUS, __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor(color))
        self._nodes[id(node)] = node
        return item

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Sync node checked state and emit selection_changed.

        Args:
            item: Changed tree item.
            column: Column that changed.
        """
        if column != _COL_NAME:
            return
        node_id = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
        node = self._nodes.get(node_id)
        if node:
            node.is_checked = (item.checkState(_COL_NAME) == Qt.CheckState.Checked)
        self.selection_changed.emit(self._get_checked_paths())

    def _get_checked_paths(self) -> set[Path]:
        """Return the set of paths for all checked nodes.

        Returns:
            Set of :class:`Path` objects.
        """
        paths: set[Path] = set()
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item and item.checkState(_COL_NAME) == Qt.CheckState.Checked:
                node_id = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
                node = self._nodes.get(node_id)
                if node:
                    paths.add(node.path)
        return paths

    def filter_by_text(self, text: str) -> None:
        """Show only rows whose folder name contains *text*.

        Args:
            text: Filter string (case-insensitive).
        """
        text = text.lower()
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item:
                item.setHidden(text not in item.text(_COL_NAME).lower())

    def _show_context_menu(self, pos) -> None:
        """Display the right-click context menu.

        Args:
            pos: Mouse position relative to the widget.
        """
        item = self.itemAt(pos)
        if not item:
            return
        node_id = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
        node = self._nodes.get(node_id)
        if not node:
            return

        menu = QMenu(self)
        open_action = QAction("Open in Windows Explorer", self)
        open_action.triggered.connect(lambda: self._open_explorer(node.path))
        menu.addAction(open_action)
        menu.exec(self.viewport().mapToGlobal(pos))

    def _open_explorer(self, path: Path) -> None:
        """Open a path in Windows Explorer.

        Args:
            path: Folder to reveal.
        """
        try:
            subprocess.Popen(["explorer", str(path)])
        except Exception:
            pass
