"""
Mediagator — Step 6: Pre-Transfer Analysis.

What this step does
-------------------
1. Disk speed test  — writes a small temp file to the destination and measures
   the actual write speed.  This gives a realistic transfer-time estimate.
2. Transfer plan    — tallies every checked folder's files/bytes and resolves
   final destination paths (dates were already read in Step 3's probe, so this
   is nearly instant).
3. Phase check      — if the estimated time exceeds 60 minutes the transfer is
   automatically split into ~45-minute phases so you can take breaks, verify
   results, and resume without losing progress.
4. Confirmation     — shows the summary and lets you start when ready.

Author: Nathan
"""

import logging
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFrame, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, QThread, pyqtSlot, Qt
from PyQt6.QtGui import QColor

from src.gui.wizard_state import WizardState
from src.core.analyzer import build_transfer_plan
from src.core.phase_manager import build_phases
from src.utils.date_utils import format_duration
from src.utils.file_utils import human_readable_size
from src.config.constants import PHASE_THRESHOLD_SECONDS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

class AnalysisWorker(QThread):
    """Builds the transfer plan and runs the disk speed test.

    Signals:
        analysis_complete(object): Emits the built TransferPlan.
    """

    analysis_complete = pyqtSignal(object)

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        self._state = state

    def run(self) -> None:
        if not self._state.scan_result or not self._state.destination_root:
            return
        plan = build_transfer_plan(
            self._state.scan_result,
            self._state.destination_root,
            self._state.checked_folder_paths or None,
            org_mode=self._state.org_mode,
        )
        if plan.is_phased:
            plan.phases = build_phases(plan)
        else:
            from src.models.transfer_phase import TransferPhase
            plan.phases = [TransferPhase(phase_number=1, folder_nodes=plan.folder_nodes)]
        self._state.transfer_plan = plan
        self.analysis_complete.emit(plan)


# ---------------------------------------------------------------------------
# Small stat card (re-uses dashboard style)
# ---------------------------------------------------------------------------

class _StatCard(QFrame):
    def __init__(self, label: str, value: str, colour: str, note: str = "", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            "background: #2a2a3e; border: 1px solid #3a3a5a; border-radius: 8px;"
        )
        self.setMinimumWidth(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(3)

        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"color: {colour}; font-size: 20px; font-weight: bold; border: none;"
        )
        lay.addWidget(self._val)

        lbl = QLabel(label)
        lbl.setObjectName("hintLabel")
        lbl.setStyleSheet("font-size: 11px; border: none;")
        lay.addWidget(lbl)

        if note:
            note_lbl = QLabel(note)
            note_lbl.setObjectName("hintLabel")
            note_lbl.setStyleSheet("font-size: 10px; border: none;")
            lay.addWidget(note_lbl)

    def set_value(self, value: str) -> None:
        self._val.setText(value)


# ---------------------------------------------------------------------------
# Step widget
# ---------------------------------------------------------------------------

