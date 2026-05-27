"""
Mediagator — Persistent settings management.

Loads and saves user settings to %APPDATA%/Mediagator/settings.json.

Author: Nathan
"""

import json
import logging
from pathlib import Path
from typing import Any

from src.config.constants import APPDATA_DIR, SETTINGS_FILE, DEFAULT_EXCLUSIONS, DEFAULT_CONFLICT_BEHAVIOR

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "selected_drives": [],
    "exclusion_list": sorted(DEFAULT_EXCLUSIONS),
    "selected_extensions": [],          # empty = use all MEDIA_EXTENSIONS
    "selected_scan_folders": [],
    "empty_folder_behavior": "flag",    # "delete" | "flag" | "leave"
    "toast_notifications": True,
    "email_notifications": False,
    "email_host": "",
    "email_port": 587,
    "email_sender": "",
    "email_recipient": "",
    "email_password": "",
    "lightroom_report": False,
    "welcome_seen": False,              # show welcome screen until user checks "don't show again"
    "conflict_behavior": DEFAULT_CONFLICT_BEHAVIOR,  # rename | skip | overwrite
    "theme": "dark",                    # dark | light
    "profiles": {},                     # name → {source_folders, extensions, destination, org_mode}
}


def _ensure_dir() -> None:
    """Create the settings directory if it does not exist."""
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict[str, Any]:
    """Load settings from disk, falling back to defaults for missing keys.

    Returns:
        A dictionary of all settings.
    """
    _ensure_dir()
    settings = dict(_DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as fh:
                stored = json.load(fh)
            settings.update(stored)
        except Exception as exc:
            logger.warning("Could not read settings file: %s", exc)
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    """Persist settings to disk.

    Args:
        settings: Dictionary of settings values to save.
    """
    _ensure_dir()
    try:
        with SETTINGS_FILE.open("w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
    except Exception as exc:
        logger.error("Could not save settings: %s", exc)


def load_session() -> dict[str, Any]:
    """Load resume session state from disk.

    Returns:
        Session state dict, or empty dict if none exists.
    """
    session_file = APPDATA_DIR / "session_state.json"
    if session_file.exists():
        try:
            with session_file.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception as exc:
            logger.warning("Could not read session state: %s", exc)
    return {}


def save_session(session: dict[str, Any]) -> None:
    """Persist transfer resume session state to disk.

    Args:
        session: Session state dictionary.
    """
    _ensure_dir()
    session_file = APPDATA_DIR / "session_state.json"
    try:
        with session_file.open("w", encoding="utf-8") as fh:
            json.dump(session, fh, indent=2)
    except Exception as exc:
        logger.error("Could not save session state: %s", exc)


def clear_session() -> None:
    """Remove the session state file after a completed or cancelled transfer."""
    session_file = APPDATA_DIR / "session_state.json"
    try:
        session_file.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Could not clear session state: %s", exc)
