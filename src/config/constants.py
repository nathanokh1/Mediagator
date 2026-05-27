"""
MediaMitigator — Application-wide constants.

Author: Nathan
"""

from pathlib import Path
import os

# ---------------------------------------------------------------------------
# File type sets
# ---------------------------------------------------------------------------
IMAGE_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".heic", ".raw", ".cr2", ".cr3",
    ".nef", ".arw", ".dng", ".tiff", ".tif", ".bmp", ".gif", ".webp",
}

VIDEO_EXTENSIONS: set[str] = {
    ".mp4", ".mov", ".avi", ".mkv", ".mts", ".m2ts", ".mxf", ".lrv", ".thm",
}

MEDIA_EXTENSIONS: set[str] = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# ---------------------------------------------------------------------------
# File type groups — used by the FileTypeFilterWidget in Step 1.
# Each entry: label shown in UI, list of extensions, default checked state.
# ---------------------------------------------------------------------------
FILE_TYPE_GROUPS: list[dict] = [
    {
        "name": "📷  Photos",
        "id": "photos",
        "items": [
            {"label": "JPG / JPEG",       "exts": [".jpg", ".jpeg"],       "default": True},
            {"label": "PNG",              "exts": [".png"],                "default": True},
            {"label": "HEIC  (iPhone)",   "exts": [".heic"],               "default": True},
            {"label": "GIF",              "exts": [".gif"],                "default": True},
            {"label": "WEBP",             "exts": [".webp"],               "default": True},
            {"label": "BMP",              "exts": [".bmp"],                "default": True},
        ],
    },
    {
        "name": "📸  RAW / Professional",
        "id": "raw",
        "items": [
            {"label": "RAW",              "exts": [".raw"],                "default": True},
            {"label": "CR2 / CR3  (Canon)","exts": [".cr2", ".cr3"],      "default": True},
            {"label": "NEF  (Nikon)",     "exts": [".nef"],               "default": True},
            {"label": "ARW  (Sony)",      "exts": [".arw"],               "default": True},
            {"label": "DNG  (Adobe)",     "exts": [".dng"],               "default": True},
            {"label": "TIFF / TIF",       "exts": [".tiff", ".tif"],      "default": True},
        ],
    },
    {
        "name": "🎬  Videos",
        "id": "videos",
        "items": [
            {"label": "MP4",              "exts": [".mp4"],                "default": True},
            {"label": "MOV  (Apple)",     "exts": [".mov"],               "default": True},
            {"label": "AVI",              "exts": [".avi"],                "default": True},
            {"label": "MKV",              "exts": [".mkv"],                "default": True},
            {"label": "MTS / M2TS  (Camcorder)", "exts": [".mts", ".m2ts"], "default": True},
            {"label": "MXF  (Professional)",     "exts": [".mxf"],         "default": True},
            {"label": "LRV / THM  (GoPro proxy)","exts": [".lrv", ".thm"],"default": True},
        ],
    },
]

DEFAULT_SELECTED_EXTENSIONS: set[str] = MEDIA_EXTENSIONS.copy()

# ---------------------------------------------------------------------------
# Organisation modes — how transferred folders are arranged at the destination.
# ---------------------------------------------------------------------------
class OrgMode:
    """Organisation mode identifiers."""
    YEAR_MONTH = "year_month"   # dest/2024/06-June/FolderName/
    YEAR_ONLY  = "year_only"    # dest/2024/FolderName/
    FLAT       = "flat"         # dest/FolderName/  (no date hierarchy)

ORG_MODE_LABELS: dict[str, str] = {
    OrgMode.YEAR_MONTH: "Year / Month  —  2024 › 06-June › Folder Name",
    OrgMode.YEAR_ONLY:  "Year only     —  2024 › Folder Name",
    OrgMode.FLAT:       "No reorganisation  —  Folder Name  (copy as-is)",
}

DEFAULT_ORG_MODE: str = OrgMode.YEAR_MONTH

# ---------------------------------------------------------------------------
# Default folder exclusions (case-insensitive match against folder name)
# ---------------------------------------------------------------------------
DEFAULT_EXCLUSIONS: set[str] = {
    "movies and shows",
    "movies and shows backup",
    "movies",
    "tv shows",
    "plex",
    "recycle bin",
    "system volume information",
    "$recycle.bin",
    "windows",
    "program files",
    "program files (x86)",
    "appdata",
}

# ---------------------------------------------------------------------------
# Smart folder classification (used in Drive Selection step)
# ---------------------------------------------------------------------------

# These folder names are almost certainly personal media — auto-check them
MEDIA_FOLDER_HINTS: set[str] = {
    "pictures", "photos", "photo", "camera", "dcim", "videos", "video",
    "media", "memories", "footage", "raw", "shoots", "shoot", "events",
    "lightroom", "catalog", "catalogs", "imports", "exports", "drone",
    "gopro", "dji", "wedding", "family", "vacation", "holiday",
    "birthday", "travel", "portrait", "landscapes", "captures",
    "gallery", "albums", "album", "film", "films", "timelapses",
    "b-roll", "broll", "highlights", "edits",
}

# These folder names are OS / application infrastructure — auto-uncheck them
SYSTEM_FOLDER_HINTS: set[str] = {
    "windows", "program files", "program files (x86)", "programdata",
    "appdata", "$recycle.bin", "system volume information", "recovery",
    "boot", "efi", "perflogs", "msocache", "winsxs", "drivers", "inf",
    "temp", "tmp", "cache", "node_modules", ".git", "venv", "__pycache__",
    "plex", "steam", "steamapps", "epic games", "origin", "battle.net",
    "blizzard", "games", "game", "software", "apps", "application",
    "intel", "amd", "nvidia", "dell", "hp", "lenovo", "asus",
    "miui", "android", "ios", ".android", ".gradle", ".npm",
    "logs", "log", "crashreports", "dumps", "minidump",
    "movies and shows", "movies and shows backup", "tv shows",
}

# Folders on the C:\ drive root that should almost always be unchecked
C_DRIVE_SYSTEM_ROOTS: set[str] = {
    "windows", "program files", "program files (x86)", "programdata",
    "perflogs", "recovery", "boot", "system volume information",
    "$recycle.bin", "msocache", "winsxs", "drivers",
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
APP_NAME = "MediaMitigator"
APPDATA_DIR: Path = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
SETTINGS_FILE: Path = APPDATA_DIR / "settings.json"
SESSION_FILE: Path = APPDATA_DIR / "session_state.json"

# ---------------------------------------------------------------------------
# Transfer thresholds
# ---------------------------------------------------------------------------
PHASE_THRESHOLD_SECONDS: int = 3600          # 60 minutes — trigger phased mode
PHASE_TARGET_SECONDS: int = 2700             # ~45 min per phase
DUPLICATE_FOLDER_NAME: str = "_DUPLICATES_REVIEW"
DISK_SPEED_TEST_SIZE_MB: int = 50
DISK_SPEED_TEST_DURATION_S: int = 3
MULTI_YEAR_THRESHOLD: int = 2                # span > 2 years → MULTI_YEAR flag
CREATION_DATE_TOLERANCE_S: float = 1.0       # seconds tolerance for duplicate check

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
WINDOW_MIN_WIDTH: int = 1000
WINDOW_MIN_HEIGHT: int = 700
WINDOW_TITLE: str = "MediaMitigator"

STEP_NAMES: list[str] = [
    "Welcome",
    "Drive Selection",
    "Initial Scan",
    "Destination",
    "Folder Review",
    "Transfer Settings",
    "Pre-Transfer Analysis",
    "Transfer",
    "Report",
]
