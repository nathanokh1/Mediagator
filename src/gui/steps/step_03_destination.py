"""
MediaMitigator — Step 3: Destination Folder.

User picks a destination and chooses one of three organisation modes.
A background probe scan resolves destination paths for all source folders.

Organisation modes
------------------
YEAR_MONTH  (default)   dest/2024/06-June/Folder Name/
YEAR_ONLY               dest/2024/Folder Name/
FLAT                    dest/Folder Name/   (no reorganisation)

Author: Nathan
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QGroupBox, QProgressBar, QButtonGroup,
    QRadioButton, QFrame,
)
from PyQt6.QtCore import pyqtSignal, QThread, pyqtSlot, Qt

from src.gui.wizard_state import WizardState
from src.config.constants import OrgMode, ORG_MODE_LABELS
from src.utils.file_utils import human_readable_size

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------

class ProbeWorker(QThread):
    """Resolves destination paths for all folder nodes in the background.

    Uses a fast sampled date resolver (10 files per folder, piexif only)
    Thread count scales with the number of folders (10 %, floor 4, ceil 16)
    so small jobs don't over-thread and large jobs saturate I/O safely.
    16 threads is a practical ceiling before HDD seek-time starts to hurt.

    Signals:
        probe_progress(int, int): (folders_done, folders_total)
        probe_complete: Emitted when all paths are resolved.
    """

    # Thread-count tuning constants
    _WORKER_PCT  = 0.10   # 10 % of folder count
    _WORKER_MIN  = 4      # always use at least this many threads
    _WORKER_MAX  = 16     # cap — beyond this HDD seek-time dominates

    probe_progress = pyqtSignal(int, int)
    probe_complete = pyqtSignal()

    def __init__(self, state: WizardState) -> None:
        super().__init__()
        self._state = state

    def run(self) -> None:
        from src.core.date_resolver import resolve_folder_dates_fast
        from src.core.analyzer import resolve_destination
        from src.models.folder_node import FolderStatus

        if not self._state.scan_result or not self._state.destination_root:
            self.probe_complete.emit()
            return

        nodes = self._state.scan_result.folder_nodes
        total = len(nodes)
        org_mode = self._state.org_mode
        dest_root = self._state.destination_root
        done_count = [0]          # mutable for closure
        lock = threading.Lock()

        def _resolve_one(node):
            year, month, multi_year = resolve_folder_dates_fast(node.path)
            node.majority_year = year
            node.majority_month = month
            if multi_year:
                node.status = FolderStatus.MULTI_YEAR
            node.destination_path = resolve_destination(node, dest_root, org_mode)
            with lock:
                done_count[0] += 1
                self.probe_progress.emit(done_count[0], total)

        max_workers = int(max(
            self._WORKER_MIN,
            min(self._WORKER_MAX, total * self._WORKER_PCT),
        ))
        logger.info("Probe: %d folders, %d worker threads", total, max_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_resolve_one, node) for node in nodes]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as exc:
                    logger.debug("Probe node error: %s", exc)

        self.probe_complete.emit()


# ---------------------------------------------------------------------------
# Step widget
# ---------------------------------------------------------------------------

class DestinationStep(QWidget):
    """Step 3 — destination folder picker with org mode selector.

    Signals:
        next_requested: User clicked Next.
        back_requested: User clicked Back.
    """

    next_requested = pyqtSignal()
    back_requested = pyqtSignal()

    # Maps radio button id → OrgMode constant
    _MODE_IDS = [OrgMode.YEAR_MONTH, OrgMode.YEAR_ONLY, OrgMode.FLAT]

    def __init__(self, state: WizardState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._probe_worker: ProbeWorker | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("Choose Destination Folder")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Select where transferred media will be saved, "
            "then choose how you want the files organised."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #aaa;")
        layout.addWidget(subtitle)

        # ── Folder picker ─────────────────────────────────────────────
        picker_group = QGroupBox("Destination Folder")
        picker_layout = QVBoxLayout(picker_group)

        path_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Choose a destination folder…")
        self._path_edit.setReadOnly(True)
        path_row.addWidget(self._path_edit)

        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(browse_btn)

        new_folder_btn = QPushButton("New Folder")
        new_folder_btn.clicked.connect(self._new_folder)
        path_row.addWidget(new_folder_btn)
        picker_layout.addLayout(path_row)

        self._space_label = QLabel("")
        self._space_label.setTextFormat(Qt.TextFormat.RichText)
        picker_layout.addWidget(self._space_label)
        layout.addWidget(picker_group)

        # ── Organisation mode ─────────────────────────────────────────
        org_group = QGroupBox("Organisation Mode")
        org_layout = QVBoxLayout(org_group)
        org_layout.setSpacing(10)

        self._mode_group = QButtonGroup(self)
        descriptions = {
            OrgMode.YEAR_MONTH: (
                "Organise by Year › Month  (recommended)",
                "Folders are placed in <b>dest / 2024 / 06-June / Folder Name</b>.<br>"
                "Great for large collections — easy to browse by date.",
            ),
            OrgMode.YEAR_ONLY: (
                "Organise by Year only",
                "Folders are placed in <b>dest / 2024 / Folder Name</b>.<br>"
                "Matches an existing year-based folder structure.",
            ),
            OrgMode.FLAT: (
                "No reorganisation  —  copy as-is",
                "Folders land directly at <b>dest / Folder Name</b>.<br>"
                "Original folder names are preserved; no date hierarchy is added.",
            ),
        }

        for idx, mode in enumerate(self._MODE_IDS):
            radio_label, detail_text = descriptions[mode]
            row_widget = self._make_mode_row(idx, mode, radio_label, detail_text)
            org_layout.addWidget(row_widget)

        # Live path preview
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("border: 1px solid #333;")
        org_layout.addWidget(sep)

        preview_row = QHBoxLayout()
        preview_lbl = QLabel("Preview:")
        preview_lbl.setStyleSheet("color: #888; font-size: 11px;")
        preview_lbl.setFixedWidth(56)
        self._preview_label = QLabel()
        self._preview_label.setStyleSheet(
            "color: #ffb74d; font-family: monospace; font-size: 12px;"
        )
        preview_row.addWidget(preview_lbl)
        preview_row.addWidget(self._preview_label, stretch=1)
        org_layout.addLayout(preview_row)

        layout.addWidget(org_group)

        # ── Probe status ──────────────────────────────────────────────
        probe_group = QGroupBox("Resolving Destination Paths")
        probe_layout = QVBoxLayout(probe_group)

        self._probe_bar = QProgressBar()
        self._probe_bar.setRange(0, 100)
        self._probe_bar.setValue(0)
        self._probe_bar.setFixedHeight(10)
        self._probe_bar.hide()
        probe_layout.addWidget(self._probe_bar)

        self._probe_status = QLabel("Waiting for destination selection.")
        self._probe_status.setStyleSheet("color: #aaa; font-size: 11px;")
        probe_layout.addWidget(self._probe_status)
        layout.addWidget(probe_group)

        layout.addStretch()

        # ── Navigation ────────────────────────────────────────────────
        nav = QHBoxLayout()
        self._back_btn = QPushButton("← Back")
        self._back_btn.setObjectName("secondaryBtn")
        self._back_btn.setMinimumWidth(100)
        self._back_btn.clicked.connect(self.back_requested.emit)
        nav.addWidget(self._back_btn)
        nav.addStretch()
        self._next_btn = QPushButton("Next →")
        self._next_btn.setObjectName("primaryBtn")
        self._next_btn.setMinimumWidth(130)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self._on_next)
        nav.addWidget(self._next_btn)
        layout.addLayout(nav)

        # Initialise selection
        self._apply_initial_mode()
        self._refresh_preview()

    def _make_mode_row(
        self, idx: int, mode: str, radio_label: str, detail_text: str
    ) -> QWidget:
        """Build one radio button row with icon, title, and detail text."""
        container = QWidget()
        container.setStyleSheet(
            "QWidget { border: 1px solid #2a2a3e; border-radius: 6px; padding: 4px; }"
        )
        row = QHBoxLayout(container)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(12)

        radio = QRadioButton()
        radio.setStyleSheet("QRadioButton::indicator { width: 16px; height: 16px; }")
        self._mode_group.addButton(radio, idx)
        radio.toggled.connect(self._on_mode_changed)
        row.addWidget(radio)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title_lbl = QLabel(radio_label)
        title_lbl.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #e0e0e0; border: none;"
        )
        text_col.addWidget(title_lbl)

        detail_lbl = QLabel(detail_text)
        detail_lbl.setWordWrap(True)
        detail_lbl.setTextFormat(Qt.TextFormat.RichText)
        detail_lbl.setStyleSheet("color: #888; font-size: 11px; border: none;")
        text_col.addWidget(detail_lbl)

        row.addLayout(text_col, stretch=1)
        return container

    def _apply_initial_mode(self) -> None:
        """Set the radio selection from the current WizardState org_mode."""
        mode = self._state.org_mode
        idx = self._MODE_IDS.index(mode) if mode in self._MODE_IDS else 0
        btn = self._mode_group.button(idx)
        if btn:
            btn.setChecked(True)

    def _refresh_preview(self) -> None:
        """Update the live path preview label with a native Windows path."""
        root = self._state.destination_root or Path("dest")
        mode = self._state.org_mode
        if mode == OrgMode.YEAR_MONTH:
            preview = root / "2024" / "06-June" / "My Vacation"
        elif mode == OrgMode.YEAR_ONLY:
            preview = root / "2024" / "My Vacation"
        else:
            preview = root / "My Vacation"
        self._preview_label.setText(str(preview))

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_mode_changed(self) -> None:
        idx = self._mode_group.checkedId()
        if 0 <= idx < len(self._MODE_IDS):
            self._state.org_mode = self._MODE_IDS[idx]
        self._refresh_preview()
        # Re-run probe if destination already chosen
        if self._state.destination_root and self._state.scan_result:
            self._start_probe()

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self._set_destination(Path(folder))

    def _new_folder(self) -> None:
        parent = QFileDialog.getExistingDirectory(self, "Select Parent for New Folder")
        if not parent:
            return
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            new_path = Path(parent) / name.strip()
            new_path.mkdir(parents=True, exist_ok=True)
            self._set_destination(new_path)

    def _set_destination(self, path: Path) -> None:
        self._state.destination_root = path
        self._path_edit.setText(str(path))
        self._update_space_label(path)
        self._refresh_preview()
        self._start_probe()

    def _update_space_label(self, path: Path) -> None:
        try:
            usage = psutil.disk_usage(str(path))
            needed = self._state.scan_result.total_size_bytes if self._state.scan_result else 0
            free_str = human_readable_size(usage.free)
            needed_str = human_readable_size(needed)
            ok = usage.free >= needed
            color = "#4caf50" if ok else "#f44336"
            status = "✓ Enough space" if ok else "✗ Not enough space"
            self._space_label.setText(
                f"Free: {free_str}  |  Needed: {needed_str}  |  "
                f"<span style='color:{color}'>{status}</span>"
            )
        except Exception as exc:
            self._space_label.setText(f"Could not read disk info: {exc}")

    def _start_probe(self) -> None:
        total = len(self._state.scan_result.folder_nodes) if self._state.scan_result else 0
        self._probe_bar.setRange(0, max(total, 1))
        self._probe_bar.setValue(0)
        self._probe_bar.show()
        self._probe_status.setText(f"Reading dates for 0 / {total} folders…")
        self._next_btn.setEnabled(False)
        self._probe_worker = ProbeWorker(self._state)
        self._probe_worker.probe_progress.connect(self._on_probe_progress)
        self._probe_worker.probe_complete.connect(self._on_probe_complete)
        self._probe_worker.start()

    @pyqtSlot(int, int)
    def _on_probe_progress(self, done: int, total: int) -> None:
        self._probe_bar.setValue(done)
        self._probe_status.setText(f"Reading dates…  {done} / {total} folders")

    @pyqtSlot()
    def _on_probe_complete(self) -> None:
        self._probe_bar.hide()
        count = len(self._state.scan_result.folder_nodes) if self._state.scan_result else 0
        self._probe_status.setText(
            f"✓ {count} folders resolved  —  "
            f"files will be organised by {ORG_MODE_LABELS.get(self._state.org_mode, '').split('—')[0].strip()}"
        )
        self._next_btn.setEnabled(True)
        logger.info("Probe complete — mode=%s, folders=%d", self._state.org_mode, count)

    def _on_next(self) -> None:
        if self._state.destination_root:
            self.next_requested.emit()

    def refresh(self) -> None:
        if self._state.destination_root:
            self._path_edit.setText(str(self._state.destination_root))
            self._update_space_label(self._state.destination_root)
        self._apply_initial_mode()
        self._refresh_preview()
