"""
MediaMitigator — Date resolver.

Determines the best capture date for a media file and the majority
year/month for a folder full of media.

Two resolvers are provided:
  resolve_folder_dates        — full EXIF read of every file (accurate, slow)
  resolve_folder_dates_fast   — samples up to MAX_SAMPLE files, uses piexif
                                only (no PIL open), falls back to ctime.
                                ~50× faster — used by the Probe worker.

Author: Nathan
"""

import logging
import os
import random
from datetime import datetime
from pathlib import Path

from src.config.constants import MEDIA_EXTENSIONS, IMAGE_EXTENSIONS
from src.utils.exif_reader import get_media_date
from src.utils.date_utils import majority_year_month

logger = logging.getLogger(__name__)


def resolve_file_date(path: Path) -> datetime | None:
    """Return the best available capture date for a media file.

    Args:
        path: Path to the media file.

    Returns:
        Best :class:`datetime`, or ``None`` if none could be determined.
    """
    return get_media_date(path)


# Sampling constants for resolve_folder_dates_fast
_SAMPLE_PCT   = 0.20   # 20 % of the folder's files
_SAMPLE_MIN   = 10     # always read at least this many
_SAMPLE_MAX   = 500    # cap so huge folders don't stall the probe


def _fast_file_date(path: Path) -> datetime | None:
    """Read a capture date as quickly as possible.

    Order of attempts (fastest to slowest):
    1. piexif header read (image files only, no image decode)
    2. os.stat().st_ctime  (instant, but may be transfer date)

    Args:
        path: Media file path.

    Returns:
        Best available :class:`datetime`, or ``None``.
    """
    ext = path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        try:
            import piexif
            from src.utils.date_utils import parse_exif_datetime
            exif = piexif.load(str(path))
            for ifd, tag_id in (
                ("Exif", piexif.ExifIFD.DateTimeOriginal),
                ("0th",  piexif.ImageIFD.DateTime),
            ):
                raw = exif.get(ifd, {}).get(tag_id)
                if raw:
                    dt = parse_exif_datetime(raw.decode("utf-8", errors="ignore"))
                    if dt:
                        return dt
        except Exception:
            pass
    try:
        return datetime.fromtimestamp(os.stat(str(path)).st_ctime)
    except Exception:
        return None


def resolve_folder_dates_fast(
    folder: Path,
) -> tuple[int | None, int | None, bool]:
    """Fast majority-date resolver using a percentage-based random sample.

    Sample size = clamp(len(files) × 20 %, min=10, max=500).

    Examples:
      20-file folder  → 10  (floor kicks in)
      200-file folder → 40
      1 000-file folder → 200
      5 000-file folder → 500  (ceiling kicks in)

    Uses :func:`_fast_file_date` (piexif header read → ctime fallback) so
    it never fully decodes images.  Suitable for the probe pass.

    Args:
        folder: Source folder to analyse.

    Returns:
        ``(majority_year, majority_month, is_multi_year)`` tuple.
    """
    candidates: list[str] = []
    try:
        with os.scandir(str(folder)) as it:
            for entry in it:
                if not entry.is_file(follow_symlinks=False):
                    continue
                if os.path.splitext(entry.name)[1].lower() not in MEDIA_EXTENSIONS:
                    continue
                candidates.append(entry.path)
    except PermissionError as exc:
        logger.warning("Permission denied reading %s: %s", folder, exc)
        return majority_year_month([])
    except Exception as exc:
        logger.debug("Fast date read error %s: %s", folder, exc)
        return majority_year_month([])

    n = len(candidates)
    sample_size = int(max(_SAMPLE_MIN, min(_SAMPLE_MAX, n * _SAMPLE_PCT)))
    sample = random.sample(candidates, min(sample_size, n))

    dates: list[datetime] = []
    for path_str in sample:
        dt = _fast_file_date(Path(path_str))
        if dt:
            dates.append(dt)

    logger.debug(
        "Probe sample: %s — %d / %d files read (%.0f%%)",
        folder.name, len(sample), n, 100 * len(sample) / max(n, 1),
    )
    return majority_year_month(dates)


def resolve_folder_dates(folder: Path) -> tuple[int | None, int | None, bool]:
    """Determine majority year, majority month, and MULTI_YEAR flag for a folder.

    Only direct children (non-recursive) with media extensions are considered.

    Args:
        folder: Path to the source folder.

    Returns:
        Tuple of ``(year, month, is_multi_year)``.
    """
    dates: list[datetime] = []
    try:
        for child in folder.iterdir():
            if child.is_file() and child.suffix.lower() in MEDIA_EXTENSIONS:
                dt = resolve_file_date(child)
                if dt:
                    dates.append(dt)
    except PermissionError as exc:
        logger.warning("Permission denied reading %s: %s", folder, exc)

    return majority_year_month(dates)
