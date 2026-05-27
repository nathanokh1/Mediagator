"""
Mediagator — Step 4: Folder Review Tree.

Shows all source folders in a hierarchical QTreeWidget.  User can
uncheck folders and filter by name.

Author: Nathan
"""

import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox,
)
from PyQt6.QtCore import pyqtSignal

from src.gui.wizard_state import WizardState
from src.gui.widgets.folder_tree_widget import FolderTreeWidget
from src.utils.file_utils import human_readable_size

logger = logging.getLogger(__name__)


class FolderReviewStep(QWidget):
    """Step 4 — hierarchical folder review with search and summary.

    Signals:
        next_requested: User clicked Next.
        back_requested: User clicked Back.
    """

    next_requested = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self, state: WizardState, parent: QWidget | None = None) -> None:
        """Initialise the folder review step.

        Args:
            state: Shared wizard state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._state = state
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the step layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Review Folders to Transfer")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Uncheck any folder you want to exclude from the transfer. "
            "Right-click a row to open it in Windows Explorer."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #aaa;")
        layout.addWidget(subtitle)

        # Filter bar
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Type to filter by folder name…")
        self._filter_edit.textChanged.connect(self._on_filter)
        filter_row.addWidget(self._filter_edit)
        layout.addLayout(filter_row)

        # Tree
        self._tree = FolderTreeWidget()
        self._tree.selection_changed.connect(self._on_selection_changed)
        layout.addWidget(self._tree, stretch=1)

        # Summary bar
        self._summary_label = QLabel("")
        self._summary_label.setStyleSheet("color: #aaa; padding: 4px 0;")
        layout.addWidget(self._summary_label)

        # Navigation
        nav = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("secondaryBtn")
        back_btn.setMinimumWidth(100)
        back_btn.clicked.connect(self.back_requested.emit)
        nav.addWidget(back_btn)
        nav.addStretch()
        self._next_btn = QPushButton("Next →")
        self._next_btn.setObjectName("primaryBtn")
        self._next_btn.setMinimumWidth(130)
        self._next_btn.clicked.connect(self._on_next)
        nav.addWidget(self._next_btn)
        layout.addLayout(nav)

    def refresh(self) -> None:
        """Populate the tree when the step becomes visible."""
        if not self._state.scan_result:
            return
        nodes = self._state.scan_result.folder_nodes
        self._tree.populate(nodes)
        self._state.checked_folder_paths = {n.path for n in nodes if n.is_checked}
        self._update_summary()

    def _on_filter(self, text: str) -> None:
        """Filter the tree by folder name.

        Args:
            text: Filter text.
        """
        self._tree.filter_by_text(text)

    def _on_selection_changed(self, checked_paths: set[Path]) -> None:
        """Sync checked paths to state and update summary.

        Args:
            checked_paths: Set of checked folder paths.
        """
        self._state.checked_folder_paths = checked_paths
        self._update_summary()

    def _update_summary(self) -> None:
        """Refresh the summary bar below the tree."""
        if not self._state.scan_result:
            return
        checked = self._state.checked_folder_paths
        nodes = [n for n in self._state.scan_result.folder_nodes if n.path in checked]
        total_files = sum(n.file_count for n in nodes)
        total_bytes = sum(n.total_size_bytes for n in nodes)
        self._summary_label.setText(
            f"{len(nodes)} folders selected  |  {total_files:,} files  |  "
            f"{human_readable_size(total_bytes)}"
        )

    def _on_next(self) -> None:
        """Advance to Step 5."""
        self.next_requested.emit()
