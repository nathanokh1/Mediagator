"""
MediaMitigator — Step 2: Initial Scan.

Runs a fast background drive scan and shows a rich visual dashboard.
Results are cached in WizardState — navigating back and returning does
NOT restart the scan; results are shown immediately.

Smart EXIF analysis runs in its own QThread after the scan so the GUI
never freezes waiting for it.

Author: Nathan
"""

import logging
import threading
import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, pyqtSlot, QThread

from src.gui.wizard_state import WizardState
from src.gui.widgets.scan_dashboard_widget import ScanDashboardWidget
from src.core.scanner import ScanWorker
from src.utils.date_utils import format_duration

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background worker for smart analysis
# ---------------------------------------------------------------------------

class _AnalysisWorker(QThread):
    """Run SmartAnalyzer in a background thread.

    Signals:
        analysis_complete(object): Emits the SmartInsights result.
    """

    analysis_complete = pyqtSignal(object)

    def __init__(self, scan_result) -> None:
        super().__init__()
        self._result = scan_result

    def run(self) -> None:
        try:
            from src.core.smart_analyzer import analyze
            insights = analyze(self._result)
        except Exception as exc:
            logger.warning("Smart analysis failed: %s", exc)
            insights = None
        self.analysis_complete.emit(insights)


# ---------------------------------------------------------------------------
# Step widget
# ---------------------------------------------------------------------------

