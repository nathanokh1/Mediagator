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
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QFrame,
)
from PyQt6.QtCore import pyqtSignal, pyqtSlot, Qt

from src.gui.wizard_state import WizardState
from src.gui.widgets.progress_widget import ProgressWidget
from src.gui.widgets.error_panel_widget import ErrorPanelWidget
from src.core.transfer_engine import TransferWorker
from src.core.hardware_profile import add_defender_exclusions, remove_defender_exclusions
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
        self._defender_paths: list = []   # paths added to Defender exclusions
        self._completed_paths: set[str] = set()  # source paths already transferred
        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the step layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Transfer in Progress")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # ── Status banners (Defender + free space) ───────────────────────
        self._defender_banner = QLabel("")
        self._defender_banner.setWordWrap(True)
        self._defender_banner.setStyleSheet(
            "background: #1a2e1a; color: #81c784; border: 1px solid #2e5c2e; "
            "border-radius: 4px; padding: 4px 10px; font-size: 11px;"
        )
        self._defender_banner.hide()
        layout.addWidget(self._defender_banner)

        self._space_banner = QLabel("")
        self._space_banner.setWordWrap(True)
        self._space_banner.setStyleSheet(
            "background: #2e1a1a; color: #ef9a9a; border: 1px solid #5c2e2e; "
            "border-radius: 4px; padding: 4px 10px; font-size: 11px;"
        )
        self._space_banner.hide()
        layout.addWidget(self._space_banner)

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

        self._resume_btn = QPushButton("▶  Resume Transfer")
        self._resume_btn.setObjectName("accentBtn")
        self._resume_btn.setFixedHeight(36)
        self._resume_btn.setMinimumWidth(160)
        self._resume_btn.clicked.connect(self._on_resume)
        self._resume_btn.hide()
        nav.addWidget(self._resume_btn)

        self._cancel_btn = QPushButton("Cancel Transfer")
        self._cancel_btn.setFixedSize(160, 36)
        self._cancel_btn.setStyleSheet("background-color: #b71c1c;")
        self._cancel_btn.clicked.connect(self._on_cancel)
        nav.addWidget(self._cancel_btn)
        layout.addLayout(nav)

    def refresh(self) -> None:
        """Start the transfer when the step becomes visible."""
        self._cancel_event.clear()
        self._cancel_btn.setText("Cancel Transfer")
        self._cancel_btn.setEnabled(True)
        self._resume_btn.hide()
        self._completed_paths.clear()
        self._error_panel.clear_errors()
        self._defender_banner.hide()
        self._space_banner.hide()
        self._start_time = time.monotonic()

        plan = self._state.transfer_plan
        if not plan:
            logger.error("No transfer plan — cannot start transfer.")
            return

        # Attempt to add Defender exclusions for source + destination paths.
        # This is fire-and-forget — if the app isn't admin it logs a warning and
        # carries on.  The paths are stored so we can remove them afterwards.
        self._defender_paths = []
        scan_result = self._state.scan_result
        if scan_result and self._state.selected_scan_folders:
            # Collect unique drive roots from selected folders
            roots = {p.anchor for p in self._state.selected_scan_folders if p.anchor}
            self._defender_paths.extend(roots)
        if self._state.destination_root:
            self._defender_paths.append(self._state.destination_root)

        if self._defender_paths:
            added = add_defender_exclusions(self._defender_paths)
            if added:
                logger.info("Defender exclusions active for %d paths", len(self._defender_paths))
                self._defender_banner.setText(
                    "🛡  Windows Defender exclusions active — source and destination paths "
                    "are excluded from real-time scanning for this transfer."
                )
                self._defender_banner.show()
            else:
                logger.info("Defender exclusions not added (not admin or unavailable)")
                self._defender_banner.hide()
        else:
            self._defender_banner.hide()

        # ── Free space warning ────────────────────────────────────────────
        self._space_banner.hide()
        dest = self._state.destination_root
        plan = self._state.transfer_plan
        if dest and plan:
            try:
                import psutil
                usage = psutil.disk_usage(str(dest))
                needed = plan.total_size_bytes
                if usage.free < needed:
                    from src.utils.file_utils import human_readable_size
                    self._space_banner.setText(
                        f"⚠  Low disk space — destination has "
                        f"{human_readable_size(usage.free)} free but transfer needs "
                        f"~{human_readable_size(needed)}.  Transfer may fail partway through."
                    )
                    self._space_banner.show()
            except Exception:
                pass

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
            hardware_profile=self._state.hardware_profile,
            skip_paths=self._completed_paths,
        )
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.item_completed.connect(self._on_item_completed)
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
    def _on_item_completed(self, source: str, _dest: str, result: str) -> None:
        """Track successfully transferred source paths for resume support.

        Args:
            source: Source file path string.
            _dest: Destination path (unused here).
            result: Transfer outcome string.
        """
        if result == "SUCCESS":
            self._completed_paths.add(source)

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
        remove_defender_exclusions(self._defender_paths)
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
        remove_defender_exclusions(self._defender_paths)
        if self._state.transfer_plan:
            save_session({"cancelled": True})
        logger.info("Transfer cancelled by user — %d files already done.", len(self._completed_paths))

        # Show resume button if any files were completed
        if self._completed_paths:
            self._resume_btn.setText(
                f"▶  Resume  ({len(self._completed_paths):,} done, skipping…)"
            )
            self._resume_btn.show()

    def _on_resume(self) -> None:
        """Restart the worker, skipping already-transferred files."""
        if not self._state.transfer_plan:
            return

        plan = self._state.transfer_plan
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        transfer_logger = get_transfer_logger(ts)

        self._cancel_event.clear()
        self._cancel_btn.setText("Cancel Transfer")
        self._cancel_btn.setEnabled(True)
        self._resume_btn.hide()

        remaining = plan.total_files - len(self._completed_paths)
        logger.info("Resuming transfer — %d files remaining", remaining)

        self._worker = TransferWorker(
            plan=plan,
            settings=self._state.settings,
            transfer_logger=transfer_logger,
            cancellation_event=self._cancel_event,
            hardware_profile=self._state.hardware_profile,
            skip_paths=self._completed_paths,
        )
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.item_completed.connect(self._on_item_completed)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.phase_completed.connect(self._on_phase_complete)
        self._worker.transfer_complete.connect(self._on_transfer_complete)
        self._worker.start()
