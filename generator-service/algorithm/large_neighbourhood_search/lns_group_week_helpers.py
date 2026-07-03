from __future__ import annotations

from typing import Optional

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers.task_segments import iter_task_segments, logical_module_count
from constants.algorithm import EVEN, ODD
from helpers.module import is_course, module_hours
from helpers.task_module_target import module_target

GroupWeekCounts = dict[tuple[str, int], dict[str, int]]


def build_group_week_counts(placements: list[Optional[Placement]]) -> GroupWeekCounts:
    """
    Builds odd and even week counts by study year group

    Args:
        placements: Current placement list

    Returns:
        Week counts indexed by study year and group
    """
    group_week_counts: GroupWeekCounts = {}

    for placement in placements:
        if placement is None:
            continue

        task = placement.task
        if task.category != "labsem":
            continue

        for module, _row, mask, module_index in iter_task_segments(
            task,
            placement.row,
            placement.parity_mask,
            placement.module_order,
        ):
            if module_hours(module) != 1 or is_course(module):
                continue

            target = module_target(task, module_index)
            study_year_ids = tuple(str(x) for x in (target.get("studyYearsIds") or ()))
            group_index = target.get("groupIndex", task.groupIndex)
            if not study_year_ids or group_index is None:
                continue

            key = (study_year_ids[0], int(group_index))
            bucket = group_week_counts.setdefault(key, {"O": 0, "E": 0})
            if mask & ODD:
                bucket["O"] += 1
            if mask & EVEN:
                bucket["E"] += 1

    return group_week_counts


def compute_parity_imbalance_impact(
    group_week_counts: GroupWeekCounts,
    placement: Optional[Placement],
) -> int:
    """
    Computes the parity imbalance impact of one placement

    Args:
        group_week_counts: Current odd and even week counts
        placement: Placement being evaluated

    Returns:
        Imbalance impact contributed by the placement
    """
    if placement is None:
        return 0

    task = placement.task
    if task.category != "labsem":
        return 0

    imbalance = 0
    for module, _row, mask, module_index in iter_task_segments(
        task,
        placement.row,
        placement.parity_mask,
        placement.module_order,
    ):
        if module_hours(module) != 1 or is_course(module):
            continue

        target = module_target(task, module_index)
        study_year_ids = tuple(str(x) for x in (target.get("studyYearsIds") or ()))
        group_index = target.get("groupIndex", task.groupIndex)
        if not study_year_ids or group_index is None:
            continue

        counts = group_week_counts.get((study_year_ids[0], int(group_index)))
        if not counts:
            continue

        odd_count = int(counts["O"])
        even_count = int(counts["E"])
        if (mask & ODD) and odd_count > even_count:
            imbalance += odd_count - even_count
        if (mask & EVEN) and even_count > odd_count:
            imbalance += even_count - odd_count

    return imbalance


def group_week_mask_load(task, occupancy, mask: int) -> int:
    """
    Returns the current week load for a task and parity mask

    Args:
        task: Task being evaluated
        occupancy: Current occupancy state
        mask: Candidate parity mask

    Returns:
        Current load for the task group and parity
    """
    if task.category != "labsem" or logical_module_count(task) != 1:
        return 0

    module = task.modules[0]
    if int(module_hours(module) or 0) != 1:
        return 0

    target = module_target(task, 0)
    study_year_ids = tuple(str(x) for x in (target.get("studyYearsIds") or ()))
    group_index = target.get("groupIndex", task.groupIndex)
    if not study_year_ids or group_index is None:
        return 0

    if mask == ODD:
        return occupancy.sy_group_week_h.get((study_year_ids[0], int(group_index), "O"), 0)
    if mask == EVEN:
        return occupancy.sy_group_week_h.get((study_year_ids[0], int(group_index), "E"), 0)
    return 0
