"""
Mediagator — TransferPhase model.

Represents a single timed phase of a multi-phase transfer.

Author: Nathan
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

from src.models.folder_node import FolderNode


class PhaseStatus(str, Enum):
    """Lifecycle status of a transfer phase."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class TransferPhase:
    """A chunk of folders transferred together.

    Attributes:
        phase_number: 1-based index.
        folder_nodes: Folders assigned to this phase.
        status: Current phase status.
        estimated_seconds: Rough duration estimate for this phase.
    """
    phase_number: int
    folder_nodes: list[FolderNode] = field(default_factory=list)
    status: PhaseStatus = PhaseStatus.PENDING
    estimated_seconds: float = 0.0

    @property
    def total_files(self) -> int:
        """Total files in this phase."""
        return sum(n.file_count for n in self.folder_nodes)

    @property
    def total_size_bytes(self) -> int:
        """Total bytes in this phase."""
        return sum(n.total_size_bytes for n in self.folder_nodes)

    @property
    def folder_count(self) -> int:
        """Number of folders in this phase."""
        return len(self.folder_nodes)
