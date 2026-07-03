from typing import Optional

from algorithm.algorithm_classes.Placement import Placement
from constants.penalties import PEN_UNPLACED


def unplaced_penalty(placements: list[Optional[Placement]]) -> tuple[int, int]:
    """
    Calculates the penalty for unplaced tasks

    Args:
        placements: Current placements list

    Returns:
        Penalty and unplaced count
    """
    unplaced_count = sum(1 for placement in placements if placement is None)
    return unplaced_count * PEN_UNPLACED, unplaced_count
