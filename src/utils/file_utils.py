"""
MediaMitigator — File system utility helpers.

Author: Nathan
"""

import shutil
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# 16 MB read/write buffer — reduces syscall overhead vs shutil.copy2's ~16 KB default.
# Especially effective on HDDs where large sequential reads are much faster than many
# small ones, and on USB drives where per-operation latency is noticeable.
_COPY_BUFFER = 16 * 1024 * 1024


def safe_copy(source: Path, destination: Path) -> bool:
    """Copy a file with a large buffer and verify by size comparison.

    Uses a 16 MB I/O buffer (vs ``shutil.copy2``'s ~16 KB default) to
    maximise sequential throughput on HDDs and USB drives.  The destination
    parent directory is created if it does not exist.

    Args:
        source: Absolute path to the source file.
        destination: Absolute path to the destination file.

    Returns:
        ``True`` if copy succeeded and sizes match, ``False`` otherwise.
    """
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.unlink()
        # Buffered copy preserves metadata timestamps (like shutil.copy2)
        with source.open("rb") as src_fh, destination.open("wb") as dst_fh:
            shutil.copyfileobj(src_fh, dst_fh, length=_COPY_BUFFER)
        shutil.copystat(str(source), str(destination))
        if destination.stat().st_size == source.stat().st_size:
            return True
        logger.error("Size mismatch after copy: %s → %s", source, destination)
        destination.unlink(missing_ok=True)
        return False
    except Exception as exc:
        logger.error("Copy failed %s → %s: %s", source, destination, exc)
        destination.unlink(missing_ok=True)
        return False


def safe_delete(path: Path) -> bool:
    """Delete a file safely, logging any errors.

    Args:
        path: Path to the file to delete.

    Returns:
        ``True`` if the file was deleted or did not exist, ``False`` on error.
    """
    try:
        path.unlink(missing_ok=True)
        return True
    except Exception as exc:
        logger.error("Delete failed %s: %s", path, exc)
        return False


def delete_empty_folder(folder: Path) -> bool:
    """Remove a folder only if it is empty.

    Args:
        folder: Path to the directory to remove.

    Returns:
        ``True`` if removed, ``False`` if non-empty or on error.
    """
    try:
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
            return True
        return False
    except Exception as exc:
        logger.error("Could not remove folder %s: %s", folder, exc)
        return False


def open_in_explorer(path: Path) -> None:
    """Open a path in Windows Explorer.

    Args:
        path: File or folder to reveal.
    """
    try:
        subprocess.Popen(["explorer", str(path)])
    except Exception as exc:
        logger.warning("Could not open Explorer for %s: %s", path, exc)


def human_readable_size(size_bytes: int) -> str:
    """Convert a byte count to a human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted string like ``"1.23 GB"`` or ``"456 MB"``.
    """
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes //= 1024
    return f"{size_bytes:.1f} PB"


def next_available_path(path: Path) -> Path:
    """Return a non-conflicting path by appending ``_2``, ``_3`` etc.

    Args:
        path: Desired destination path.

    Returns:
        Original path if it does not exist, otherwise a suffixed variant.
    """
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
