"""
Mediagator — Drive and folder scanner.

Walks user-selected folders for media files using os.scandir (much faster
than rglob) with batched signal emission and optional parallel root scanning
via a thread pool.

Author: Nathan
"""

import logging
import os
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import psutil
from PyQt6.QtCore import QThread, pyqtSignal

from src.config.constants import (
    MEDIA_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS,
    MEDIA_FOLDER_HINTS, SYSTEM_FOLDER_HINTS, C_DRIVE_SYSTEM_ROOTS,
)
from src.models.folder_node import FolderNode, FolderStatus
from src.models.scan_result import ScanResult, DriveInfo

logger = logging.getLogger(__name__)

# Emit a progress signal every N new media files found (reduces GUI overhead).
# Kept high so the GUI thread never gets flooded on large collections.
_PROGRESS_BATCH = 500


def enumerate_drives() -> list[DriveInfo]:
    """Return all eligible Windows drives as :class:`DriveInfo` objects.

    Returns:
        List of :class:`DriveInfo` instances sorted by drive letter.
    """
    drives: list[DriveInfo] = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for p in partitions:
            if "cdrom" in p.opts.lower() or p.fstype == "":
                continue
            if not p.mountpoint:
                continue
            try:
                usage = psutil.disk_usage(p.mountpoint)
            except PermissionError:
                continue
            letter = Path(p.mountpoint).drive.rstrip(":\\").upper()
            if not letter:
                continue
            label = p.device.rstrip("\\")
            drives.append(
                DriveInfo(
                    letter=letter,
                    label=label,
                    total_bytes=usage.total,
                    free_bytes=usage.free,
                    is_selected=True,
                )
            )
    except Exception as exc:
        logger.error("Drive enumeration failed: %s", exc)
    return sorted(drives, key=lambda d: d.letter)


def classify_folder(folder: Path) -> str:
    """Classify a folder as ``'media'``, ``'system'``, or ``'unknown'``.

    Args:
        folder: Folder path to classify.

    Returns:
        One of ``'media'``, ``'system'``, or ``'unknown'``.
    """
    name = folder.name.lower()
    is_drive_root_child = (folder.parent == Path(folder.drive + "\\"))

    if is_drive_root_child and folder.drive.upper().startswith("C"):
        if name in C_DRIVE_SYSTEM_ROOTS:
            return "system"

    if name in SYSTEM_FOLDER_HINTS:
        return "system"
    if name in MEDIA_FOLDER_HINTS:
        return "media"
    return "unknown"


def get_top_level_folders(drive_path: Path) -> list[tuple[Path, str]]:
    """List immediate child folders of a drive root with their classification.

    Args:
        drive_path: Drive root path (e.g. ``Path("D:\\")``).

    Returns:
        ``(folder_path, classification)`` tuples, media-first ordering.
    """
    results: list[tuple[Path, str]] = []
    try:
        with os.scandir(str(drive_path)) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    p = Path(entry.path)
                    results.append((p, classify_folder(p)))
    except PermissionError:
        pass
    except Exception as exc:
        logger.warning("Could not list folders on %s: %s", drive_path, exc)

    order = {"media": 0, "unknown": 1, "system": 2}
    results.sort(key=lambda t: (order.get(t[1], 1), t[0].name.lower()))
    return results


def get_subfolders(folder: Path) -> list[tuple[Path, str]]:
    """List immediate subfolders of any folder with their classification.

    Args:
        folder: Parent folder to list.

    Returns:
        ``(subfolder_path, classification)`` tuples sorted alphabetically.
    """
    results: list[tuple[Path, str]] = []
    try:
        with os.scandir(str(folder)) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False):
                    p = Path(entry.path)
                    results.append((p, classify_folder(p)))
    except PermissionError:
        pass
    except Exception as exc:
        logger.warning("Could not list subfolders of %s: %s", folder, exc)

    results.sort(key=lambda t: t[0].name.lower())
    return results


def _scan_one_root(
    root: Path,
    exclusions: set[str],
    cancel: threading.Event,
    progress_cb,          # callable(root_str, folder_str, delta_images, delta_videos, delta_bytes)
    extensions: set[str] | None = None,
) -> dict[Path, FolderNode]:
    """Scan a single root folder using os.scandir (non-recursive stack walk).

    Args:
        root: Root folder path.
        exclusions: Lowercase folder names to skip.
        cancel: Cancellation event.
        progress_cb: Callback for incremental progress updates.
        extensions: Allowed file extensions. Defaults to MEDIA_EXTENSIONS.

    Returns:
        Dict mapping folder path → :class:`FolderNode`.
    """
    allowed_exts = extensions if extensions else MEDIA_EXTENSIONS
    folder_map: dict[Path, FolderNode] = {}
    stack: deque[str] = deque([str(root)])
    batch_images = 0
    batch_videos = 0
    batch_bytes = 0
    current_folder = str(root)

    while stack and not cancel.is_set():
        dir_path = stack.pop()
        current_folder = dir_path

        try:
            with os.scandir(dir_path) as it:
                entries = list(it)
        except PermissionError:
            continue
        except Exception as exc:
            logger.warning("scandir error %s: %s", dir_path, exc)
            continue

        for entry in entries:
            if cancel.is_set():
                break
            if entry.is_dir(follow_symlinks=False):
                if entry.name.lower() not in exclusions:
                    stack.append(entry.path)
            elif entry.is_file(follow_symlinks=False):
                ext = os.path.splitext(entry.name)[1].lower()
                if ext not in allowed_exts:
                    continue
                parent = Path(dir_path)
                if parent not in folder_map:
                    folder_map[parent] = FolderNode(path=parent)
                node = folder_map[parent]
                node.file_count += 1
                try:
                    size = entry.stat().st_size
                    node.total_size_bytes += size
                    batch_bytes += size
                except OSError:
                    size = 0
                if ext in IMAGE_EXTENSIONS:
                    batch_images += 1
                elif ext in VIDEO_EXTENSIONS:
                    batch_videos += 1

                if (batch_images + batch_videos) >= _PROGRESS_BATCH:
                    progress_cb(str(root), current_folder, batch_images, batch_videos, batch_bytes)
                    batch_images = 0
                    batch_videos = 0
                    batch_bytes = 0

    # Flush remaining
    if batch_images + batch_videos > 0:
        progress_cb(str(root), current_folder, batch_images, batch_videos, batch_bytes)

    return folder_map


