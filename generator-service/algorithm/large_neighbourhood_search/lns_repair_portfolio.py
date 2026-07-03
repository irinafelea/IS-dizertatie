from __future__ import annotations

from typing import List, Optional, Tuple
import random as rn

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers._cell_key_early import _cell_key_early
from algorithm.algorithm_helpers.allowed_masks_for_task import allowed_masks_for_task
from algorithm.algorithm_helpers.can_place import can_place
from algorithm.algorithm_helpers.flexible_groups import build_flexible_group_options, is_flexible_mandatory_labsem
from algorithm.algorithm_helpers.rebuild_occ import rebuild_occ
from algorithm.algorithm_helpers.task_priority import task_priority
from algorithm.algorithm_helpers.task_segments import task_module_orders, logical_module_count
from algorithm.large_neighbourhood_search.lns_group_week_helpers import group_week_mask_load
from algorithm.large_neighbourhood_search.repair_soft_hint_for_candidate import repair_soft_hint_for_candidate
from algorithm.algorithm_score.score_solution import score_solution
from app.models.TaskDTO import TaskDTO
from constants.algorithm import BOTH
from constants.parameters import LNS_REINSERTION_TRY_LIMIT
from helpers.module import module_hours


def _candidate_payloads_for_task(
        i: int,
        tasks: List[TaskDTO],
        placements: List[Optional[Placement]],
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache: List[List[Tuple[int, int]]],
        teachers_availabilities,
        teacher_task_counts,
        top_k: int = 2,
):
    """
    Builds the top reinsertion candidates for one removed task

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
        top_k: Number of distinct candidates to keep

    Returns:
        Ranked reinsertion candidates with fast hints
    """
    t = tasks[i]
    cells = cells_cache[i]
    if not cells:
        return []

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

    ranked: list[tuple[Tuple[int, ...], Placement]] = []

    for (r, c) in trial_cells:
        if module_hours(m) >= 2 and not one_hour_modules:
            for task_variant in task_variants:
                if can_place(occ, task_variant, r, c, BOTH, module_orders[0], base_matrix, rooms, timeslots, teachers_availabilities,
                             teacher_task_counts, days=days):
                    hint = repair_soft_hint_for_candidate(occ, task_variant, r, c, BOTH, timeslots, teachers_availabilities)
                    ranked.append((hint, Placement(task=task_variant, row=r, col=c, parity_mask=BOTH, module_order=module_orders[0])))
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
                        ranked.append((hint, Placement(task=task_variant, row=r, col=c, parity_mask=mask, module_order=module_order)))

    if not ranked:
        return []

    ranked.sort(key=lambda item: item[0])
    unique_candidates: list[tuple[Tuple[int, ...], Placement]] = []
    seen = set()
    for hint, placement in ranked:
        module_order_key = tuple(int(x) for x in (placement.module_order or ()))
        key = (
            placement.row,
            placement.col,
            int(placement.parity_mask),
        module_order_key,
        int(placement.task.groupIndex or 0),
        int(placement.task.groupSpan or 1),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append((hint, placement))
        if len(unique_candidates) >= top_k:
            break
    return unique_candidates


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
    Reinserts one removed task using the repair portfolio

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
    candidates = _candidate_payloads_for_task(
        i, tasks, placements, base_matrix, rooms, days, timeslots, cells_cache, teachers_availabilities, teacher_task_counts, top_k=1
    )
    if not candidates:
        return False
    placements[i] = candidates[0][1]
    return True


def repair_removed_tasks(
        removed_indices: List[int],
        tasks: List[TaskDTO],
        placements: List[Optional[Placement]],
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache: List[List[Tuple[int, int]]],
        teachers_availabilities,
        teacher_task_counts,
        repair_operator: str = "greedy",
        enforce_bachelor_third_year_free_day: bool = False,
        original_placements: List[Optional[Placement]] | None = None,
) -> tuple[int, int]:
    """
    Repairs the tasks removed during the LNS destroy phase

    Args:
        removed_indices: Task indices removed during destroy
        tasks: All tasks from the timetable instance
        placements: Current placement list
        base_matrix: Base matrix with blocked cells
        rooms: All available rooms
        days: All timetable days
        timeslots: All timetable timeslots
        cells_cache: Cached candidate cells by task
        teachers_availabilities: Teacher availability rules
        teacher_task_counts: Number of tasks per teacher
        repair_operator: Repair strategy to use
        enforce_bachelor_third_year_free_day: Whether to enforce third-year free-day penalties
        original_placements: Placements before the destroy phase

    Returns:
        Repaired count and unrepaired count
    """
    repaired_count = 0
    unrepaired_count = 0

    def restore_original(idx: int) -> None:
        """
        Restores the original placement when repair fails

        Args:
            idx: Task index to restore

        Returns:
            None
        """
        nonlocal unrepaired_count
        placements[idx] = None
        original = original_placements[idx] if original_placements is not None else None
        if original is not None:
            occ = rebuild_occ(placements, timeslots, teachers_availabilities)
            if can_place(
                occ,
                original.task,
                original.row,
                original.col,
                original.parity_mask,
                original.module_order,
                base_matrix,
                rooms,
                timeslots,
                teachers_availabilities,
                teacher_task_counts,
                days=days,
            ):
                placements[idx] = original
        unrepaired_count += 1

    def choose_best_exact(idx: int, candidates: list[tuple[Tuple[int, ...], Placement]]) -> Optional[Placement]:
        """
        Selects the best candidate by exact score evaluation

        Args:
            idx: Task index being reinserted
            candidates: Ranked fast-hint candidates

        Returns:
            Best exact-scoring placement or None
        """
        if not candidates:
            return None
        best_score = None
        best_hint = None
        best_placement = None
        saved = placements[idx]
        for hint, candidate in candidates:
            placements[idx] = candidate
            exact = score_solution(
                placements,
                timeslots,
                teachers_availabilities,
                enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
            )
            if best_score is None or (exact, hint) < (best_score, best_hint):
                best_score = exact
                best_hint = hint
                best_placement = candidate
        placements[idx] = saved
        return best_placement

    if repair_operator == "greedy":
        remove_sorted = sorted(removed_indices, key=lambda i: task_priority(tasks[i], len(cells_cache[i]), cells_cache[i]))
        for idx in remove_sorted:
            candidates = _candidate_payloads_for_task(
                idx, tasks, placements, base_matrix, rooms, days, timeslots, cells_cache, teachers_availabilities, teacher_task_counts, top_k=3
            )
            best = choose_best_exact(idx, candidates)
            if best is None:
                restore_original(idx)
                continue
            placements[idx] = best
            repaired_count += 1
        return repaired_count, unrepaired_count

    pending = set(removed_indices)
    while pending:
        best_idx = None
        best_key = None
        best_candidates = None

        for idx in list(pending):
            candidates = _candidate_payloads_for_task(
                idx, tasks, placements, base_matrix, rooms, days, timeslots, cells_cache, teachers_availabilities, teacher_task_counts, top_k=3
            )
            if not candidates:
                restore_original(idx)
                pending.remove(idx)
                continue

            saved = placements[idx]
            scored: list[tuple[int, Tuple[int, ...], Placement]] = []
            for hint, candidate in candidates:
                placements[idx] = candidate
                exact = score_solution(
                    placements,
                    timeslots,
                    teachers_availabilities,
                    enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
                )
                scored.append((exact, hint, candidate))
            placements[idx] = saved
            scored.sort(key=lambda item: (item[0], item[1]))

            first_score = scored[0][0]
            second_score = scored[1][0] if len(scored) > 1 else first_score + 10 ** 9
            regret = second_score - first_score

            def _descending_sortable(value):
                if isinstance(value, tuple):
                    return tuple(_descending_sortable(v) for v in value)
                return -value if isinstance(value, (int, float)) else value

            priority = task_priority(tasks[idx], len(cells_cache[idx]), cells_cache[idx])
            priority_key = _descending_sortable(priority)
            key = (regret, -first_score, priority_key)
            if best_key is None or key > best_key:
                best_key = key
                best_idx = idx
                best_candidates = scored

        if best_idx is None or not best_candidates:
            break

        placements[best_idx] = best_candidates[0][2]
        repaired_count += 1
        pending.remove(best_idx)

    for idx in pending:
        restore_original(idx)

    return repaired_count, unrepaired_count
