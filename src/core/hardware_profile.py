"""
Mediagator — Hardware Profile.

Detects source and destination drive types (SSD vs HDD), available RAM,
and CPU core count, then computes optimal transfer settings.

Detection uses a PowerShell one-liner so it works on all Windows versions
without third-party dependencies.  Falls back gracefully on any error.

Author: Nathan
"""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Drive type constants
# ---------------------------------------------------------------------------

DRIVE_SSD     = "SSD"
DRIVE_HDD     = "HDD"
DRIVE_UNKNOWN = "Unknown"


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class HardwareProfile:
    """Detected hardware configuration and derived transfer settings.

    Attributes:
        source_drive_type: "SSD", "HDD", or "Unknown".
        dest_drive_type:   "SSD", "HDD", or "Unknown".
        available_ram_gb:  Free physical RAM in gigabytes.
        cpu_cores:         Logical CPU count.
        optimal_workers:   Recommended parallel folder-copy workers.
        optimal_buffer_mb: Recommended copy buffer size in megabytes.
        is_admin:          True if the process has elevated privileges.
    """
    source_drive_type: str = DRIVE_UNKNOWN
    dest_drive_type:   str = DRIVE_UNKNOWN
    available_ram_gb:  float = 0.0
    cpu_cores:         int = 1
    optimal_workers:   int = 3
    optimal_buffer_mb: int = 16
    is_admin:          bool = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_admin() -> bool:
    """Return True if the current process has administrator privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _get_drive_type(path: Path) -> str:
    """Return 'SSD', 'HDD', or 'Unknown' for the drive containing *path*.

    Uses a PowerShell pipeline:
        Get-Partition → Get-Disk → Get-PhysicalDisk → MediaType
    """
    try:
        drive_letter = Path(path).resolve().drive  # e.g. 'E:'
        if not drive_letter or len(drive_letter) < 2:
            return DRIVE_UNKNOWN
        letter = drive_letter[0]  # just the letter

        ps = (
            f"$p = Get-Partition -DriveLetter '{letter}' -ErrorAction SilentlyContinue;"
            f"if ($p) {{"
            f"  $d = Get-PhysicalDisk | Where-Object {{ $_.DeviceId -eq [string]$p.DiskNumber }};"
            f"  $d.MediaType"
            f"}} else {{ 'Unknown' }}"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=8
        )
        output = result.stdout.strip().lower()
        if "ssd" in output:
            return DRIVE_SSD
        if "hdd" in output or "hard disk" in output:
            return DRIVE_HDD
        return DRIVE_UNKNOWN
    except Exception as exc:
        logger.debug("Drive type detection failed for %s: %s", path, exc)
        return DRIVE_UNKNOWN


def _available_ram_gb() -> float:
    """Return available physical RAM in GB using psutil if available."""
    try:
        import psutil  # optional dependency
        return psutil.virtual_memory().available / (1024 ** 3)
    except Exception:
        pass
    try:
        # Fallback: parse 'wmic OS get FreePhysicalMemory'
        r = subprocess.run(
            ["wmic", "OS", "get", "FreePhysicalMemory"],
            capture_output=True, text=True, timeout=6
        )
        lines = [l.strip() for l in r.stdout.splitlines() if l.strip().isdigit()]
        if lines:
            return int(lines[0]) / (1024 ** 2)  # KB → GB
    except Exception:
        pass
    return 4.0  # safe default


def _cpu_cores() -> int:
    return os.cpu_count() or 2


# ---------------------------------------------------------------------------
# Optimal settings logic
# ---------------------------------------------------------------------------

# Workers per (source_type, dest_type)
_WORKER_TABLE: dict[tuple[str, str], int] = {
    (DRIVE_SSD,     DRIVE_SSD):     6,
    (DRIVE_SSD,     DRIVE_HDD):     3,
    (DRIVE_SSD,     DRIVE_UNKNOWN): 4,
    (DRIVE_HDD,     DRIVE_SSD):     2,
    (DRIVE_HDD,     DRIVE_HDD):     2,
    (DRIVE_HDD,     DRIVE_UNKNOWN): 2,
    (DRIVE_UNKNOWN, DRIVE_SSD):     4,
    (DRIVE_UNKNOWN, DRIVE_HDD):     2,
    (DRIVE_UNKNOWN, DRIVE_UNKNOWN): 3,
}


def _optimal_buffer_mb(ram_gb: float, src: str, dst: str) -> int:
    """Return the best copy buffer size in MB given RAM and drive types."""
    # Cap buffer when an HDD is involved — large buffers don't help spinning disks
    hdd_involved = DRIVE_HDD in (src, dst)

    if ram_gb < 4:
        return 8
    if ram_gb < 8:
        return 16 if hdd_involved else 32
    if ram_gb < 32:
        return 32 if not hdd_involved else 16
    return 32 if hdd_involved else 64


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_hardware(source_path: Path, dest_path: Path) -> HardwareProfile:
    """Probe system hardware and return an optimised :class:`HardwareProfile`.

    This function is intended to be called once when the destination folder
    is selected (Step 3).  It is fast (< 1–2 s) but should still be called
    from a background thread so the GUI stays responsive.

    Args:
        source_path: Any path on the source drive (used to identify drive).
        dest_path:   Any path on the destination drive.

    Returns:
        A populated :class:`HardwareProfile`.
    """
    src_type  = _get_drive_type(source_path)
    dest_type = _get_drive_type(dest_path)
    ram_gb    = _available_ram_gb()
    cores     = _cpu_cores()
    admin     = _is_admin()

    workers   = _WORKER_TABLE.get((src_type, dest_type), 3)
    # Never exceed half the logical core count
    workers   = min(workers, max(cores // 2, 1))
    buffer_mb = _optimal_buffer_mb(ram_gb, src_type, dest_type)

    profile = HardwareProfile(
        source_drive_type = src_type,
        dest_drive_type   = dest_type,
        available_ram_gb  = round(ram_gb, 1),
        cpu_cores         = cores,
        optimal_workers   = workers,
        optimal_buffer_mb = buffer_mb,
        is_admin          = admin,
    )
    logger.info(
        "HardwareProfile: src=%s dest=%s ram=%.1fGB cores=%d → workers=%d buffer=%dMB admin=%s",
        src_type, dest_type, ram_gb, cores, workers, buffer_mb, admin,
    )
    return profile


# ---------------------------------------------------------------------------
# Windows Defender exclusion helpers
# ---------------------------------------------------------------------------

def add_defender_exclusions(paths: list[Path]) -> bool:
    """Add *paths* to Windows Defender real-time exclusions.

    Requires administrator privileges.

    Args:
        paths: List of folder paths to exclude.

    Returns:
        True if the operation succeeded, False otherwise.
    """
    if not _is_admin():
        logger.warning("Defender exclusions skipped — not running as admin.")
        return False
    try:
        for p in paths:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f'Add-MpPreference -ExclusionPath "{p}"'],
                capture_output=True, timeout=10
            )
            logger.info("Added Defender exclusion: %s", p)
        return True
    except Exception as exc:
        logger.warning("Failed to add Defender exclusions: %s", exc)
        return False


def remove_defender_exclusions(paths: list[Path]) -> None:
    """Remove previously added Defender exclusions.

    Safe to call even if the exclusion was never added or admin rights are gone.

    Args:
        paths: List of folder paths to remove from exclusions.
    """
    if not _is_admin():
        return
    try:
        for p in paths:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f'Remove-MpPreference -ExclusionPath "{p}"'],
                capture_output=True, timeout=10
            )
            logger.info("Removed Defender exclusion: %s", p)
    except Exception as exc:
        logger.warning("Failed to remove Defender exclusions: %s", exc)
