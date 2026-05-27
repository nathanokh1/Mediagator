"""
Mediagator — Date utility helpers.

Author: Nathan
"""

from datetime import datetime
from collections import Counter
from pathlib import Path


def parse_exif_datetime(value: str) -> datetime | None:
    """Parse an EXIF datetime string into a :class:`datetime`.

    EXIF stores dates as ``YYYY:MM:DD HH:MM:SS``.

    Args:
        value: Raw EXIF datetime string.

    Returns:
        Parsed :class:`datetime`, or ``None`` on parse failure.
    """
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def majority_year_month(dates: list[datetime]) -> tuple[int | None, int | None, bool]:
    """Determine the majority year and month from a list of file dates.

    Rules:
    - Majority year = most common year.  Tie → use oldest year.
    - Majority month = most common month *within* majority year.  Tie → oldest month.
    - MULTI_YEAR flag = files span more than 2 distinct calendar years.

    Args:
        dates: Non-empty list of datetimes.

    Returns:
        Tuple of ``(year, month, is_multi_year)``.  All values are ``None`` /
        ``False`` if *dates* is empty.
    """
    if not dates:
        return None, None, False

    years = [d.year for d in dates]
    unique_years = sorted(set(years))
    is_multi_year = (len(unique_years) > 2)

    year_counts = Counter(years)
    max_count = max(year_counts.values())
    candidate_years = [y for y, c in year_counts.items() if c == max_count]
    majority_year = min(candidate_years)

    months_in_year = [d.month for d in dates if d.year == majority_year]
    if not months_in_year:
        return majority_year, None, is_multi_year

    month_counts = Counter(months_in_year)
    max_month_count = max(month_counts.values())
    candidate_months = [m for m, c in month_counts.items() if c == max_month_count]
    majority_month = min(candidate_months)

    return majority_year, majority_month, is_multi_year


MONTH_NAMES = {
    1: "01-January", 2: "02-February", 3: "03-March", 4: "04-April",
    5: "05-May", 6: "06-June", 7: "07-July", 8: "08-August",
    9: "09-September", 10: "10-October", 11: "11-November", 12: "12-December",
}


def month_folder_name(month: int) -> str:
    """Return the destination month folder name for a given month number.

    Args:
        month: Month number (1-12).

    Returns:
        Formatted string like ``"01-January"``.
    """
    return MONTH_NAMES.get(month, f"{month:02d}-Unknown")


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        String like ``"1h 23m"`` or ``"45s"``.
    """
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}m"
