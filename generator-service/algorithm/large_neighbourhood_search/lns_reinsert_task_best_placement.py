from typing import Optional, List, Tuple

import random as rn

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers._cell_key_early import _cell_key_early
from algorithm.algorithm_helpers.allowed_masks_for_task import allowed_masks_for_task
from algorithm.algorithm_helpers.can_place import can_place
from algorithm.algorithm_helpers.flexible_groups import build_flexible_group_options, is_flexible_mandatory_labsem
from algorithm.algorithm_helpers.rebuild_occ import rebuild_occ
from algorithm.algorithm_helpers.task_segments import task_module_orders, logical_module_count
from algorithm.large_neighbourhood_search.lns_group_week_helpers import group_week_mask_load
from algorithm.large_neighbourhood_search.repair_soft_hint_for_candidate import repair_soft_hint_for_candidate
from app.models.TaskDTO import TaskDTO
from constants.algorithm import BOTH, VERY_LARGE_SCORE
from constants.parameters import LNS_REINSERTION_TRY_LIMIT
from helpers.module import module_hours


def lns_reinsert_task_best_placement(
        i: int,
        tasks: List[TaskDTO],
        placements: List[Optional[Placement]],
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache: List[List[Tuple[int, int]]],
        teachers_availabilities,
        teacher_task_counts
) -> bool:
    """
    Reinserts one removed task with the best fast-hint candidate

    Args:
        i: Task index to reinsert
        tasks: All tasks from the timetable instance
        placements: Current placement list
        base_matrix: Base matrix with blocked cells
        rooms: All available rooms
        days: All timetable days
        timeslots: All timetable timeslots
        cells_cache: Cached candidate cells by task
        teachers_availabilities: Teacher availability rules
        teacher_task_counts: Number of tasks per teacher

    Returns:
        True if the task was successfully reinserted
    """

    t = tasks[i]
    cells = cells_cache[i]
    if not cells:
        return False

    occ = rebuild_occ(placements, timeslots, teachers_availabilities)
    flexible_group_options = build_flexible_group_options(tasks)

    cells_sorted = sorted(cells, key=lambda rc: _cell_key_early(rc, timeslots))
    start = rn.randrange(0, len(cells_sorted))
    trial_cells = (cells_sorted[start:] + cells_sorted[:start])[:LNS_REINSERTION_TRY_LIMIT]

    m = t.modules[0]
    module_orders = task_module_orders(t)
    one_hour_modules = [module for module in t.modules if module_hours(module) == 1]
    parity_source = one_hour_modules[0] if one_hour_modules else m
    masks = allowed_masks_for_task(parity_source)
    if int(t.durationHours or 0) == 1 and logical_module_count(t) == 2 and all(module_hours(module) == 1 for module in t.modules[:2]):
        masks = [BOTH]
    task_variants = [t]
    if is_flexible_mandatory_labsem(t):
        options = flexible_group_options.get(i, [])
        task_variants = [
            t.model_copy(
                update={
                    "groupIndex": option["groupIndex"],
                    "groupSpan": option["groupSpan"],
                    "numberOfStudents": option["numberOfStudents"],
                },
                deep=True,
            )
            for option in options
        ] or [t]

    best_p: Optional[Placement] = None
    best_hint = (VERY_LARGE_SCORE,) * 10

    for (r, c) in trial_cells:
        if module_hours(m) >= 2 and not one_hour_modules:
            for task_variant in task_variants:
                if can_place(occ, task_variant, r, c, BOTH, module_orders[0], base_matrix, rooms, timeslots, teachers_availabilities,
                             teacher_task_counts, days=days):
                    hint = repair_soft_hint_for_candidate(occ, task_variant, r, c, BOTH, timeslots, teachers_availabilities)
                    if hint < best_hint:
                        best_hint = hint
                        best_p = Placement(task=task_variant, row=r, col=c, parity_mask=BOTH, module_order=module_orders[0])
            continue

        ordered_variants = sorted(
            task_variants,
            key=lambda task_variant: (
                min(group_week_mask_load(task_variant, occ, mask) for mask in masks) if masks else 0,
                int(task_variant.groupIndex or 0),
            ),
        )

        for task_variant in ordered_variants:
            masks_sorted = sorted(
                masks,
                key=lambda mask: (
                    group_week_mask_load(task_variant, occ, mask),
                    mask,
                ),
            )
            for mask in masks_sorted:
                for module_order in module_orders:
                    if can_place(occ, task_variant, r, c, mask, module_order, base_matrix, rooms, timeslots, teachers_availabilities,
                                 teacher_task_counts, days=days):
                        hint = repair_soft_hint_for_candidate(occ, task_variant, r, c, mask, timeslots, teachers_availabilities)
                        if hint < best_hint:
                            best_hint = hint
                            best_p = Placement(task=task_variant, row=r, col=c, parity_mask=mask, module_order=module_order)

    if best_p is None:
        return False

    placements[i] = best_p
    return True
