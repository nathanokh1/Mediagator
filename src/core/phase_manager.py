"""
Mediagator — Phase manager.

Splits a TransferPlan into timed phases of ~45-minute chunks when the
estimated transfer duration exceeds 60 minutes.

Author: Nathan
"""

import logging

from src.config.constants import PHASE_TARGET_SECONDS
from src.models.folder_node import FolderNode
from src.models.transfer_phase import TransferPhase
from src.models.transfer_plan import TransferPlan

logger = logging.getLogger(__name__)


def build_phases(plan: TransferPlan) -> list[TransferPhase]:
    """Split plan folder nodes into ~45-minute transfer phases.

    Each phase accumulates folders until its estimated duration would exceed
    ``PHASE_TARGET_SECONDS``, then a new phase starts.  Single very large
    folders always get their own phase if they exceed the target alone.

    Args:
        plan: The transfer plan (must have ``measured_speed_mbs`` set).

    Returns:
        List of :class:`TransferPhase` objects in execution order.
    """
    if not plan.folder_nodes:
        return []

    speed_bytes_per_s = plan.measured_speed_mbs * 1024 * 1024
    if speed_bytes_per_s <= 0:
        speed_bytes_per_s = 50 * 1024 * 1024

    phases: list[TransferPhase] = []
    current_nodes: list[FolderNode] = []
    current_seconds: float = 0.0
    phase_num = 1

    for node in plan.folder_nodes:
        node_seconds = node.total_size_bytes / speed_bytes_per_s

        if current_nodes and (current_seconds + node_seconds) > PHASE_TARGET_SECONDS:
            phases.append(
                TransferPhase(
                    phase_number=phase_num,
                    folder_nodes=list(current_nodes),
                    estimated_seconds=current_seconds,
                )
            )
            phase_num += 1
            current_nodes = []
            current_seconds = 0.0

        current_nodes.append(node)
        current_seconds += node_seconds

    if current_nodes:
        phases.append(
            TransferPhase(
                phase_number=phase_num,
                folder_nodes=list(current_nodes),
                estimated_seconds=current_seconds,
            )
        )

    logger.info("Phase manager created %d phase(s).", len(phases))
    return phases
