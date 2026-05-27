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
from dataclasses import dataclass
from pathlib import Path

import psutil
from PyQt6.QtCore import pyqtSignal, QThread, pyqtSlot, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QGroupBox, QProgressBar, QButtonGroup,
    QRadioButton, QFrame, QScrollArea, QSizePolicy,
)

from src.gui.wizard_state import WizardState
from src.config.constants import OrgMode, ORG_MODE_LABELS
from src.utils.file_utils import human_readable_size
from src.core.hardware_profile import detect_hardware, HardwareProfile, _get_drive_type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background workers
# ---------------------------------------------------------------------------

class HardwareWorker(QThread):
    """Detect hardware profile in a background thread.

    Signals:
        hardware_ready(object): Emits the detected :class:`HardwareProfile`.
    """

    hardware_ready = pyqtSignal(object)

    def __init__(self, source_path: Path, dest_path: Path) -> None:
        super().__init__()
        self._source = source_path
        self._dest   = dest_path

    def run(self) -> None:
        profile = detect_hardware(self._source, self._dest)
        self.hardware_ready.emit(profile)

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
# Drive discovery
# ---------------------------------------------------------------------------

@dataclass
class _DriveData:
    """Detected info for one mounted drive."""
    root:       Path
    label:      str
    drive_type: str   # SSD / HDD / Unknown
    total_gb:   float
    free_gb:    float
    used_pct:   float


class DriveInfoWorker(QThread):
    """Enumerate all fixed drives and detect their type + free space.

    Signals:
        drives_ready(list): List of :class:`_DriveData` objects.
    """

    drives_ready = pyqtSignal(list)

    def run(self) -> None:
        results: list[_DriveData] = []
        try:
            for part in psutil.disk_partitions(all=False):
                # Skip optical / ram drives
                if "cdrom" in part.opts or part.fstype == "":
                    continue
                root = Path(part.mountpoint)
                try:
                    usage = psutil.disk_usage(str(root))
                except PermissionError:
                    continue
                total_gb = usage.total / (1024 ** 3)
                free_gb  = usage.free  / (1024 ** 3)
                used_pct = usage.percent

                # Drive label from Windows (e.g. "Local Disk (C:)")
                try:
                    import subprocess, json
                    ps = (
                        f"$d = Get-PSDrive -Name '{root.drive[0]}' -ErrorAction SilentlyContinue;"
                        f"if ($d) {{ $d.Description }} else {{ '' }}"
                    )
                    r = subprocess.run(
                        ["powershell", "-NoProfile", "-Command", ps],
                        capture_output=True, text=True, timeout=4
                    )
                    label = r.stdout.strip() or root.drive
                except Exception:
                    label = root.drive

                drive_type = _get_drive_type(root)
                results.append(_DriveData(
                    root=root, label=label, drive_type=drive_type,
                    total_gb=total_gb, free_gb=free_gb, used_pct=used_pct,
                ))
        except Exception as exc:
            logger.debug("DriveInfoWorker error: %s", exc)
        self.drives_ready.emit(results)


# ---------------------------------------------------------------------------
# Drive card widget
# ---------------------------------------------------------------------------

