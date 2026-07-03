from typing import Dict, List

from app.models.TaskDTO import TaskDTO
from constants.algorithm import EVEN, ODD


def build_one_hour_pair_index(tasks: List[TaskDTO]) -> Dict[int, int]:
    """
    Builds the partner index for paired one-hour tasks

    Args:
        tasks: All tasks from the timetable instance

    Returns:
        Mapping from task index to paired task index
    """
    grouped: Dict[str, List[int]] = {}
    out: Dict[int, int] = {}

    for idx, task in enumerate(tasks):
        if int(task.durationHours or 0) != 1:
            continue
        pair_key = str(task.pairGroupKey or "").strip()
        if not pair_key:
            continue
        grouped.setdefault(pair_key, []).append(idx)

    for indices in grouped.values():
        if len(indices) != 2:
            continue
        left, right = indices
        out[left] = right
        out[right] = left

    return out


def opposite_single_masks(masks: List[int]) -> List[tuple[int, int]]:
    """
    Builds opposite odd and even mask pairs

    Args:
        masks: Available single-week masks

    Returns:
        Odd and even mask pairs in the order they should be tried
    """
    pairs: List[tuple[int, int]] = []

    for mask in masks:
        if mask == ODD:
            pairs.append((ODD, EVEN))
        elif mask == EVEN:
            pairs.append((EVEN, ODD))

    return pairs
