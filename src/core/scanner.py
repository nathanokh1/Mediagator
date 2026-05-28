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
import time as _time_mod
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


# ---------------------------------------------------------------------------
# Analysis data accumulator (collected during scan, zero extra I/O)
# ---------------------------------------------------------------------------

# Stale age thresholds in seconds
_STALE_THRESHOLDS: dict[str, float] = {
    "3m+": 90 * 86400,
    "6m+": 180 * 86400,
    "1y+": 365 * 86400,
    "2y+": 730 * 86400,
}


@dataclass
class _AnalysisAccum:
    """Mutable accumulator for per-root analysis data."""
    ext_stats:    dict[str, list[int]] = field(default_factory=dict)
    year_dist:    dict[int, list[int]] = field(default_factory=dict)
    stale_counts: dict[str, list[int]] = field(default_factory=lambda: {k: [0, 0] for k in _STALE_THRESHOLDS})
    stale_folders: dict[str, set]      = field(default_factory=lambda: {k: set() for k in _STALE_THRESHOLDS})


def _scan_one_root(
    root: Path,
    exclusions: set[str],
    cancel: threading.Event,
    progress_cb,
    extensions: set[str] | None = None,
) -> tuple[dict[Path, FolderNode], _AnalysisAccum]:
    """Scan a single root folder, collecting analysis data at no extra I/O cost."""
    allowed_exts = extensions if extensions else MEDIA_EXTENSIONS
    folder_map: dict[Path, FolderNode] = {}
    accum = _AnalysisAccum()
    stack: deque[str] = deque([str(root)])
    batch_images = 0
    batch_videos = 0
    batch_bytes = 0
    current_folder = str(root)
    now_ts = _time_mod.time()

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
                    st = entry.stat()
                    size = st.st_size
                    mtime = st.st_mtime
                except OSError:
                    size = 0
                    mtime = now_ts

                node.total_size_bytes += size
                batch_bytes += size

                # Extension stats
                rec = accum.ext_stats.setdefault(ext, [0, 0])
                rec[0] += 1
                rec[1] += size

                # Year distribution
                try:
                    year = datetime.fromtimestamp(mtime).year
                except (OSError, OverflowError, ValueError):
                    year = 0
                if 1980 < year < 2100:
                    yrec = accum.year_dist.setdefault(year, [0, 0])
                    yrec[0] += 1
                    yrec[1] += size

                # Stale buckets
                age_s = now_ts - mtime
                for bucket, threshold in _STALE_THRESHOLDS.items():
                    if age_s >= threshold:
                        accum.stale_counts[bucket][0] += 1
                        accum.stale_counts[bucket][1] += size
                        accum.stale_folders[bucket].add(parent)

                if ext in IMAGE_EXTENSIONS:
                    batch_images += 1
                elif ext in VIDEO_EXTENSIONS:
                    batch_videos += 1

                if (batch_images + batch_videos) >= _PROGRESS_BATCH:
                    progress_cb(str(root), current_folder, batch_images, batch_videos, batch_bytes)
                    batch_images = 0
                    batch_videos = 0
                    batch_bytes = 0

    if batch_images + batch_videos > 0:
        progress_cb(str(root), current_folder, batch_images, batch_videos, batch_bytes)

    return folder_map, accum


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

        # Merged analysis accumulators across all roots
        merged_ext:   dict[str, list[int]] = {}
        merged_year:  dict[int, list[int]] = {}
        merged_stale: dict[str, list[int]] = {k: [0, 0] for k in _STALE_THRESHOLDS}
        merged_stale_folders: dict[str, set] = {k: set() for k in _STALE_THRESHOLDS}

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
                    result_map, accum = future.result()
                    for path, node in result_map.items():
                        if path in combined:
                            combined[path].file_count += node.file_count
                            combined[path].total_size_bytes += node.total_size_bytes
                        else:
                            combined[path] = node
                    # Merge analysis data
                    for ext, (cnt, byt) in accum.ext_stats.items():
                        r = merged_ext.setdefault(ext, [0, 0])
                        r[0] += cnt; r[1] += byt
                    for yr, (cnt, byt) in accum.year_dist.items():
                        r = merged_year.setdefault(yr, [0, 0])
                        r[0] += cnt; r[1] += byt
                    for bkt in _STALE_THRESHOLDS:
                        merged_stale[bkt][0] += accum.stale_counts[bkt][0]
                        merged_stale[bkt][1] += accum.stale_counts[bkt][1]
                        merged_stale_folders[bkt].update(accum.stale_folders[bkt])
                except Exception as exc:
                    logger.error("Scan thread error: %s", exc)
                    self.error_occurred.emit(str(exc))

        # Compute deep folders (depth from drive root > 5)
        deep: list[tuple] = []
        for p in combined:
            try:
                depth = len(p.relative_to(p.anchor).parts)
                if depth > 5:
                    deep.append((p, depth))
            except ValueError:
                pass
        deep.sort(key=lambda t: t[1], reverse=True)

        result = ScanResult(
            drives_scanned=sorted({str(f.drive) for f in self._scan_folders}),
            folder_nodes=list(combined.values()),
            total_files=self._total_images + self._total_videos,
            total_size_bytes=self._total_bytes,
            image_count=self._total_images,
            video_count=self._total_videos,
            ext_stats=merged_ext,
            year_dist=merged_year,
            stale_buckets=merged_stale,
            stale_folders=merged_stale_folders,
            deep_folders=deep[:20],
        )
        result.top_folders = sorted(
            result.folder_nodes, key=lambda n: n.total_size_bytes, reverse=True
        )[:10]
        self.scan_complete.emit(result)
