"""
Mediagator — TransferPlan model.

Holds the complete plan produced by the analyzer before any transfer starts.

Author: Nathan
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

from src.models.folder_node import FolderNode
from src.models.transfer_phase import TransferPhase


@dataclass
class TransferPlan:
    """Complete pre-transfer plan.

    Attributes:
        destination_root: Root destination folder.
        folder_nodes: Ordered list of checked folder units to transfer.
        phases: Phase breakdown (single item if no phasing needed).
        total_files: Total files to transfer.
        total_size_bytes: Total bytes to transfer.
        measured_speed_mbs: Speed measured by disk speed test (MB/s).
        estimated_seconds: Estimated transfer duration.
        is_phased: Whether multi-phase mode is active.
        lightroom_paths: Accumulates destination paths for Lightroom report.
    """
    destination_root: Path
    folder_nodes: list[FolderNode] = field(default_factory=list)
    phases: list[TransferPhase] = field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0
    measured_speed_mbs: float = 0.0
    estimated_seconds: float = 0.0
    is_phased: bool = False
    lightroom_paths: list[Path] = field(default_factory=list)

    @property
    def total_size_gb(self) -> float:
        """Total transfer size in gigabytes."""
        return self.total_size_bytes / (1024 ** 3)

    @property
    def phase_count(self) -> int:
        """Number of transfer phases."""
        return len(self.phases)
