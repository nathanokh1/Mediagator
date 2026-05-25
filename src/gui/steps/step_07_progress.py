"""
MediaMitigator — Step 7: Transfer Progress.

Runs the TransferWorker and displays live progress, phase indicator,
and the collapsible error panel.

Author: Nathan
"""

import logging
import threading
import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
)
from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt

from src.gui.wizard_state import WizardState
from src.gui.widgets.progress_widget import ProgressWidget
from src.gui.widgets.error_panel_widget import ErrorPanelWidget
from src.core.transfer_engine import TransferWorker
from src.utils.logger import get_transfer_logger
from src.utils.notification import notify
from src.config.settings import save_session, clear_session

logger = logging.getLogger(__name__)


class TransferProgressStep(QWidget):
    """Step 7 — live transfer progress with cancel support.

    Signals:
        next_requested: Transfer complete; advance to Step 8.
        back_requested: Back to Step 6 (only when not running).
    """

    next_requested = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self, state: WizardState, parent: QWidget | None = None) -> None:
        """Initialise the progress step.

        Args:
            state: Shared wizard state.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self._state = state
        self._worker: TransferWorker | None = None
        self._cancel_event = threading.Event()
        self._start_time: float = 0.0
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the step layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Transfer in Progress")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Phase indicator
        self._phase_label = QLabel("")
        self._phase_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        self._phase_label.hide()
        layout.addWidget(self._phase_label)

        # Progress widget
        self._progress_widget = ProgressWidget()
        layout.addWidget(self._progress_widget)

        # Error panel
        self._error_panel = ErrorPanelWidget()
        layout.addWidget(self._error_panel)

        layout.addStretch()

        # Navigation
        nav = QHBoxLayout()
        nav.addStretch()
        self._cancel_btn = QPushButton("Cancel Transfer")
        self._cancel_btn.setFixedSize(160, 36)
        self._cancel_btn.setStyleSheet("background-color: #b71c1c;")
        self._cancel_btn.clicked.connect(self._on_cancel)
        nav.addWidget(self._cancel_btn)
        layout.addLayout(nav)

    def refresh(self) -> None:
        """Start the transfer when the step becomes visible."""
        self._cancel_event.clear()
        self._error_panel.clear_errors()
        self._start_time = time.monotonic()

        plan = self._state.transfer_plan
        if not plan:
            logger.error("No transfer plan — cannot start transfer.")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        transfer_logger = get_transfer_logger(ts)

        if plan.is_phased and plan.phase_count > 1:
            self._phase_label.setText(f"Phase 1 of {plan.phase_count}")
            self._phase_label.show()

        self._worker = TransferWorker(
            plan=plan,
            settings=self._state.settings,
            transfer_logger=transfer_logger,
            cancellation_event=self._cancel_event,
        )
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.phase_completed.connect(self._on_phase_complete)
        self._worker.transfer_complete.connect(self._on_transfer_complete)
        self._worker.start()

    @pyqtSlot(int, int, float, float, str, str)
    def _on_progress(
        self,
        files_done: int,
        files_total: int,
        bytes_transferred: float,
        speed_mbs: float,
        src: str,
        dst: str,
    ) -> None:
        """Update the progress widget.

        Args:
            files_done: Files completed.
            files_total: Total files.
            bytes_transferred: Bytes transferred.
            speed_mbs: Current speed MB/s.
            src: Source path string.
            dst: Destination path string.
        """
        elapsed = time.monotonic() - self._start_time
        self._progress_widget.update_progress(
            files_done, files_total, bytes_transferred, speed_mbs, src, dst, elapsed
        )

    @pyqtSlot(str, str, str)
    def _on_error(self, timestamp: str, source: str, issue: str) -> None:
        """Append to error panel and notify if threshold exceeded.

        Args:
            timestamp: HH:MM:SS string.
            source: Source path string.
            issue: Error description.
        """
        self._error_panel.add_error(timestamp, source, issue)
        error_count = len(self._error_panel._entries)
        if error_count == 10:
            notify(self._state.settings, "MediaMitigator — Errors", f"{error_count} errors encountered during transfer.")

    @pyqtSlot(int, int)
    def _on_phase_complete(self, phase_num: int, total: int) -> None:
        """Handle a phase completion notification.

        Args:
            phase_num: Completed phase number.
            total: Total phases.
        """
        self._phase_label.setText(f"Phase {phase_num + 1} of {total}")
        notify(
            self._state.settings,
            "MediaMitigator — Phase Complete",
            f"Phase {phase_num} of {total} complete.  Starting phase {phase_num + 1}…",
        )

    @pyqtSlot(object)
    def _on_transfer_complete(self, stats) -> None:
        """Handle full transfer completion.

        Args:
            stats: :class:`TransferStats` with final statistics.
        """
        self._state.transfer_stats = stats
        clear_session()
        notify(
            self._state.settings,
            "MediaMitigator — Transfer Complete",
            f"All {stats.files_completed:,} files transferred successfully.",
        )
        self._cancel_btn.setEnabled(False)
        self.next_requested.emit()

    def _on_cancel(self) -> None:
        """Request a clean cancel and save session state."""
        self._cancel_event.set()
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setText("Cancelling…")
        if self._state.transfer_plan:
            save_session({"cancelled": True})
        logger.info("Transfer cancelled by user.")