def _deduplicate_folders(folders: list[Path]) -> list[Path]:
    """Remove any path that is already covered by an ancestor in the list.

    If both ``E:\\Photos`` and ``E:\\Photos\\RAW`` are selected, scanning
    both would count RAW files twice because ``_scan_one_root`` recurses the
    full subtree.  This function keeps only the topmost (shortest) paths so
    every file is visited exactly once.

    Args:
        folders: Raw list of user-selected folder paths.

    Returns:
        Deduplicated list — no path is a descendant of another in the result.
    """
    resolved = sorted({p.resolve() for p in folders if p.exists()}, key=lambda p: len(p.parts))
    keep: list[Path] = []
    for candidate in resolved:
        if not any(
            candidate != ancestor and candidate.is_relative_to(ancestor)
            for ancestor in keep
        ):
            keep.append(candidate)
    return keep


class ScanWorker(QThread):
    """QThread worker that scans selected folders for media files.

    Uses os.scandir + batched emissions for speed.  Multiple root folders
    are scanned in parallel via a ThreadPoolExecutor.

    Overlapping paths are deduplicated before scanning so files are never
    counted more than once.

    Signals:
        progress_updated(str, str, int): root, current_folder, total_found.
        scan_complete(ScanResult): Emitted on successful completion.
        error_occurred(str): Non-fatal error message.
    """

    progress_updated = pyqtSignal(str, str, int)
    scan_complete = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        scan_folders: list[Path],
        exclusions: set[str],
        cancellation_event: threading.Event | None = None,
        extensions: set[str] | None = None,
    ) -> None:
        """Initialise the scan worker.

        Args:
            scan_folders: Explicit folders to scan recursively.
            exclusions: Lowercase folder names to always skip.
            cancellation_event: Optional shared event for clean cancel.
            extensions: Allowed file extensions. Defaults to MEDIA_EXTENSIONS.
        """
        super().__init__()
        deduped = _deduplicate_folders(scan_folders)
        dropped = len(scan_folders) - len(deduped)
        if dropped:
            logger.info(
                "Deduplication removed %d redundant path(s) from scan list "
                "(child paths already covered by a selected ancestor).",
                dropped,
            )
        self._scan_folders = deduped
        self._exclusions = {e.lower() for e in exclusions}
        self._cancel = cancellation_event or threading.Event()
        self._extensions = extensions or MEDIA_EXTENSIONS
        self._total_images = 0
        self._total_videos = 0
        self._total_bytes = 0
        self._lock = threading.Lock()

    def run(self) -> None:
        """Scan all selected folders in parallel and emit results."""
        import time as _time
        combined: dict[Path, FolderNode] = {}
        _last_emit = [0.0]          # mutable container so inner fn can write
        _EMIT_INTERVAL = 0.1        # seconds between GUI updates (~10 fps)

        def progress_cb(root: str, folder: str, di: int, dv: int, db: int) -> None:
            with self._lock:
                self._total_images += di
                self._total_videos += dv
                self._total_bytes += db
                total = self._total_images + self._total_videos
                now = _time.monotonic()
                if now - _last_emit[0] < _EMIT_INTERVAL:
                    return
                _last_emit[0] = now
            self.progress_updated.emit(root, folder, total)

        max_workers = min(len(self._scan_folders), 4)
        with ThreadPoolExecutor(max_workers=max(max_workers, 1)) as pool:
            futures = {
                pool.submit(
                    _scan_one_root,
                    folder,
                    self._exclusions,
                    self._cancel,
                    progress_cb,
                    self._extensions,
                ): folder
                for folder in self._scan_folders
                if folder.exists() and folder.is_dir()
            }
            for future in as_completed(futures):
                try:
                    result_map = future.result()
                    for path, node in result_map.items():
                        if path in combined:
                            combined[path].file_count += node.file_count
                            combined[path].total_size_bytes += node.total_size_bytes
                        else:
                            combined[path] = node
                except Exception as exc:
                    logger.error("Scan thread error: %s", exc)
                    self.error_occurred.emit(str(exc))

        result = ScanResult(
            drives_scanned=sorted({str(f.drive) for f in self._scan_folders}),
            folder_nodes=list(combined.values()),
            total_files=self._total_images + self._total_videos,
            total_size_bytes=self._total_bytes,
            image_count=self._total_images,
            video_count=self._total_videos,
        )
        result.top_folders = sorted(
            result.folder_nodes, key=lambda n: n.total_size_bytes, reverse=True
        )[:5]
        self.scan_complete.emit(result)
