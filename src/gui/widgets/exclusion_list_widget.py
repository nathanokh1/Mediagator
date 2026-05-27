"""
Mediagator — ExclusionListWidget.

A list widget with Add / Remove buttons for managing the folder
exclusion list used during scanning.

Author: Nathan
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QInputDialog, QLabel,
)
from PyQt6.QtCore import pyqtSignal


class ExclusionListWidget(QWidget):
    """Editable list of folder-name exclusions.

    Signals:
        exclusions_changed(list[str]): Emitted whenever the list changes.
    """

    exclusions_changed = pyqtSignal(list)

    def __init__(
        self,
        exclusions: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Initialise the widget.

        Args:
            exclusions: Initial exclusion strings.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._build_ui(exclusions or [])

    def _build_ui(self, exclusions: list[str]) -> None:
        """Construct the layout.

        Args:
            exclusions: Initial list contents.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("Folder Exclusions (case-insensitive, skipped during scan):")
        layout.addWidget(lbl)

        self._list = QListWidget()
        for item in sorted(exclusions):
            self._list.addItem(item)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add")
        add_btn.clicked.connect(self._add_exclusion)
        remove_btn = QPushButton("− Remove")
        remove_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def _add_exclusion(self) -> None:
        """Open an input dialog and add the entered folder name."""
        text, ok = QInputDialog.getText(self, "Add Exclusion", "Folder name to exclude:")
        if ok and text.strip():
            normalized = text.strip().lower()
            existing = self.get_exclusions()
            if normalized not in existing:
                self._list.addItem(normalized)
                self.exclusions_changed.emit(self.get_exclusions())

    def _remove_selected(self) -> None:
        """Remove the currently selected item from the list."""
        for item in self._list.selectedItems():
            self._list.takeItem(self._list.row(item))
        self.exclusions_changed.emit(self.get_exclusions())

    def get_exclusions(self) -> list[str]:
        """Return the current list of exclusion strings.

        Returns:
            Sorted list of lowercase exclusion strings.
        """
        return sorted(
            self._list.item(i).text()
            for i in range(self._list.count())
        )

    def set_exclusions(self, exclusions: list[str]) -> None:
        """Replace the list contents.

        Args:
            exclusions: New list of exclusion strings.
        """
        self._list.clear()
        for item in sorted(exclusions):
            self._list.addItem(item)
