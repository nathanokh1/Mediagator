"""
Mediagator — EXIF and media metadata reader.

Provides a unified interface for extracting capture dates from image and
video files using Pillow, piexif, and pymediainfo.

Author: Nathan
"""

import logging
from datetime import datetime
from pathlib import Path

from src.config.constants import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from src.utils.date_utils import parse_exif_datetime

logger = logging.getLogger(__name__)


def get_image_date(path: Path) -> datetime | None:
    """Extract capture date from an image file using EXIF metadata.

    Tries in order:
    1. ``DateTimeOriginal`` tag via piexif
    2. ``DateTime`` tag via Pillow

    Args:
        path: Path to the image file.

    Returns:
        Capture :class:`datetime`, or ``None`` if not available.
    """
    try:
        import piexif
        exif_data = piexif.load(str(path))
        for ifd in ("Exif", "0th"):
            tag = piexif.ExifIFD.DateTimeOriginal if ifd == "Exif" else piexif.ImageIFD.DateTime
            raw = exif_data.get(ifd, {}).get(tag)
            if raw:
                dt = parse_exif_datetime(raw.decode("utf-8", errors="ignore"))
                if dt:
                    return dt
    except Exception:
        pass

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        img = Image.open(path)
        exif_data = img._getexif()  # type: ignore[attr-defined]
        if exif_data:
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, "")
                if tag_name in ("DateTimeOriginal", "DateTime"):
                    dt = parse_exif_datetime(str(value))
                    if dt:
                        return dt
    except Exception:
        pass

    return None


def get_video_date(path: Path) -> datetime | None:
    """Extract capture date from a video file using pymediainfo.

    Args:
        path: Path to the video file.

    Returns:
        Capture :class:`datetime`, or ``None`` if not available.
    """
    try:
        from pymediainfo import MediaInfo
        info = MediaInfo.parse(str(path))
        for track in info.tracks:
            for attr in ("file_last_modification_date", "encoded_date", "tagged_date"):
                raw = getattr(track, attr, None)
                if raw:
                    dt = parse_exif_datetime(str(raw).replace("UTC ", ""))
                    if dt:
                        return dt
    except Exception as exc:
        logger.debug("pymediainfo failed on %s: %s", path, exc)
    return None


def get_media_date(path: Path) -> datetime | None:
    """Return the best available capture date for any media file.

    Delegates to :func:`get_image_date` for images and :func:`get_video_date`
    for videos.  Falls back to the file's creation time on Windows.

    Args:
        path: Path to the media file.

    Returns:
        Best available :class:`datetime`.
    """
    ext = path.suffix.lower()
    dt: datetime | None = None

    if ext in IMAGE_EXTENSIONS:
        dt = get_image_date(path)
    elif ext in VIDEO_EXTENSIONS:
        dt = get_video_date(path)

    if dt is None:
        try:
            import os
            ctime = os.path.getctime(str(path))
            dt = datetime.fromtimestamp(ctime)
        except Exception:
            pass

    return dt
