"""
MediaMitigator — FolderNode model.

Represents a single source folder unit eligible for transfer.

Author: Nathan
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class FolderStatus(str, Enum):
    """Transfer readiness status for a folder node."""
    READY = "READY"
    MULTI_YEAR = "MULTI_YEAR"
    DUPLICATE_ROOT = "DUPLICATE_ROOT"
    EXCLUDED = "EXCLUDED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class FolderNode:
    """A single atomic folder unit for transfer.

    Attributes:
        path: Absolute path to the source folder.
        file_count: Number of media files directly inside this folder.
        total_size_bytes: Combined size in bytes of all direct media files.
        destination_path: Resolved destination path (set during probe scan).
        status: Current transfer status.
        majority_year: Year determined by majority date logic.
        majority_month: Month (1-12) determined by majority date logic.
        is_checked: Whether the user has checked this folder for transfer.
        children: Child FolderNodes (for hierarchical display only).
        error_message: Last error message, if any.
    """
    path: Path
    file_count: int = 0
    total_size_bytes: int = 0
    destination_path: Path | None = None
    status: FolderStatus = FolderStatus.READY
    majority_year: int | None = None
    majority_month: int | None = None
    is_checked: bool = True
    children: list[FolderNode] = field(default_factory=list)
    error_message: str = ""

    @property
    def name(self) -> str:
        """The folder's base name."""
        return self.path.name

    @property
    def total_size_mb(self) -> float:
        """Total size in megabytes."""
        return self.total_size_bytes / (1024 * 1024)

    @property
    def total_size_gb(self) -> float:
        """Total size in gigabytes."""
        return self.total_size_bytes / (1024 ** 3)
