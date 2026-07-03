from typing import List, Optional

import random as rn

from algorithm.algorithm_classes.Occ import Occ
from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers._cell_key_early import _cell_key_early
from algorithm.algorithm_helpers.initial_soft_hint_for_candidate import initial_soft_hint_for_candidate
from algorithm.algorithm_helpers.allowed_masks_for_task import allowed_masks_for_task
from algorithm.algorithm_helpers.can_place import can_place
from algorithm.algorithm_helpers.flexible_groups import build_flexible_group_options, is_flexible_mandatory_labsem
from algorithm.algorithm_helpers.task_segments import task_module_orders, logical_module_count
from app.models.TaskDTO import TaskDTO
from constants.algorithm import BOTH, VERY_LARGE_SCORE
from constants.parameters import GA_CONSTRUCT_CELL_TRIES
from helpers.task_module_target import module_target
from algorithm.hard_constraints.room_allows_task import room_pressure, parity_pressure


def construct_feasible_solution(tasks: List[TaskDTO], base_matrix, rooms, days, timeslots, cells_cache, order: List[int], teachers_availabilities, teacher_task_counts) -> \
List[Optional[Placement]]:
    """
    Builds a feasible timetable using the GA constructor

    Args:
        tasks: All tasks from the timetable instance
        base_matrix: Base matrix with blocked cells
        rooms: All available rooms
        days: All timetable days
        timeslots: All timetable timeslots
        cells_cache: Cached candidate cells by task
        order: Task construction order
        teachers_availabilities: Teacher availability rules
        teacher_task_counts: Number of tasks per teacher

    Returns:
        Constructed placement list with unplaced tasks left as None
    """

    n = len(tasks)

    bad = [i for i, c in enumerate(cells_cache) if not c]
    if bad:
        raise RuntimeError(f"Infeasible tasks (0 candidate cells): {bad[:30]}{'...' if len(bad) > 30 else ''}")

    occ = Occ()
    placed: List[Optional[Placement]] = [None] * n
    flexible_group_options = build_flexible_group_options(tasks)

    def group_week_mask_load(task_variant: TaskDTO, mask: int) -> int:
        if task_variant.category != "labsem" or logical_module_count(task_variant) != 1:
            return 0
        module = task_variant.modules[0]
        if int(module.numberOfHours or 0) != 1:
            return 0

        target = module_target(task_variant, 0)
        sy_ids = tuple(str(x) for x in (target.get("studyYearsIds") or ()))
        gi = target.get("groupIndex", task_variant.groupIndex)
        if not sy_ids or gi is None:
            return 0

        if mask == 1:
            return occ.sy_group_week_h.get((sy_ids[0], int(gi), "O"), 0)
        if mask == 2:
            return occ.sy_group_week_h.get((sy_ids[0], int(gi), "E"), 0)
        return 0

    for idx in order:
        t = tasks[idx]
        cells = cells_cache[idx]

        cells_sorted = sorted(
            cells,
            key=lambda rc: (
                room_pressure(occ, rc[1], [rc[0]]),
                _cell_key_early(rc, timeslots)
            )
        )

        if len(cells_sorted) <= GA_CONSTRUCT_CELL_TRIES:
            trial_cells = cells_sorted
        else:
            start = rn.randrange(0, len(cells_sorted))
            trial_cells = (cells_sorted[start:] + cells_sorted[:start])[:GA_CONSTRUCT_CELL_TRIES]

        m = t.modules[0]
        task_duration = int(t.durationHours or 0)

        module_orders = task_module_orders(t)
        one_hour_modules = [module for module in t.modules if module.numberOfHours == 1]
        parity_source = one_hour_modules[0] if one_hour_modules else m
        masks = allowed_masks_for_task(parity_source)
        if task_duration == 1 and logical_module_count(t) == 2 and all(module.numberOfHours == 1 for module in t.modules[:2]):
            masks = [BOTH]

        task_variants = [t]
        if is_flexible_mandatory_labsem(t):
            options = flexible_group_options.get(idx, [])
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

        best_pick: Optional[Placement] = None
        best_hint = (VERY_LARGE_SCORE,) * 8

        for (r, c) in trial_cells:
            if task_duration >= 2 and not one_hour_modules:
                for task_variant in task_variants:
                    if can_place(
                            occ, task_variant, r, c, BOTH, module_orders[0],
                            base_matrix, rooms, timeslots,
                            teachers_availabilities, teacher_task_counts, days
                    ):
                        hint = initial_soft_hint_for_candidate(occ, task_variant, r, BOTH, timeslots, teachers_availabilities)
                        if hint < best_hint:
                            best_hint = hint
                            best_pick = Placement(task=task_variant, row=r, col=c, parity_mask=BOTH, module_order=module_orders[0])
                continue

            ordered_variants = sorted(
                task_variants,
                key=lambda task_variant: (
                    min(group_week_mask_load(task_variant, mask) for mask in masks) if masks else 0,
                    int(task_variant.groupIndex or 0),
                ),
            )

            for task_variant in ordered_variants:
                masks_sorted = sorted(
                    masks,
                    key=lambda mask: (
                        group_week_mask_load(task_variant, mask),
                        parity_pressure(occ, r, c, mask),
                        mask
                    )
                )

                for mask in masks_sorted:
                    for module_order in module_orders:
                        if can_place(
                                occ, task_variant, r, c, mask, module_order,
                                base_matrix, rooms, timeslots,
                                teachers_availabilities, teacher_task_counts, days
                        ):
                            hint = initial_soft_hint_for_candidate(occ, task_variant, r, mask, timeslots, teachers_availabilities)
                            if hint < best_hint:
                                best_hint = hint
                                best_pick = Placement(task=task_variant, row=r, col=c, parity_mask=mask, module_order=module_order)

        if best_pick is None:
            continue

        placed[idx] = best_pick
        occ.add(best_pick, timeslots, teachers_availabilities)

    return placed
