"""
Mediagator — DriveCardWidget.

Displays a single drive as a selectable card with label, usage bar,
free space and total size.

Author: Nathan
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QProgressBar, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.models.scan_result import DriveInfo
from src.utils.file_utils import human_readable_size


class DriveCardWidget(QFrame):
    """Card-style widget representing one Windows drive.

    Signals:
        selection_changed(str, bool): (drive_letter, is_selected)
    """

    selection_changed = pyqtSignal(str, bool)

    def __init__(self, drive: DriveInfo, parent: QWidget | None = None) -> None:
        """Initialise the drive card.

        Args:
            drive: Drive metadata.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._drive = drive
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the card layout."""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(200)
        self.setMinimumHeight(130)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Header row: checkbox + drive letter
        header = QHBoxLayout()
        self._checkbox = QCheckBox()
        self._checkbox.setChecked(self._drive.is_selected)
        self._checkbox.stateChanged.connect(self._on_state_changed)
        header.addWidget(self._checkbox)

        letter_label = QLabel(f"Drive {self._drive.letter}:")
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        letter_label.setFont(font)
        header.addWidget(letter_label)
        header.addStretch()
        layout.addLayout(header)

        # Drive label
        label_text = self._drive.label or "Local Disk"
        lbl = QLabel(label_text)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        # Usage bar
        usage_bar = QProgressBar()
        usage_bar.setRange(0, 100)
        usage_bar.setValue(int(self._drive.usage_percent))
        usage_bar.setTextVisible(False)
        usage_bar.setFixedHeight(8)
        layout.addWidget(usage_bar)

        # Space info
        free_str = human_readable_size(self._drive.free_bytes)
        total_str = human_readable_size(self._drive.total_bytes)
        space_lbl = QLabel(f"Free: {free_str} / {total_str}")
        space_lbl.setStyleSheet("color: #aaa; font-size: 10px;")
        layout.addWidget(space_lbl)

        layout.addStretch()

    def _on_state_changed(self, state: int) -> None:
        """Propagate checkbox change as a signal.

        Args:
            state: Qt checkbox state value.
        """
        is_checked = (state == Qt.CheckState.Checked.value)
        self._drive.is_selected = is_checked
        self.selection_changed.emit(self._drive.letter, is_checked)

    @property
    def drive_letter(self) -> str:
        """Drive letter this card represents."""
        return self._drive.letter

    @property
    def is_selected(self) -> bool:
        """Whether this drive is checked for scanning."""
        return self._checkbox.isChecked()
