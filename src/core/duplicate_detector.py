"""
MediaMitigator — Duplicate file detector.

Determines whether a source file is a true duplicate of an already-transferred
destination file or another file in the transfer queue.

Author: Nathan
"""

import logging
import os
from pathlib import Path
from datetime import datetime

from src.config.constants import CREATION_DATE_TOLERANCE_S
from src.utils.exif_reader import get_media_date

logger = logging.getLogger(__name__)


def _creation_time(path: Path) -> datetime | None:
    """Return the file creation time as a :class:`datetime`.

    Args:
        path: File path.

    Returns:
        Creation :class:`datetime`, or ``None`` on error.
    """
    try:
        return datetime.fromtimestamp(os.path.getctime(str(path)))
    except Exception:
        return None


def is_duplicate(
    source: Path,
    destination: Path,
) -> tuple[bool, str]:
    """Check whether *source* is a true duplicate of *destination*.

    A true duplicate satisfies BOTH conditions:
    - Same filename (case-insensitive).
    - Same EXIF DateTimeOriginal OR creation timestamps within tolerance.

    Args:
        source: Candidate source file.
        destination: Existing destination file.

    Returns:
        Tuple of ``(is_dup, method_description)`` where *method_description*
        explains which comparison was used.
    """
    if source.name.lower() != destination.name.lower():
        return False, ""

    src_exif = get_media_date(source)
    dst_exif = get_media_date(destination)

    if src_exif and dst_exif:
        if src_exif == dst_exif:
            return True, f"EXIF match ({src_exif})"
    else:
        src_ctime = _creation_time(source)
        dst_ctime = _creation_time(destination)
        if src_ctime and dst_ctime:
            delta = abs((src_ctime - dst_ctime).total_seconds())
            if delta <= CREATION_DATE_TOLERANCE_S:
                return True, f"ctime match Δ{delta:.2f}s ({src_ctime} / {dst_ctime})"

    return False, ""
