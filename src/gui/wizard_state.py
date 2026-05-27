"""
Mediagator — Shared wizard state.

WizardState is the single source of truth threaded through every step.

Author: Nathan
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.models.scan_result import ScanResult, DriveInfo
from src.models.transfer_plan import TransferPlan
from src.core.transfer_engine import TransferStats
from src.core.hardware_profile import HardwareProfile
from src.config.constants import DEFAULT_SELECTED_EXTENSIONS, DEFAULT_ORG_MODE


@dataclass
class WizardState:
    """Mutable container shared across all 8 wizard steps.

    Attributes:
        settings: Loaded user settings dict.
        available_drives: Drives discovered at startup.
        selected_scan_folders: Explicit list of folders chosen in Step 1 to scan.
        scan_result: Output of the initial drive scan.
        destination_root: Chosen destination folder.
        hardware_profile: Detected hardware config and optimal transfer settings.
        transfer_plan: Fully built transfer plan.
        transfer_stats: Statistics produced after transfer completes.
        checked_folder_paths: Paths the user has kept checked in Step 4.
        current_phase_index: 0-based index of the active transfer phase.
    """
    settings: dict[str, Any] = field(default_factory=dict)
    available_drives: list[DriveInfo] = field(default_factory=list)
    selected_scan_folders: list[Path] = field(default_factory=list)
    selected_extensions: set[str] = field(default_factory=lambda: set(DEFAULT_SELECTED_EXTENSIONS))
    scan_result: ScanResult | None = None
    destination_root: Path | None = None
    org_mode: str = ""          # empty = not yet chosen; set when user picks a mode
    hardware_profile: HardwareProfile | None = None
    transfer_plan: TransferPlan | None = None
    transfer_stats: TransferStats | None = None
    checked_folder_paths: set[Path] = field(default_factory=set)
    current_phase_index: int = 0
