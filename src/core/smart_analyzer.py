"""
Mediagator — Smart media analyzer.

Samples the scan result to produce AI-style insights without requiring
any external ML model:

  • Camera / device fingerprinting from EXIF Make + Model
  • Shooting event detection via date-gap clustering
  • GPS coverage percentage
  • Year range and peak year
  • File-naming pattern detection (GoPro, DJI, iPhone, etc.)
  • Organisation style recommendation

All analysis is done by reading only EXIF headers (fast, small reads).

Author: Nathan
"""

from __future__ import annotations

import logging
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.models.scan_result import ScanResult
from src.config.constants import IMAGE_EXTENSIONS, MEDIA_EXTENSIONS

logger = logging.getLogger(__name__)

# Maximum files to sample for EXIF analysis (keeps analysis fast)
_MAX_SAMPLE = 2000

# Date gap that separates two distinct shooting "events"
_EVENT_GAP_DAYS = 3

# Filename prefixes that reveal camera/device
_FILENAME_CAMERAS: list[tuple[str, str]] = [
    (r"^GX\d", "GoPro MAX"),
    (r"^G[HXO]\d", "GoPro"),
    (r"^DJI_\d", "DJI Drone"),
    (r"^DJI\d", "DJI Drone"),
    (r"^GOPR\d", "GoPro"),
    (r"^IMG_E", "iPhone (edited)"),
    (r"^IMG_\d{4}", "iPhone / Canon"),
    (r"^DSC\d", "Sony"),
    (r"^DSF\d", "Sony Fuji"),
    (r"^DSCF\d", "Fujifilm"),
    (r"^_MG_\d", "Canon"),
    (r"^_DSC\d", "Sony"),
    (r"^P\d{7}", "Olympus"),
    (r"^MVI_\d", "Canon (video)"),
    (r"^VID_\d", "Android Phone"),
    (r"^PANO_\d", "Panoramic"),
    (r"^100[A-Z]{4}", "Camera Card Root"),
]


@dataclass
class SmartInsights:
    """Results of the smart media analysis.

    Attributes:
        top_cameras: List of ``(camera_name, count)`` tuples, most common first.
        event_count: Number of detected shooting events.
        year_range: Tuple ``(earliest_year, latest_year)`` or ``(None, None)``.
        peak_year: Year with the most files.
        gps_percent: Percentage of sampled images with GPS data.
        total_sampled: Number of files actually sampled.
        filename_cameras: Cameras detected purely by filename prefix.
        date_clusters: List of ``(start_date, end_date, file_count)`` per event.
        recommendation: Human-readable organisation recommendation string.
        raw_stats: Extra dict for the dashboard to display freely.
    """
    top_cameras: list[tuple[str, int]] = field(default_factory=list)
    event_count: int = 0
    year_range: tuple[int | None, int | None] = (None, None)
    peak_year: int | None = None
    gps_percent: float = 0.0
    total_sampled: int = 0
    filename_cameras: list[tuple[str, int]] = field(default_factory=list)
    date_clusters: list[tuple[datetime, datetime, int]] = field(default_factory=list)
    recommendation: str = ""
    raw_stats: dict[str, Any] = field(default_factory=dict)


def _try_read_exif(path: Path) -> dict[str, Any]:
    """Read a minimal EXIF subset from an image file.

    Args:
        path: Image path.

    Returns:
        Dict with keys ``date``, ``make``, ``model``, ``has_gps``.
    """
    result: dict[str, Any] = {"date": None, "make": "", "model": "", "has_gps": False}
    try:
        import piexif
        data = piexif.load(str(path))
        # Date
        raw_date = (
            data.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
            or data.get("0th", {}).get(piexif.ImageIFD.DateTime)
        )
        if raw_date:
            try:
                result["date"] = datetime.strptime(
                    raw_date.decode("utf-8", errors="ignore").strip(),
                    "%Y:%m:%d %H:%M:%S",
                )
            except ValueError:
                pass
        # Make / Model
        make = data.get("0th", {}).get(piexif.ImageIFD.Make, b"")
        model = data.get("0th", {}).get(piexif.ImageIFD.Model, b"")
        result["make"] = make.decode("utf-8", errors="ignore").strip().rstrip("\x00")
        result["model"] = model.decode("utf-8", errors="ignore").strip().rstrip("\x00")
        # GPS
        result["has_gps"] = bool(data.get("GPS"))
    except Exception:
        pass
    return result


def _sample_files(scan_result: ScanResult, max_files: int) -> list[Path]:
    """Select up to *max_files* image paths from the scan result.

    Takes files evenly across all folders so the sample is representative.

    Args:
        scan_result: Completed scan result.
        max_files: Maximum sample size.

    Returns:
        List of image file paths.
    """
    image_files: list[Path] = []
    for node in scan_result.folder_nodes:
        try:
            for entry in os.scandir(str(node.path)):
                if (
                    entry.is_file(follow_symlinks=False)
                    and os.path.splitext(entry.name)[1].lower() in IMAGE_EXTENSIONS
                ):
                    image_files.append(Path(entry.path))
        except (PermissionError, FileNotFoundError):
            continue

    if len(image_files) <= max_files:
        return image_files

    # Evenly spaced sample
    step = len(image_files) / max_files
    return [image_files[int(i * step)] for i in range(max_files)]


