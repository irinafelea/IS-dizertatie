from typing import Dict, List, Optional, Tuple

from algorithm.algorithm_classes.Placement import Placement
from constants.algorithm import EVEN, ODD
from constants.penalties import PEN_ROOM_SINGLE_PARITY_ONE_HOUR
from helpers.module import module_hours


def room_single_parity_one_hour_penalty(placements: List[Optional[Placement]]) -> tuple[int, int]:
    """
    Computes the single-parity one-hour room penalty

    Args:
        placements: Current placement list

    Returns:
        Penalty and violation count
    """
    room_row_mask: Dict[Tuple[int, int], int] = {}

    for placement in placements:
        if placement is None:
            continue
        if placement.task.online:
            continue
        if module_hours(placement.module) != 1:
            continue

        key = (placement.row, placement.col)
        room_row_mask[key] = room_row_mask.get(key, 0) | placement.parity_mask

    count = sum(1 for mask in room_row_mask.values() if mask in (ODD, EVEN))
    return count * PEN_ROOM_SINGLE_PARITY_ONE_HOUR, count
