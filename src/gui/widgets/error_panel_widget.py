"""
Mediagator — ErrorPanelWidget.

Collapsible panel that lists transfer errors/flags inline, with an
Export Errors button.

Author: Nathan
"""

from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class ErrorPanelWidget(QWidget):
    """Inline collapsible error/flag display panel.

    Shows automatically on first error.  Contains a scrollable list of
    flagged items and an Export button that saves them to the logs folder.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialise the error panel (starts hidden)."""
        super().__init__(parent)
        self._entries: list[tuple[str, str, str, str]] = []
        self._build_ui()
        self.hide()

    def _build_ui(self) -> None:
        """Construct the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header row with toggle
        header = QHBoxLayout()
        self._toggle_btn = QPushButton("▼ Errors / Flags")
        self._toggle_btn.setFlat(True)
        self._toggle_btn.setStyleSheet("color: #f44336; font-weight: bold;")
        self._toggle_btn.clicked.connect(self._toggle_list)
        header.addWidget(self._toggle_btn)
        header.addStretch()

        self._export_btn = QPushButton("Export Errors")
        self._export_btn.clicked.connect(self._export)
        header.addWidget(self._export_btn)
        layout.addLayout(header)

        # Error list
        self._list = QListWidget()
        self._list.setFixedHeight(150)
        self._list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._list)
        self._list_visible = True

    def add_error(self, timestamp: str, source: str, issue: str, action: str = "SKIPPED") -> None:
        """Add an error entry to the panel, making it visible if hidden.

        Args:
            timestamp: HH:MM:SS string.
            source: Source file path string.
            issue: Short description of the issue.
            action: Action taken (e.g. ``SKIPPED``, ``FLAGGED``).
        """
        self._entries.append((timestamp, source, issue, action))
        item = QListWidgetItem(f"[{timestamp}] {action}: {source}  —  {issue}")
        item.setForeground(QColor("#f44336"))
        self._list.addItem(item)
        self._list.scrollToBottom()
        self.show()

    def _toggle_list(self) -> None:
        """Show or hide the error list."""
        self._list_visible = not self._list_visible
        self._list.setVisible(self._list_visible)
        icon = "▼" if self._list_visible else "▶"
        self._toggle_btn.setText(f"{icon} Errors / Flags ({len(self._entries)})")

    def _export(self) -> None:
        """Save the error list to a text file in logs/."""
        from pathlib import Path as _Path
        logs_dir = _Path("logs")
        logs_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = logs_dir / f"errors_{ts}.txt"
        try:
            with out_path.open("w", encoding="utf-8") as fh:
                for ts_str, src, issue, action in self._entries:
                    fh.write(f"[{ts_str}] [{action}] {src} — {issue}\n")
        except Exception:
            pass

    def clear_errors(self) -> None:
        """Clear all error entries."""
        self._entries.clear()
        self._list.clear()
