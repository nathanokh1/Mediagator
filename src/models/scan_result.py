"""
Mediagator — ScanResult model.

Holds the output of the initial drive scan.

Author: Nathan
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

from src.models.folder_node import FolderNode


@dataclass
class DriveInfo:
    """Basic metadata about a scanned drive.

    Attributes:
        letter: Drive letter (e.g. 'D').
        label: Volume label.
        total_bytes: Total capacity in bytes.
        free_bytes: Free space in bytes.
        is_selected: Whether the user has selected this drive.
    """
    letter: str
    label: str
    total_bytes: int
    free_bytes: int
    is_selected: bool = True

    @property
    def used_bytes(self) -> int:
        """Used space in bytes."""
        return self.total_bytes - self.free_bytes

    @property
    def usage_percent(self) -> float:
        """Percentage of drive used (0.0–100.0)."""
        if self.total_bytes == 0:
            return 0.0
        return (self.used_bytes / self.total_bytes) * 100.0

    @property
    def root_path(self) -> Path:
        """Root path for this drive."""
        return Path(f"{self.letter}:\\")


@dataclass
class ScanResult:
    """Output of a full drive scan.

    Attributes:
        drives_scanned: List of drives that were included in the scan.
        folder_nodes: Flat list of all discovered folder units.
        total_files: Total media file count across all folders.
        total_size_bytes: Combined size of all media files.
        image_count: Count of image files.
        video_count: Count of video files.
        top_folders: Up to 5 largest folders by size.
    """
    drives_scanned: list[str] = field(default_factory=list)
    folder_nodes: list[FolderNode] = field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0
    image_count: int = 0
    video_count: int = 0
    top_folders: list[FolderNode] = field(default_factory=list)

    @property
    def total_size_gb(self) -> float:
        """Total media size in gigabytes."""
        return self.total_size_bytes / (1024 ** 3)

    @property
    def folder_count(self) -> int:
        """Number of discovered folder units."""
        return len(self.folder_nodes)
