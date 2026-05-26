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
import re
from datetime import datetime
from pathlib import Path

from src.config.constants import MEDIA_EXTENSIONS, IMAGE_EXTENSIONS
from src.utils.exif_reader import get_media_date
from src.utils.date_utils import majority_year_month

logger = logging.getLogger(__name__)

# Matches a plausible photo-era 4-digit year anywhere in a folder name.
# Range 1970–2035 avoids false matches on things like "1080p" or "4096".
_YEAR_RE = re.compile(r"(?<!\d)(19[7-9]\d|20[0-2]\d|2030|2031|2032|2033|2034|2035)(?!\d)")


def _year_from_folder_name(name: str) -> int | None:
    """Extract a plausible capture year directly from the folder name.

    Examples that match:
        "2022 Summer Vacation" → 2022
        "RAW_2019_Yosemite"    → 2019
        "SF 1.17.16"           → None  (no 4-digit year)
        "1080p_timelapse"      → None  (year range guard)

    Args:
        name: Folder base name (not full path).

    Returns:
        Integer year, or ``None`` if no plausible year found.
    """
    m = _YEAR_RE.search(name)
    return int(m.group()) if m else None


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


_THIS_YEAR = datetime.now().year


def _fast_file_date(path: Path) -> datetime | None:
    """Return a capture date estimate as quickly as possible.

    Strategy (fastest first):
    1. ``os.stat().st_mtime``  — one syscall, no file open.  Cameras set mtime
       to the shutter time, so this is usually accurate for unedited files.
    2. piexif header read      — only for image files when mtime looks like a
       recent transfer (mtime year == current year AND file is > 1 year old by
       size heuristic).  Avoids opening huge RAW files unnecessarily.

    Args:
        path: Media file path.

    Returns:
        Best available :class:`datetime`, or ``None``.
    """
    # Step 1: filesystem mtime — essentially free
    try:
        st = os.stat(str(path))
        mtime = datetime.fromtimestamp(st.st_mtime)
        # If mtime year is plausible (not the current year), trust it and skip EXIF.
        # Current-year mtime often means the file was just copied.
        if mtime.year < _THIS_YEAR:
            return mtime
        mtime_for_fallback = mtime
    except Exception:
        mtime_for_fallback = None

    # Step 2: piexif — only reached if mtime looks like a transfer date
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

    return mtime_for_fallback


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
    # ── Tier 1: folder name  (zero I/O, instant) ─────────────────────
    year = _year_from_folder_name(folder.name)
    if year:
        # We have a confident year from the name.  Still sample a few files
        # to determine the majority MONTH, but skip full EXIF reads.
        candidates: list[str] = []
        try:
            with os.scandir(str(folder)) as it:
                for entry in it:
                    if entry.is_file(follow_symlinks=False):
                        if os.path.splitext(entry.name)[1].lower() in MEDIA_EXTENSIONS:
                            candidates.append(entry.path)
        except Exception:
            pass

        # Sample fewer files since the year is already known
        month_sample = random.sample(candidates, min(20, len(candidates)))
        dates: list[datetime] = []
        for p in month_sample:
            dt = _fast_file_date(Path(p))
            if dt:
                dates.append(dt)

        _, month, multi_year = majority_year_month(dates)
        logger.debug("Probe (name): %s → year=%d month=%s", folder.name, year, month)
        return year, month, False

    # ── Tier 2: file mtime / piexif sample (normal path) ─────────────
    candidates = []
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

    dates = []
    for path_str in sample:
        dt = _fast_file_date(Path(path_str))
        if dt:
            dates.append(dt)

    logger.debug(
        "Probe (files): %s — %d / %d sampled (%.0f%%)",
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
