from collections import defaultdict
from typing import List, Optional

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers.task_segments import iter_task_segments
from constants.algorithm import ODD, EVEN
from constants.penalties import PEN_GROUP_WEEK_PARITY_IMBALANCE
from helpers.module import is_course, module_hours
from helpers.task_module_target import module_target


def group_week_parity_imbalance_penalty(
    placements: List[Optional[Placement]],
) -> tuple[int, int]:
    """
    Computes the group week parity imbalance penalty

    Args:
        placements: Current placement list

    Returns:
        Penalty and imbalance count
    """
    counts = defaultdict(lambda: {"O": 0, "E": 0})

    for placement in placements:
        if placement is None:
            continue

        task = placement.task
        if task.category != "labsem":
            continue

        segments = iter_task_segments(task, placement.row, placement.parity_mask, placement.module_order)
        for module, _row, mask, module_index in segments:
            if module_hours(module) != 1:
                continue
            if is_course(module):
                continue

            target = module_target(task, module_index)
            sy_ids = tuple(str(x) for x in (target.get("studyYearsIds") or ()))
            if not sy_ids:
                continue
            gi = target.get("groupIndex", task.groupIndex)
            if gi is None:
                continue

            key = (sy_ids[0], int(gi))
            if mask & ODD:
                counts[key]["O"] += 1
            if mask & EVEN:
                counts[key]["E"] += 1

    imbalance = 0
    for values in counts.values():
        imbalance += abs(int(values["O"]) - int(values["E"]))

    return imbalance * PEN_GROUP_WEEK_PARITY_IMBALANCE, imbalance
