"""
Mediagator — ScanResult model.

Holds the output of the initial drive scan, including rich analysis data
collected at zero extra I/O cost during the scan.

Author: Nathan
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

from src.models.folder_node import FolderNode


@dataclass
class DriveInfo:
    """Basic metadata about a scanned drive."""
    letter: str
    label: str
    total_bytes: int
    free_bytes: int
    is_selected: bool = True

    @property
    def used_bytes(self) -> int:
        return self.total_bytes - self.free_bytes

    @property
    def usage_percent(self) -> float:
        if self.total_bytes == 0:
            return 0.0
        return (self.used_bytes / self.total_bytes) * 100.0

    @property
    def root_path(self) -> Path:
        return Path(f"{self.letter}:\\")


@dataclass
class ScanResult:
    """Output of a full drive scan.

    Attributes:
        drives_scanned: Drive letters included in the scan.
        folder_nodes: All discovered folder units.
        total_files: Total media file count.
        total_size_bytes: Combined size of all media files.
        image_count: Count of image files.
        video_count: Count of video files.
        top_folders: Up to 10 largest folders by media size.

        -- Analysis data (collected during scan at no extra I/O cost) --
        ext_stats: Extension → [count, bytes] e.g. {'.jpg': [120, 4096000]}
        year_dist: Year → [count, bytes] e.g. {2022: [300, 8192000]}
        stale_buckets: Stale age bucket → [count, bytes].
            Keys: '3m+', '6m+', '1y+', '2y+' (each is inclusive of longer).
        stale_folders: Age bucket → set of folder Paths containing stale files.
        deep_folders: List of (Path, depth) for paths with depth > 5 from root.
    """
    drives_scanned: list[str] = field(default_factory=list)
    folder_nodes: list[FolderNode] = field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0
    image_count: int = 0
    video_count: int = 0
    top_folders: list[FolderNode] = field(default_factory=list)

    # Rich analysis
    ext_stats: dict[str, list[int]] = field(default_factory=dict)   # ext → [count, bytes]
    year_dist: dict[int, list[int]] = field(default_factory=dict)   # year → [count, bytes]
    stale_buckets: dict[str, list[int]] = field(default_factory=dict)  # bucket → [count, bytes]
    stale_folders: dict[str, set[Path]] = field(default_factory=dict)  # bucket → {folder paths}
    deep_folders: list[tuple[Path, int]] = field(default_factory=list)  # (path, depth)

    @property
    def total_size_gb(self) -> float:
        return self.total_size_bytes / (1024 ** 3)

    @property
    def folder_count(self) -> int:
        return len(self.folder_nodes)
