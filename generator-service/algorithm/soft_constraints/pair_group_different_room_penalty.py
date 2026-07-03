from typing import Dict, List, Optional, Set

from algorithm.algorithm_classes.Placement import Placement
from constants.penalties import PEN_PAIR_GROUP_DIFFERENT_ROOM


def pair_group_different_room_penalty(placements: List[Optional[Placement]]) -> tuple[int, int]:
    """
    Computes the paired-group different-room penalty

    Args:
        placements: Current placement list

    Returns:
        Penalty and violation count
    """
    rooms_by_pair: Dict[str, Set[int]] = {}

    for placement in placements:
        if placement is None:
            continue

        task = placement.task
        pair_key = task.pairGroupKey
        if not pair_key or task.durationHours != 1:
            continue

        rooms_by_pair.setdefault(pair_key, set()).add(placement.col)

    penalty = 0
    count = 0
    for room_set in rooms_by_pair.values():
        if len(room_set) > 1:
            penalty += (len(room_set) - 1) * PEN_PAIR_GROUP_DIFFERENT_ROOM
            count += 1

    return penalty, count