class _DriveCard(QFrame):
    """Informational card showing one drive's type, capacity, and free space."""

    def __init__(self, data: _DriveData, needed_bytes: int, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(185)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        has_space = data.free_gb * (1024 ** 3) >= needed_bytes
        self.setStyleSheet(
            "QFrame { background: #2a2a3e; border: 1px solid #3a3a5a; border-radius: 10px; }"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        # Drive root + type badge
        top = QHBoxLayout()
        root_lbl = QLabel(str(data.root.drive))
        root_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #fff; border: none;")
        top.addWidget(root_lbl)
        top.addStretch()

        type_colours = {"SSD": "#4caf50", "HDD": "#ff9800", "Unknown": "#666"}
        tc = type_colours.get(data.drive_type, "#666")
        type_lbl = QLabel(data.drive_type)
        type_lbl.setStyleSheet(
            f"color: {tc}; font-size: 10px; font-weight: bold; "
            f"background: transparent; border: 1px solid {tc}; "
            f"border-radius: 4px; padding: 1px 5px;"
        )
        top.addWidget(type_lbl)
        lay.addLayout(top)

        # Label / volume name
        if data.label and data.label != str(data.root.drive):
            name_lbl = QLabel(data.label)
            name_lbl.setStyleSheet("color: #aaa; font-size: 10px; border: none;")
            name_lbl.setWordWrap(True)
            lay.addWidget(name_lbl)

        # Mini usage bar
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(data.used_pct))
        bar.setTextVisible(False)
        bar.setFixedHeight(6)
        fill_colour = "#f44336" if data.used_pct > 85 else "#ff9800" if data.used_pct > 60 else "#4caf50"
        bar.setStyleSheet(f"""
            QProgressBar {{ background: #1a1a2e; border: none; border-radius: 3px; }}
            QProgressBar::chunk {{ background: {fill_colour}; border-radius: 3px; }}
        """)
        lay.addWidget(bar)

        # Capacity text
        space_text = f"{data.free_gb:.1f} GB free / {data.total_gb:.1f} GB"
        space_lbl = QLabel(space_text)
        space_lbl.setStyleSheet("color: #888; font-size: 10px; border: none;")
        lay.addWidget(space_lbl)

        # Enough space indicator
        if needed_bytes > 0:
            if has_space:
                ok_lbl = QLabel("✓ Enough space")
                ok_lbl.setStyleSheet("color: #4caf50; font-size: 10px; border: none;")
            else:
                ok_lbl = QLabel("✗ Not enough space")
                ok_lbl.setStyleSheet("color: #f44336; font-size: 10px; border: none;")
            lay.addWidget(ok_lbl)



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
    _MODE_IDS = [OrgMode.YEAR_MONTH, OrgMode.YEAR_ONLY, OrgMode.EVENT_YEAR, OrgMode.FILE_DATE, OrgMode.FLAT]

    def __init__(self, state: WizardState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._probe_worker: ProbeWorker | None = None
        self._hw_worker: HardwareWorker | None = None
        self._drive_worker: DriveInfoWorker | None = None
        self._detected_drives: list[_DriveData] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Outer layout: scrollable content + fixed nav bar at bottom
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Scrollable content area ────────────────────────────────────
        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        page_scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                width: 8px; background: #1a1a2e; border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #444466; border-radius: 4px; min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(12)
        page_scroll.setWidget(content)
        outer.addWidget(page_scroll, stretch=1)

        # ── Title ─────────────────────────────────────────────────────
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

        # ── Available Drives ──────────────────────────────────────────
        drives_group = QGroupBox("Available Drives")
        drives_outer = QVBoxLayout(drives_group)
        drives_outer.setSpacing(6)

        self._drives_hint = QLabel("Scanning available drives…")
        self._drives_hint.setStyleSheet("color: #888; font-size: 11px;")
        drives_outer.addWidget(self._drives_hint)

        cards_scroll = QScrollArea()
        cards_scroll.setWidgetResizable(True)
        cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cards_scroll.setFixedHeight(162)
        cards_scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:horizontal {
                height: 8px; background: #1a1a2e; border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #444466; border-radius: 4px; min-width: 30px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        """)

        self._cards_container = QWidget()
        self._cards_layout = QHBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(2, 2, 2, 2)
        self._cards_layout.setSpacing(10)
        self._cards_layout.addStretch()
        cards_scroll.setWidget(self._cards_container)
        drives_outer.addWidget(cards_scroll)
        layout.addWidget(drives_group)

        # ── Destination folder picker ──────────────────────────────────
        picker_group = QGroupBox("Destination Folder")
        picker_layout = QVBoxLayout(picker_group)
        picker_layout.setSpacing(6)

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

        # ── Organisation mode ──────────────────────────────────────────
        org_group = QGroupBox("Organisation Mode")
        org_layout = QVBoxLayout(org_group)
        org_layout.setSpacing(6)
        org_layout.setContentsMargins(10, 8, 10, 8)

        self._mode_group = QButtonGroup(self)
        modes = [
            (OrgMode.YEAR_MONTH,  "Year / Month  (recommended)",
             "dest \\ 2024 \\ 06-June \\ Folder Name"),
            (OrgMode.YEAR_ONLY,   "Year only",
             "dest \\ 2024 \\ Folder Name"),
            (OrgMode.EVENT_YEAR,  "Event under Year  — keeps your folder names",
             "dest \\ 2024 \\ Bali Trip"),
            (OrgMode.FILE_DATE,   "Flatten by Date  — re-sorts individual files by EXIF",
             "dest \\ 2024 \\ 06-June \\ photo.jpg"),
            (OrgMode.FLAT,        "No reorganisation — copy as-is",
             "dest \\ Folder Name"),
        ]
        for idx, (mode, label, example) in enumerate(modes):
            row = QHBoxLayout()
            row.setSpacing(10)
            radio = QRadioButton(label)
            radio.setStyleSheet("font-size: 13px; color: #e0e0e0;")
            self._mode_group.addButton(radio, idx)
            radio.toggled.connect(self._on_mode_changed)
            row.addWidget(radio)
            row.addStretch()
            ex_lbl = QLabel(example)
            ex_lbl.setStyleSheet(
                "color: #666; font-size: 11px; font-family: monospace;"
            )
            row.addWidget(ex_lbl)
            org_layout.addLayout(row)

        # Preview line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #333;")
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

        # ── Probe status ───────────────────────────────────────────────
        probe_group = QGroupBox("Resolving Destination Paths")
        probe_layout = QVBoxLayout(probe_group)
        probe_layout.setSpacing(4)

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

        # ── Fixed nav bar ──────────────────────────────────────────────
        nav_widget = QWidget()
        nav_widget.setObjectName("navBar")
        nav = QHBoxLayout(nav_widget)
        nav.setContentsMargins(24, 10, 24, 10)
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
        outer.addWidget(nav_widget)

        # Restore previous mode (if any) without triggering a probe
        self._apply_initial_mode()
        self._refresh_preview()
        self._update_next_btn()


    def _apply_initial_mode(self) -> None:
        """Restore a previously saved org_mode — does nothing if none was chosen."""
        mode = self._state.org_mode
        if mode not in self._MODE_IDS:
            # No previous choice — leave all radio buttons unchecked
            self._mode_group.setExclusive(False)
            for btn in self._mode_group.buttons():
                btn.setChecked(False)
            self._mode_group.setExclusive(True)
            return
        idx = self._MODE_IDS.index(mode)
        btn = self._mode_group.button(idx)
        if btn:
            btn.setChecked(True)

    def _update_next_btn(self) -> None:
        """Enable Next only when destination AND org mode are both chosen."""
        dest_ok = bool(self._state.destination_root)
        mode_ok = self._state.org_mode in self._MODE_IDS
        probe_done = not (self._probe_worker and self._probe_worker.isRunning())
        self._next_btn.setEnabled(dest_ok and mode_ok and probe_done)

    def _refresh_preview(self) -> None:
        """Update the live path preview label with a native Windows path."""
        mode = self._state.org_mode
        if mode not in self._MODE_IDS:
            self._preview_label.setText("← Select an organisation mode to see a preview")
            self._preview_label.setStyleSheet("color: #888; font-size: 11px; font-style: italic;")
            return
        root = self._state.destination_root or Path("dest")
        if mode == OrgMode.YEAR_MONTH:
            preview = root / "2024" / "06-June" / "My Vacation"
        elif mode == OrgMode.YEAR_ONLY:
            preview = root / "2024" / "My Vacation"
        elif mode == OrgMode.EVENT_YEAR:
            preview = root / "2024" / "Bali Trip"
        elif mode == OrgMode.FILE_DATE:
            preview = root / "2024" / "06-June" / "IMG_4821.jpg"
        else:  # FLAT
            preview = root / "My Vacation"
        self._preview_label.setText(str(preview))
        self._preview_label.setStyleSheet("color: #e0e0e0; font-size: 11px; font-style: normal;")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_mode_changed(self) -> None:
        idx = self._mode_group.checkedId()
        if 0 <= idx < len(self._MODE_IDS):
            self._state.org_mode = self._MODE_IDS[idx]
        self._refresh_preview()
        self._update_next_btn()
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
        self._start_hardware_detection(path)

    @staticmethod
    def _stop_worker(worker) -> None:
        """Gracefully stop a QThread worker if it is still running."""
        if worker is not None and worker.isRunning():
            worker.quit()
            worker.wait(3000)   # wait up to 3 s before giving up

    def _start_hardware_detection(self, dest_path: Path) -> None:
        """Kick off hardware detection in the background."""
        self._stop_worker(self._hw_worker)
        source_roots = self._state.selected_scan_folders
        source_hint = source_roots[0] if source_roots else dest_path
        self._hw_worker = HardwareWorker(source_hint, dest_path)
        self._hw_worker.hardware_ready.connect(self._on_hardware_ready)
        self._hw_worker.start()

    @pyqtSlot(object)
    def _on_hardware_ready(self, profile: HardwareProfile) -> None:
        self._state.hardware_profile = profile
        logger.info(
            "Hardware detected: src=%s dest=%s workers=%d buffer=%dMB",
            profile.source_drive_type, profile.dest_drive_type,
            profile.optimal_workers, profile.optimal_buffer_mb,
        )

    def _start_drive_scan(self) -> None:
        """Enumerate all drives in the background and populate the cards panel."""
        self._stop_worker(self._drive_worker)
        self._drive_worker = DriveInfoWorker()
        self._drive_worker.drives_ready.connect(self._on_drives_ready)
        self._drive_worker.start()

    @pyqtSlot(list)
    def _on_drives_ready(self, drives: list) -> None:
        """Rebuild the drive card row from detected drives."""
        self._detected_drives = drives

        # Clear existing cards (keep trailing stretch)
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        needed = (
            self._state.scan_result.total_size_bytes
            if self._state.scan_result else 0
        )

        # Sort: enough space first, then by free space descending
        sorted_drives = sorted(
            drives,
            key=lambda d: (d.free_gb * (1024 ** 3) < needed, -d.free_gb),
        )

        # Exclude drives that are pure source drives
        source_roots = {
            Path(p.drive + "\\") for p in self._state.selected_scan_folders
        }

        shown = 0
        for d in sorted_drives:
            card = _DriveCard(d, needed)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
            shown += 1

        if shown == 0:
            self._drives_hint.setText("No drives detected.")
        else:
            src_note = " (source drives shown for reference)" if source_roots else ""
            self._drives_hint.setText(
                f"{shown} drive(s) detected{src_note} — click one to select it as destination."
            )

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
        self._stop_worker(self._probe_worker)
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
        mode_label = ORG_MODE_LABELS.get(self._state.org_mode, "").split("—")[0].strip()
        self._probe_status.setText(
            f"✓ {count} folders resolved"
            + (f"  —  organised by {mode_label}" if mode_label else "")
        )
        self._update_next_btn()
        logger.info("Probe complete — mode=%s, folders=%d", self._state.org_mode, count)

    def _on_next(self) -> None:
        if self._state.destination_root:
            self.next_requested.emit()

    def cleanup(self) -> None:
        """Stop all background workers — call before hiding or resetting the step."""
        self._stop_worker(self._probe_worker)
        self._stop_worker(self._hw_worker)
        self._stop_worker(self._drive_worker)

    def hideEvent(self, event) -> None:
        """Stop workers when the step is navigated away from."""
        self.cleanup()
        super().hideEvent(event)

    def refresh(self) -> None:
        if self._state.destination_root:
            self._path_edit.setText(str(self._state.destination_root))
            self._update_space_label(self._state.destination_root)
        self._apply_initial_mode()
        self._refresh_preview()
        self._update_next_btn()
        # Always refresh drive cards so free-space indicators are current
        self._start_drive_scan()