def _detect_filename_cameras(files: list[Path]) -> list[tuple[str, int]]:
    """Detect camera types from filename prefixes.

    Args:
        files: List of file paths.

    Returns:
        ``(camera_name, count)`` list, most common first.
    """
    counts: Counter[str] = Counter()
    patterns = [(re.compile(p, re.IGNORECASE), name) for p, name in _FILENAME_CAMERAS]
    for f in files:
        for pattern, name in patterns:
            if pattern.match(f.name):
                counts[name] += 1
                break
    return counts.most_common(5)


def _cluster_events(
    dates: list[datetime],
    gap_days: int = _EVENT_GAP_DAYS,
) -> list[tuple[datetime, datetime, int]]:
    """Group sorted dates into shooting events by temporal gaps.

    Args:
        dates: Sorted list of capture datetimes.
        gap_days: Gap in days that separates two events.

    Returns:
        List of ``(start, end, count)`` per cluster.
    """
    if not dates:
        return []
    clusters: list[tuple[datetime, datetime, int]] = []
    cluster_start = dates[0]
    cluster_prev = dates[0]
    cluster_count = 1
    gap = timedelta(days=gap_days)

    for dt in dates[1:]:
        if dt - cluster_prev > gap:
            clusters.append((cluster_start, cluster_prev, cluster_count))
            cluster_start = dt
            cluster_count = 1
        else:
            cluster_count += 1
        cluster_prev = dt
    clusters.append((cluster_start, cluster_prev, cluster_count))
    return clusters


def _build_recommendation(insights: SmartInsights) -> str:
    """Generate a plain-English recommendation string.

    Args:
        insights: Partially populated insights (cameras / events / GPS).

    Returns:
        Recommendation string.
    """
    parts: list[str] = []

    if insights.top_cameras:
        primary = insights.top_cameras[0][0]
        parts.append(f"Primary device: {primary}.")

    if insights.gps_percent >= 50:
        parts.append(
            f"GPS data available on {insights.gps_percent:.0f}% of images — "
            "location-based folder names are possible."
        )
    elif insights.gps_percent > 0:
        parts.append(
            f"GPS data on {insights.gps_percent:.0f}% of images (partial coverage)."
        )

    y_start, y_end = insights.year_range
    if y_start and y_end:
        span = y_end - y_start
        if span == 0:
            parts.append(f"All media from {y_start}.")
        else:
            parts.append(f"Media spans {span + 1} years ({y_start}–{y_end}).")

    if insights.event_count > 0:
        parts.append(
            f"Detected ~{insights.event_count} distinct shooting events. "
            "Recommended layout: [Year] / [MM-Month] / [FolderName]."
        )

    return "  ".join(parts) if parts else "Analysis complete."


def analyze(scan_result: ScanResult) -> SmartInsights:
    """Run smart analysis on a completed scan result.

    Samples up to 2 000 image files, reads their EXIF headers, and
    produces :class:`SmartInsights`.

    Args:
        scan_result: Completed :class:`ScanResult`.

    Returns:
        Populated :class:`SmartInsights`.
    """
    insights = SmartInsights()
    files = _sample_files(scan_result, _MAX_SAMPLE)
    insights.total_sampled = len(files)

    if not files:
        insights.recommendation = "No image files sampled — nothing to analyse."
        return insights

    # Filename-based camera detection (fast, no I/O beyond filenames)
    insights.filename_cameras = _detect_filename_cameras(files)

    # EXIF analysis
    camera_counter: Counter[str] = Counter()
    dates: list[datetime] = []
    year_counter: Counter[int] = Counter()
    gps_count = 0

    for path in files:
        exif = _try_read_exif(path)

        if exif["make"] or exif["model"]:
            name = f"{exif['make']} {exif['model']}".strip()
            camera_counter[name] += 1

        if exif["date"]:
            dates.append(exif["date"])
            year_counter[exif["date"].year] += 1

        if exif["has_gps"]:
            gps_count += 1

    insights.top_cameras = camera_counter.most_common(5)
    insights.gps_percent = (gps_count / len(files)) * 100 if files else 0.0

    if dates:
        dates.sort()
        insights.year_range = (dates[0].year, dates[-1].year)
        insights.peak_year = year_counter.most_common(1)[0][0] if year_counter else None
        insights.date_clusters = _cluster_events(dates)
        insights.event_count = len(insights.date_clusters)

    # Merge filename cameras into top_cameras if EXIF cameras are sparse
    if len(insights.top_cameras) < 2 and insights.filename_cameras:
        seen = {c for c, _ in insights.top_cameras}
        for name, count in insights.filename_cameras:
            if name not in seen:
                insights.top_cameras.append((name, count))

    insights.raw_stats = {
        "year_distribution": dict(year_counter.most_common(10)),
        "files_with_exif_date": len(dates),
        "files_with_gps": gps_count,
    }

    insights.recommendation = _build_recommendation(insights)
    return insights
