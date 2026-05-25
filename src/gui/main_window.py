"""
MediaMitigator — MainWindow.

Hosts the step indicator breadcrumb and the QStackedWidget that
renders each of the 8 wizard steps.

Author: Nathan
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStackedWidget, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.config.constants import WINDOW_TITLE, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, STEP_NAMES
from src.gui.wizard_state import WizardState
from src.gui.steps.step_01_drive_selection import DriveSelectionStep
from src.gui.steps.step_02_initial_scan import InitialScanStep
from src.gui.steps.step_03_destination import DestinationStep
from src.gui.steps.step_04_folder_review import FolderReviewStep
from src.gui.steps.step_05_transfer_settings import TransferSettingsStep
from src.gui.steps.step_06_pre_transfer import PreTransferStep
from src.gui.steps.step_07_progress import TransferProgressStep
from src.gui.steps.step_08_report import ReportStep

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Application main window containing the 8-step wizard.

    Args:
        state: Shared :class:`WizardState` instance.
    """

    def __init__(self, state: WizardState) -> None:
        """Initialise the main window.

        Args:
            state: Shared wizard state passed to every step.
        """
        super().__init__()
        self._state = state
        self._current_step = 0
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1200, 800)
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the main window layout."""
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet("background: #1e1e2e; border-bottom: 1px solid #333;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        app_title = QLabel("MediaMitigator")
        font = QFont()
        font.setBold(True)
        font.setPointSize(13)
        app_title.setFont(font)
        app_title.setStyleSheet("color: #ff9800;")
        header_layout.addWidget(app_title)
        header_layout.addStretch()
        root.addWidget(header)

        # Step breadcrumb
        self._breadcrumb = _StepBreadcrumb(STEP_NAMES)
        root.addWidget(self._breadcrumb)

        # Stacked widget
        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        # Build steps
        self._steps: list[QWidget] = []
        self._step_classes = [
            DriveSelectionStep,
            InitialScanStep,
            DestinationStep,
            FolderReviewStep,
            TransferSettingsStep,
            PreTransferStep,
            TransferProgressStep,
            ReportStep,
        ]

        for StepClass in self._step_classes:
            step = StepClass(self._state)
            self._steps.append(step)
            self._stack.addWidget(step)

        # Wire navigation signals
        self._connect_signals()
        self._go_to_step(0)

    def _connect_signals(self) -> None:
        """Connect next_requested / back_requested signals for each step."""
        for i, step in enumerate(self._steps):
            if hasattr(step, "next_requested"):
                step.next_requested.connect(lambda idx=i: self._go_to_step(idx + 1))
            if hasattr(step, "back_requested"):
                step.back_requested.connect(lambda idx=i: self._go_to_step(idx - 1))

        # Step 8: start new transfer → return to step 1
        report_step = self._steps[7]
        if hasattr(report_step, "new_transfer_requested"):
            report_step.new_transfer_requested.connect(lambda: self._go_to_step(0))

    def _go_to_step(self, index: int) -> None:
        """Navigate to a wizard step by index.

        Args:
            index: 0-based step index.
        """
        if index < 0 or index >= len(self._steps):
            return
        self._current_step = index
        self._stack.setCurrentIndex(index)
        self._breadcrumb.set_active(index)

        step = self._steps[index]
        if hasattr(step, "refresh"):
            step.refresh()


class _StepBreadcrumb(QWidget):
    """Horizontal step indicator shown at the top of every wizard screen."""

    def __init__(self, names: list[str]) -> None:
        """Initialise the breadcrumb.

        Args:
            names: Ordered list of step display names.
        """
        super().__init__()
        self.setFixedHeight(40)
        self.setStyleSheet("background: #121218; border-bottom: 1px solid #2a2a3a;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        self._labels: list[QLabel] = []
        for i, name in enumerate(names):
            lbl = QLabel(f"{i + 1}. {name}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #555; font-size: 11px; padding: 0 8px;")
            layout.addWidget(lbl)
            self._labels.append(lbl)
            if i < len(names) - 1:
                sep = QLabel("›")
                sep.setStyleSheet("color: #333; padding: 0 2px;")
                layout.addWidget(sep)

        layout.addStretch()

    def set_active(self, index: int) -> None:
        """Highlight the active step label.

        Args:
            index: 0-based active step index.
        """
        for i, lbl in enumerate(self._labels):
            if i == index:
                lbl.setStyleSheet("color: #ff9800; font-weight: bold; font-size: 11px; padding: 0 8px;")
            elif i < index:
                lbl.setStyleSheet("color: #4caf50; font-size: 11px; padding: 0 8px;")
            else:
                lbl.setStyleSheet("color: #555; font-size: 11px; padding: 0 8px;")
