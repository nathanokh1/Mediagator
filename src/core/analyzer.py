"""
MediaMitigator — Transfer analyzer.

Resolves destination paths for each FolderNode and runs the disk
speed test to estimate transfer duration.

Author: Nathan
"""

import logging
import shutil
import tempfile
import time
from pathlib import Path

from src.config.constants import (
    DISK_SPEED_TEST_SIZE_MB,
    DISK_SPEED_TEST_DURATION_S,
    PHASE_THRESHOLD_SECONDS,
    OrgMode,
    DEFAULT_ORG_MODE,
)
from src.models.folder_node import FolderNode, FolderStatus
from src.models.scan_result import ScanResult
from src.models.transfer_plan import TransferPlan
from src.core.date_resolver import resolve_folder_dates
from src.utils.date_utils import month_folder_name

logger = logging.getLogger(__name__)


def resolve_destination(
    node: FolderNode,
    dest_root: Path,
    org_mode: str = DEFAULT_ORG_MODE,
) -> Path:
    """Compute the destination path for a single :class:`FolderNode`.

    The layout depends on *org_mode*:

    * ``OrgMode.YEAR_MONTH``  — ``[dest]/YYYY/MM-MonthName/FolderName/``
    * ``OrgMode.YEAR_ONLY``   — ``[dest]/YYYY/FolderName/``
    * ``OrgMode.EVENT_YEAR``  — ``[dest]/YYYY/FolderName/``  (alias of YEAR_ONLY,
                                  emphasises preserving your existing folder name)
    * ``OrgMode.FLAT``        — ``[dest]/FolderName/``
    * ``OrgMode.FILE_DATE``   — ``[dest]/YYYY/MM-MonthName/``  (no folder name;
                                  individual files are placed directly in date folder)

    Args:
        node: Source folder node (must have ``majority_year`` / ``majority_month``
            set for dated modes).
        dest_root: Root destination directory.
        org_mode: One of the :class:`OrgMode` string constants.

    Returns:
        Resolved destination :class:`Path`.
    """
    name = node.name

    if org_mode == OrgMode.FLAT:
        return dest_root / name

    year = node.majority_year or 0

    if org_mode in (OrgMode.YEAR_ONLY, OrgMode.EVENT_YEAR):
        return dest_root / str(year) / name

    month = node.majority_month or 1
    month_str = month_folder_name(month)

    if org_mode == OrgMode.FILE_DATE:
        # Files from this folder land directly in the date directory — no subfolder
        return dest_root / str(year) / month_str

    # Default: YEAR_MONTH
    return dest_root / str(year) / month_str / name


def run_speed_test(destination: Path) -> float:
    """Measure write speed to the destination drive.

    Writes a ``DISK_SPEED_TEST_SIZE_MB`` MB temp file to *destination*,
    measures elapsed time, and deletes it.

    Args:
        destination: Destination directory for the test write.

    Returns:
        Measured write speed in MB/s.  Returns 50.0 as a safe default on
        failure.
    """
    destination.mkdir(parents=True, exist_ok=True)
    test_bytes = DISK_SPEED_TEST_SIZE_MB * 1024 * 1024
    tmp_path = destination / "_mm_speedtest.tmp"

    try:
        chunk = b"\x00" * (1024 * 1024)
        start = time.perf_counter()
        deadline = start + DISK_SPEED_TEST_DURATION_S
        written = 0
        with tmp_path.open("wb") as fh:
            while written < test_bytes and time.perf_counter() < deadline:
                fh.write(chunk)
                written += len(chunk)
        elapsed = max(time.perf_counter() - start, 0.001)
        mb_per_s = (written / (1024 * 1024)) / elapsed
        return round(mb_per_s, 2)
    except Exception as exc:
        logger.warning("Speed test failed: %s", exc)
        return 50.0
    finally:
        tmp_path.unlink(missing_ok=True)


def build_transfer_plan(
    scan_result: ScanResult,
    destination_root: Path,
    checked_paths: set[Path] | None = None,
    org_mode: str = DEFAULT_ORG_MODE,
) -> TransferPlan:
    """Build a complete :class:`TransferPlan` from a scan result.

    Resolves destination paths for every checked :class:`FolderNode`,
    runs the disk speed test, and returns the plan.  Phase splitting is
    performed separately by :mod:`phase_manager`.

    Args:
        scan_result: Result from the initial drive scan.
        destination_root: Root destination folder.
        checked_paths: Set of folder paths the user has checked.  If
            ``None``, all folders are included.

    Returns:
        A fully populated :class:`TransferPlan`.
    """
    from src.models.transfer_plan import TransferPlan

    nodes: list[FolderNode] = []
    for node in scan_result.folder_nodes:
        if checked_paths is not None and node.path not in checked_paths:
            node.status = FolderStatus.EXCLUDED
            continue
        if not node.is_checked:
            node.status = FolderStatus.EXCLUDED
            continue

        # Skip date resolution if the ProbeWorker already resolved this node
        # (majority_year is set to a non-zero value).  This avoids re-reading
        # every EXIF file a second time, which would stall the Pre-Transfer step.
        if not node.majority_year:
            year, month, multi_year = resolve_folder_dates(node.path)
            node.majority_year = year
            node.majority_month = month
            if multi_year:
                node.status = FolderStatus.MULTI_YEAR

        node.destination_path = resolve_destination(node, destination_root, org_mode)
        nodes.append(node)

    total_files = sum(n.file_count for n in nodes)
    total_bytes = sum(n.total_size_bytes for n in nodes)

    speed_mbs = run_speed_test(destination_root)
    estimated_seconds = (total_bytes / (1024 * 1024)) / max(speed_mbs, 0.1)

    plan = TransferPlan(
        destination_root=destination_root,
        folder_nodes=nodes,
        total_files=total_files,
        total_size_bytes=total_bytes,
        measured_speed_mbs=speed_mbs,
        estimated_seconds=estimated_seconds,
        is_phased=(estimated_seconds > PHASE_THRESHOLD_SECONDS),
    )
    return plan