class InitialScanStep(QWidget):
    """Step 2 — background scan with live progress and visual dashboard.

    Results are cached in :attr:`WizardState.scan_result`.  Calling
    :meth:`refresh` when results already exist shows the cached dashboard
    instantly without rescanning.

    Signals:
        next_requested: User clicked Next.
        back_requested: User clicked Back.
    """

    next_requested = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self, state: WizardState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._worker: ScanWorker | None = None
        self._analysis_worker: _AnalysisWorker | None = None
        self._cancel_event = threading.Event()
        self._start_time: float = 0.0
        self._scan_elapsed: float = 0.0
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(500)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        # Title
        self._title = QLabel("Scanning for Media Files")
        self._title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self._title)

        # ── Progress panel (visible while scanning) ──────────────────
        self._progress_panel = QGroupBox("Scan Progress")
        pg = QVBoxLayout(self._progress_panel)
        pg.setSpacing(6)

        self._root_label = QLabel("Root: —")
        pg.addWidget(self._root_label)

        self._folder_label = QLabel("Folder: —")
        self._folder_label.setWordWrap(True)
        pg.addWidget(self._folder_label)

        stats_row = QHBoxLayout()
        self._found_label = QLabel("Media files found: 0")
        self._rate_label  = QLabel("Rate: —")
        self._elapsed_label = QLabel("Elapsed: 0s")
        self._rate_label.setStyleSheet("color: #aaa;")
        self._elapsed_label.setStyleSheet("color: #aaa;")
        stats_row.addWidget(self._found_label)
        stats_row.addStretch()
        stats_row.addWidget(self._rate_label)
        stats_row.addSpacing(20)
        stats_row.addWidget(self._elapsed_label)
        pg.addLayout(stats_row)

        self._spinner = QProgressBar()
        self._spinner.setRange(0, 0)
        self._spinner.setFixedHeight(8)
        pg.addWidget(self._spinner)

        layout.addWidget(self._progress_panel)

        # ── Analysis status (shown between scan complete and analysis done) ──
        self._analysis_label = QLabel("")
        self._analysis_label.setStyleSheet(
            "color: #ff9800; font-style: italic; font-size: 12px;"
        )
        self._analysis_label.hide()
        layout.addWidget(self._analysis_label)

        # ── Dashboard (visible after analysis) ───────────────────────
        self._dashboard = ScanDashboardWidget()
        self._dashboard.hide()
        layout.addWidget(self._dashboard, stretch=1)

        # ── Rescan button ─────────────────────────────────────────────
        self._rescan_btn = QPushButton("↺ Re-scan")
        self._rescan_btn.setFixedSize(110, 32)
        self._rescan_btn.hide()
        self._rescan_btn.clicked.connect(self._start_scan)

        # ── Navigation ────────────────────────────────────────────────
        nav = QHBoxLayout()
        self._back_btn = QPushButton("← Back")
        self._back_btn.setObjectName("secondaryBtn")
        self._back_btn.setMinimumWidth(100)
        self._back_btn.clicked.connect(self.back_requested.emit)
        nav.addWidget(self._back_btn)
        nav.addWidget(self._rescan_btn)
        nav.addStretch()
        self._next_btn = QPushButton("Next →")
        self._next_btn.setObjectName("primaryBtn")
        self._next_btn.setMinimumWidth(130)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self.next_requested.emit)
        nav.addWidget(self._next_btn)
        layout.addLayout(nav)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Show cached results instantly, or start a new scan if none exist."""
        if self._state.scan_result is not None:
            self._show_cached_results()
            return
        self._start_scan()

    def _show_cached_results(self) -> None:
        """Display cached scan results without running a new scan."""
        self._title.setText("Scan Results  (cached)")
        self._progress_panel.hide()
        self._analysis_label.hide()

        result = self._state.scan_result
        insights = getattr(self._state, "_scan_insights", None)
        self._dashboard.populate(result, insights)
        self._dashboard.show()
        self._rescan_btn.show()
        self._next_btn.setEnabled(True)

    def _start_scan(self) -> None:
        """Begin a fresh scan, discarding any previous results."""
        self._state.scan_result = None
        if hasattr(self._state, "_scan_insights"):
            self._state._scan_insights = None

        self._title.setText("Scanning for Media Files")
        self._progress_panel.show()
        self._analysis_label.hide()
        self._dashboard.hide()
        self._rescan_btn.hide()
        self._next_btn.setEnabled(False)
        self._cancel_event.clear()
        self._spinner.setRange(0, 0)
        self._root_label.setText("Root: —")
        self._folder_label.setText("Folder: —")
        self._found_label.setText("Media files found: 0")
        self._rate_label.setText("Rate: —")
        self._elapsed_label.setText("Elapsed: 0s")
        self._start_time = time.monotonic()
        self._elapsed_timer.start()

        scan_folders = self._state.selected_scan_folders
        exclusions = set(self._state.settings.get("exclusion_list", []))

        if not scan_folders:
            self._root_label.setText("No folders selected — go back and select folders.")
            self._elapsed_timer.stop()
            return

        extensions = self._state.selected_extensions or None
        self._worker = ScanWorker(scan_folders, exclusions, self._cancel_event, extensions)
        self._worker.progress_updated.connect(self._on_progress)
        self._worker.scan_complete.connect(self._on_scan_complete)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()
        logger.info(
            "Scan started: %d folders, %d extensions",
            len(scan_folders),
            len(extensions) if extensions else 0,
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _tick_elapsed(self) -> None:
        elapsed = time.monotonic() - self._start_time
        self._elapsed_label.setText(f"Elapsed: {format_duration(elapsed)}")

    @pyqtSlot(str, str, int)
    def _on_progress(self, root: str, folder: str, count: int) -> None:
        elapsed = time.monotonic() - self._start_time
        rate = count / max(elapsed, 0.001)
        self._root_label.setText(f"Root: {root}")
        self._folder_label.setText(f"  {folder}")
        self._found_label.setText(f"Media files found: {count:,}")
        self._rate_label.setText(f"Rate: {rate:.0f} files/s")

    @pyqtSlot(object)
    def _on_scan_complete(self, result) -> None:
        """Scan thread finished — cache result, hand off to analysis thread."""
        self._elapsed_timer.stop()
        self._scan_elapsed = time.monotonic() - self._start_time
        self._state.scan_result = result

        logger.info(
            "Scan complete: %d files, %d folders, %.1f s",
            result.total_files,
            result.folder_count,
            self._scan_elapsed,
        )

        # Show scan counts immediately so the UI feels responsive
        self._progress_panel.hide()
        self._title.setText(
            f"Scan Complete  —  {result.total_files:,} files  "
            f"in {format_duration(self._scan_elapsed)}"
        )

        # Show partial dashboard (no insights yet) and a status message
        self._dashboard.populate(result, insights=None)
        self._dashboard.show()
        self._analysis_label.setText(
            "🔍 Running smart EXIF analysis in background…  "
            "(Next is available now — analysis will finish shortly)"
        )
        self._analysis_label.show()
        # Allow proceeding immediately even before analysis finishes
        self._next_btn.setEnabled(True)

        # Kick off analysis in its own thread
        self._analysis_worker = _AnalysisWorker(result)
        self._analysis_worker.analysis_complete.connect(self._on_analysis_complete)
        self._analysis_worker.start()

    @pyqtSlot(object)
    def _on_analysis_complete(self, insights) -> None:
        """Analysis thread finished — refresh dashboard with insights."""
        self._state._scan_insights = insights
        self._analysis_label.hide()
        self._rescan_btn.show()

        if insights:
            logger.info(
                "Smart analysis complete: %d cameras, %d events, GPS %.0f%%",
                len(insights.top_cameras),
                insights.event_count,
                insights.gps_percent,
            )

        # Re-populate with full insights
        self._dashboard.populate(self._state.scan_result, insights)

    @pyqtSlot(str)
    def _on_error(self, message: str) -> None:
        logger.warning("Scan error: %s", message)
