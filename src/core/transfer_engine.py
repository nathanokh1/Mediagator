"""
MediaMitigator — Transfer engine.

Executes the copy-verify-delete transfer for all phases, emitting
progress signals for the GUI.  Runs inside a QThread.

Author: Nathan
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from src.config.constants import DUPLICATE_FOLDER_NAME, MEDIA_EXTENSIONS, ConflictBehavior
from src.core.duplicate_detector import is_duplicate
from src.core.hardware_profile import HardwareProfile
from src.models.folder_node import FolderNode, FolderStatus
from src.models.transfer_plan import TransferPlan
from src.models.transfer_phase import TransferPhase, PhaseStatus
from src.utils.file_utils import safe_copy, safe_delete, delete_empty_folder, next_available_path
from src.utils.logger import log_operation

logger = logging.getLogger(__name__)


@dataclass
class TransferStats:
    """Mutable statistics accumulator for the active transfer.

    Attributes:
        files_completed: Successfully transferred file count.
        files_remaining: Files yet to be processed.
        bytes_transferred: Bytes successfully transferred.
        current_speed_mbs: Recent average speed in MB/s.
        elapsed_seconds: Seconds since transfer started.
        duplicates: Paths routed to the duplicates folder.
        renamed_files: (source, dest) pairs for renamed files.
        errors: (source, error_message) pairs.
        flagged_items: (timestamp, source, issue_type, action) tuples.
        lightroom_paths: Destination folder paths for Lightroom report.
    """
    files_completed: int = 0
    files_remaining: int = 0
    bytes_transferred: int = 0
    current_speed_mbs: float = 0.0
    elapsed_seconds: float = 0.0
    duplicates: list[Path] = field(default_factory=list)
    renamed_files: list[tuple[Path, Path]] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)
    flagged_items: list[tuple[str, Path, str, str]] = field(default_factory=list)
    lightroom_paths: list[Path] = field(default_factory=list)


class TransferWorker(QThread):
    """QThread worker that executes the full transfer plan.

    Signals:
        progress_updated(int, int, float, float, str, str):
            (files_done, files_total, bytes_done, speed_mbs, src_path, dst_path)
        item_completed(str, str, str):
            (source_path, dest_path, result)  — SUCCESS / DUPLICATE / RENAMED / ERROR
        error_occurred(str, str, str):
            (timestamp, source_path, issue)
        phase_completed(int, int):
            (phase_number, total_phases)
        transfer_complete(object):
            Emits the final :class:`TransferStats`.
    """

    progress_updated = pyqtSignal(int, int, float, float, str, str)
    item_completed = pyqtSignal(str, str, str)
    error_occurred = pyqtSignal(str, str, str)
    phase_completed = pyqtSignal(int, int)
    transfer_complete = pyqtSignal(object)

    def __init__(
        self,
        plan: TransferPlan,
        settings: dict[str, Any],
        transfer_logger: logging.Logger,
        cancellation_event: threading.Event | None = None,
        hardware_profile: HardwareProfile | None = None,
        skip_paths: set[str] | None = None,
    ) -> None:
        """Initialise the transfer worker.

        Args:
            plan: Fully built :class:`TransferPlan`.
            settings: User settings dict (empty_folder_behavior, etc.).
            transfer_logger: Per-session file logger.
            cancellation_event: Optional shared event for clean stop.
            hardware_profile: Detected hardware config for adaptive settings.
            skip_paths: Optional set of source path strings already
                transferred; these files will be counted but not re-copied,
                enabling in-session resume after a cancellation.
        """
        super().__init__()
        self._plan = plan
        self._settings = settings
        self._transfer_logger = transfer_logger
        self._cancel = cancellation_event or threading.Event()
        self._skip_paths: set[str] = skip_paths or set()

        # Adjust totals to account for files already done
        already_done = sum(
            1 for phase in plan.phases
            for folder in phase.folders
            for f in folder.source_files
            if str(f) in self._skip_paths
        )
        self._stats = TransferStats(
            files_completed=already_done,
            files_remaining=max(0, plan.total_files - already_done),
        )
        self._last_progress_emit = 0.0
        self._progress_lock = threading.Lock()

        # Adaptive settings — use hardware profile if available, else defaults
        if hardware_profile:
            self._folder_workers = hardware_profile.optimal_workers
            self._copy_buffer    = hardware_profile.optimal_buffer_mb * 1024 * 1024
            logger.info(
                "Transfer engine: using hardware-tuned settings — "
                "workers=%d buffer=%dMB (src=%s dst=%s)",
                self._folder_workers,
                hardware_profile.optimal_buffer_mb,
                hardware_profile.source_drive_type,
                hardware_profile.dest_drive_type,
            )
        else:
            self._folder_workers = self._FOLDER_WORKERS
            self._copy_buffer    = 16 * 1024 * 1024  # 16 MB default

    def run(self) -> None:
        """Execute all phases sequentially."""
        start_time = time.monotonic()
        total_phases = len(self._plan.phases)

        for phase in self._plan.phases:
            if self._cancel.is_set():
                break
            phase.status = PhaseStatus.RUNNING
            self._execute_phase(phase, start_time)
            if not self._cancel.is_set():
                phase.status = PhaseStatus.COMPLETED
                self.phase_completed.emit(phase.phase_number, total_phases)

        self._stats.elapsed_seconds = time.monotonic() - start_time
        self.transfer_complete.emit(self._stats)

    # Number of folders processed concurrently within a phase.
    # 3 workers: source-read, in-flight copy, and destination-write can all
    # overlap.  Good balance for HDD→SSD transfers without thrashing the source.
    _FOLDER_WORKERS = 3

    # Minimum seconds between GUI progress_updated signals.
    # Firing once per file at 7000 files/run = 7000 signal dispatches;
    # throttling to 100 ms intervals cuts that to ~60 updates/minute.
    _PROGRESS_INTERVAL = 0.1

    def _execute_phase(self, phase: TransferPhase, start_time: float) -> None:
        """Transfer all folders in a single phase using parallel folder workers.

        Two folders are processed concurrently so source reads and destination
        writes can overlap.  The cancel event is checked before each folder.

        Args:
            phase: The phase to execute.
            start_time: Monotonic start time for elapsed calculation.
        """
        with ThreadPoolExecutor(max_workers=self._folder_workers) as pool:
            futures = {
                pool.submit(self._transfer_folder, node, start_time): node
                for node in phase.folder_nodes
            }
            for future in as_completed(futures):
                if self._cancel.is_set():
                    pool.shutdown(wait=False, cancel_futures=True)
                    break
                try:
                    future.result()
                except Exception as exc:
                    node = futures[future]
                    logger.error("Folder transfer error %s: %s", node.path, exc)

    def _transfer_folder(self, node: FolderNode, start_time: float) -> None:
        """Copy all media files from *node* to its resolved destination.

        Files are sorted by extension so same-type files are read sequentially
        from the source disk, minimising HDD seek time.

        Args:
            node: Source folder node with a resolved destination_path.
            start_time: Monotonic start time for speed calculation.
        """
        if node.destination_path is None:
            logger.warning("No destination path for %s — skipped.", node.path)
            return

        dest_folder = node.destination_path

        # Sort by (extension, name) — groups all CR2s together, then JPEGs, etc.
        # Sequential reads of the same file type are much faster on spinning disks.
        files_to_transfer = sorted(
            (
                f for f in node.path.iterdir()
                if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS
            ),
            key=lambda f: (f.suffix.lower(), f.name.lower()),
        )

        for src_file in files_to_transfer:
            if self._cancel.is_set():
                return

            dest_file = dest_folder / src_file.name
            self._transfer_file(src_file, dest_file, start_time)

        # Apply empty-folder behavior
        if not self._cancel.is_set():
            self._handle_empty_folder(node)
            node.status = FolderStatus.COMPLETED
            if dest_folder not in self._stats.lightroom_paths:
                self._stats.lightroom_paths.append(dest_folder)

    def _transfer_file(
        self, src: Path, dest: Path, start_time: float
    ) -> None:
        """Copy, verify, and delete a single file.

        Args:
            src: Source file path.
            dest: Intended destination file path.
            start_time: Monotonic start time for speed computation.
        """
        # Skip files already transferred (in-session resume)
        if str(src) in self._skip_paths:
            self.item_completed.emit(str(src), str(dest), "SKIPPED")
            return

        total = self._plan.total_files
        done = self._stats.files_completed

        conflict_mode = self._settings.get("conflict_behavior", ConflictBehavior.RENAME)

        # Duplicate check against existing destination
        if dest.exists():
            dup, method = is_duplicate(src, dest)
            if dup:
                dup_dest = (
                    self._plan.destination_root
                    / DUPLICATE_FOLDER_NAME
                    / src.parent.name
                    / src.name
                )
                dup_dest.parent.mkdir(parents=True, exist_ok=True)
                if safe_copy(src, dup_dest, buffer=self._copy_buffer):
                    deleted = safe_delete(src)
                    if not deleted:
                        ts = time.strftime("%H:%M:%S")
                        self._stats.flagged_items.append(
                            (ts, src, "DELETE_FAILED", "SOURCE_KEPT")
                        )
                        log_operation(
                            self._transfer_logger, logging.WARNING,
                            "DUPLICATE", src, dup_dest, src.stat().st_size,
                            "COPY_OK_DELETE_FAILED", "source may be read-only",
                        )
                    self._stats.duplicates.append(src)
                    self._stats.files_completed += 1
                    self._stats.files_remaining -= 1
                    log_operation(
                        self._transfer_logger, logging.WARNING,
                        "DUPLICATE", src, dup_dest, src.stat().st_size,
                        "FLAGGED", method,
                    )
                    self.item_completed.emit(str(src), str(dup_dest), "DUPLICATE")
                    self._emit_progress(src, dup_dest, start_time)
                return

            # Not a true duplicate — apply conflict_behavior
            if conflict_mode == ConflictBehavior.SKIP:
                self._stats.files_completed += 1
                self._stats.files_remaining -= 1
                log_operation(
                    self._transfer_logger, logging.INFO,
                    "SKIP", src, dest, src.stat().st_size, "SKIPPED", "file exists at dest",
                )
                self.item_completed.emit(str(src), str(dest), "SKIPPED")
                self._emit_progress(src, dest, start_time)
                return
            elif conflict_mode == ConflictBehavior.OVERWRITE:
                log_operation(
                    self._transfer_logger, logging.WARNING,
                    "OVERWRITE", src, dest, src.stat().st_size, "OVERWRITING", "",
                )
                # dest.exists() — we proceed to copy below; safe_copy will overwrite
            else:
                # Default: RENAME
                dest = next_available_path(dest)
                self._stats.renamed_files.append((src, dest))
                log_operation(
                    self._transfer_logger, logging.WARNING,
                    "RENAME", src, dest, src.stat().st_size, "RENAMED", "",
                )

        size = src.stat().st_size
        if safe_copy(src, dest, buffer=self._copy_buffer):
            deleted = safe_delete(src)
            self._stats.files_completed += 1
            self._stats.files_remaining -= 1
            self._stats.bytes_transferred += size

            if deleted:
                log_operation(
                    self._transfer_logger, logging.INFO,
                    "MOVE", src, dest, size, "SUCCESS",
                )
                self.item_completed.emit(str(src), str(dest), "SUCCESS")
            else:
                # Copy succeeded but source could not be removed.
                # Log and flag so the report lists these files.
                ts = time.strftime("%H:%M:%S")
                self._stats.errors.append((src, "Copied but source not deleted — check read-only attribute"))
                self._stats.flagged_items.append((ts, src, "DELETE_FAILED", "SOURCE_KEPT"))
                log_operation(
                    self._transfer_logger, logging.WARNING,
                    "MOVE", src, dest, size, "COPY_OK_DELETE_FAILED",
                    "file may be read-only or locked",
                )
                self.error_occurred.emit(ts, str(src), "Copied OK but source not deleted")
                self.item_completed.emit(str(src), str(dest), "SUCCESS")
        else:
            ts = time.strftime("%H:%M:%S")
            self._stats.errors.append((src, "Copy/verify failed"))
            self._stats.flagged_items.append((ts, src, "COPY_FAILED", "SKIPPED"))
            log_operation(
                self._transfer_logger, logging.ERROR,
                "COPY", src, dest, size, "ERROR", "size mismatch or exception",
            )
            self.error_occurred.emit(ts, str(src), "Copy/verify failed")

        self._emit_progress(src, dest, start_time)

    def _emit_progress(self, src: Path, dest: Path, start_time: float) -> None:
        """Compute current speed and emit a rate-limited progress update signal.

        Signals are throttled to at most one every ``_PROGRESS_INTERVAL`` seconds
        so thousands of small files don't flood the GUI event queue.  Stats are
        always updated even when the signal is suppressed.

        Args:
            src: Source file for label display.
            dest: Destination file for label display.
            start_time: Monotonic transfer start time.
        """
        now = time.monotonic()
        elapsed = max(now - start_time, 0.001)
        speed_mbs = (self._stats.bytes_transferred / (1024 * 1024)) / elapsed
        self._stats.current_speed_mbs = speed_mbs

        with self._progress_lock:
            if now - self._last_progress_emit < self._PROGRESS_INTERVAL:
                return
            self._last_progress_emit = now

        self.progress_updated.emit(
            self._stats.files_completed,
            self._plan.total_files,
            float(self._stats.bytes_transferred),
            speed_mbs,
            str(src),
            str(dest),
        )

    def _handle_empty_folder(self, node: FolderNode) -> None:
        """Apply the empty-folder behavior setting after a folder transfer.

        Args:
            node: The folder node that was just transferred.
        """
        behavior = self._settings.get("empty_folder_behavior", "flag")
        if behavior == "delete":
            deleted = delete_empty_folder(node.path)
            if deleted:
                log_operation(
                    self._transfer_logger, logging.INFO,
                    "DELETE_EMPTY", node.path, None, None, "DELETED",
                )
        elif behavior == "flag":
            log_operation(
                self._transfer_logger, logging.INFO,
                "EMPTY_FOLDER", node.path, None, None, "FLAGGED",
            )