class PreTransferStep(QWidget):
    """Step 6 — disk speed test + transfer plan summary.

    Signals:
        next_requested: User clicked Start Transfer.
        back_requested: User clicked Back.
    """

    next_requested = pyqtSignal()
    back_requested = pyqtSignal()

    def __init__(self, state: WizardState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._worker: AnalysisWorker | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Title + subtitle
        title = QLabel("Pre-Transfer Analysis")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        root.addWidget(title)

        subtitle = QLabel(
            "Running a quick disk speed test on the destination drive and "
            "finalising the transfer plan.  This usually takes 5–10 seconds."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("hintLabel")
        subtitle.setStyleSheet("font-size: 12px;")
        root.addWidget(subtitle)

        # Status line (shown while running)
        self._status_lbl = QLabel("⏳  Measuring write speed…")
        self._status_lbl.setStyleSheet("color: #ff9800; font-size: 12px;")
        root.addWidget(self._status_lbl)

        # ── Stat cards ────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self._card_files = _StatCard("Files to Transfer", "—", "#ff9800")
        self._card_size  = _StatCard("Total Size", "—", "#4caf50",
                                     "amount of data to copy")
        self._card_speed = _StatCard("Write Speed", "—", "#2196f3",
                                     "measured on destination drive")
        self._card_time  = _StatCard("Estimated Time", "—", "#9c27b0")
        for card in (self._card_files, self._card_size,
                     self._card_speed, self._card_time):
            cards_row.addWidget(card)
        root.addLayout(cards_row)

        # ── Destination info ──────────────────────────────────────────
        self._dest_lbl = QLabel("")
        self._dest_lbl.setStyleSheet(
            "color: #888; font-size: 11px; padding: 4px 0;"
        )
        self._dest_lbl.setWordWrap(True)
        root.addWidget(self._dest_lbl)

        # ── Phase notice (shown only when phased) ─────────────────────
        self._phase_frame = QFrame()
        self._phase_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self._phase_frame.setStyleSheet(
            "background: #1e3a2e; border: 1px solid #4caf50; border-radius: 6px;"
        )
        self._phase_frame.hide()
        pf_lay = QVBoxLayout(self._phase_frame)
        pf_lay.setContentsMargins(14, 10, 14, 10)

        phase_title = QLabel("🔄  Phased Transfer")
        phase_title.setStyleSheet(
            "font-weight: bold; color: #4caf50; border: none;"
        )
        pf_lay.addWidget(phase_title)

        self._phase_detail = QLabel("")
        self._phase_detail.setWordWrap(True)
        self._phase_detail.setObjectName("hintLabel")
        self._phase_detail.setStyleSheet("font-size: 12px; border: none;")
        pf_lay.addWidget(self._phase_detail)

        self._phase_list_lbl = QLabel("")
        self._phase_list_lbl.setStyleSheet(
            "color: #aaa; font-size: 11px; font-family: monospace; border: none;"
        )
        self._phase_list_lbl.setWordWrap(True)
        pf_lay.addWidget(self._phase_list_lbl)
        root.addWidget(self._phase_frame)

        # ── What happens next ─────────────────────────────────────────
        self._next_info = QLabel("")
        self._next_info.setWordWrap(True)
        self._next_info.setStyleSheet(
            "color: #888; font-size: 11px; padding: 4px 0;"
        )
        self._next_info.hide()
        root.addWidget(self._next_info)

        root.addStretch()

        # ── Navigation ────────────────────────────────────────────────
        nav = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setObjectName("secondaryBtn")
        back_btn.setMinimumWidth(100)
        back_btn.clicked.connect(self.back_requested.emit)
        nav.addWidget(back_btn)
        nav.addStretch()
        self._start_btn = QPushButton("Start Transfer ▶")
        self._start_btn.setObjectName("accentBtn")
        self._start_btn.setMinimumWidth(170)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self.next_requested.emit)
        nav.addWidget(self._start_btn)
        root.addLayout(nav)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        self._start_btn.setEnabled(False)
        self._phase_frame.hide()
        self._next_info.hide()
        self._status_lbl.show()
        self._status_lbl.setText("⏳  Measuring write speed…")
        for card in (self._card_files, self._card_size,
                     self._card_speed, self._card_time):
            card.set_value("—")

        dest = self._state.destination_root
        if dest:
            from src.config.constants import ORG_MODE_LABELS
            mode_label = ORG_MODE_LABELS.get(self._state.org_mode, "").split("—")[0].strip()
            self._dest_lbl.setText(
                f"Destination:  {dest}   |   Organisation:  {mode_label}"
            )

        self._worker = AnalysisWorker(self._state)
        self._worker.analysis_complete.connect(self._on_analysis_complete)
        self._worker.start()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    @pyqtSlot(object)
    def _on_analysis_complete(self, plan) -> None:
        self._status_lbl.hide()

        self._card_files.set_value(f"{plan.total_files:,}")
        self._card_size.set_value(human_readable_size(plan.total_size_bytes))

        speed = plan.measured_speed_mbs
        speed_colour = "#4caf50" if speed >= 50 else "#ff9800" if speed >= 15 else "#f44336"
        speed_note = (
            "fast (SSD / USB 3)" if speed >= 100 else
            "normal (USB 2 / HDD)" if speed >= 30 else
            "slow — transfer may take longer"
        )
        self._card_speed.set_value(f"{speed:.0f} MB/s")
        self._card_speed._val.setStyleSheet(
            f"color: {speed_colour}; font-size: 20px; font-weight: bold; border: none;"
        )

        self._card_time.set_value(format_duration(plan.estimated_seconds))

        logger.info(
            "Pre-transfer analysis: %d files, %s, %.1f MB/s, est. %s",
            plan.total_files,
            human_readable_size(plan.total_size_bytes),
            speed,
            format_duration(plan.estimated_seconds),
        )

        if plan.is_phased:
            self._phase_frame.show()
            self._phase_detail.setText(
                f"This transfer is estimated to take {format_duration(plan.estimated_seconds)}, "
                f"so it will be automatically split into {plan.phase_count} phases "
                f"of roughly 45 minutes each.  After each phase you can verify the results "
                f"and continue at your own pace."
            )
            lines = "\n".join(
                f"  Phase {ph.phase_number}:  "
                f"{ph.folder_count} folders  ·  "
                f"{human_readable_size(ph.total_size_bytes)}  ·  "
                f"~{format_duration(ph.estimated_seconds)}"
                for ph in plan.phases
            )
            self._phase_list_lbl.setText(lines)
            next_text = (
                "The transfer will pause after each phase and notify you.  "
                "Click Start Transfer to begin Phase 1."
            )
        else:
            next_text = (
                f"All {plan.total_files:,} files will be copied in a single pass.  "
                "The source files are deleted only after a successful copy and size verification."
            )

        self._next_info.setText(next_text)
        self._next_info.show()
        self._start_btn.setEnabled(True)
