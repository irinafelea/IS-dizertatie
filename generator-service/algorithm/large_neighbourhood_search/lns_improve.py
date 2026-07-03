import os
import time
from typing import List, Optional, Tuple

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_classes.Progress import Progress
from algorithm.algorithm_score.score_solution import score_solution, score_solution_breakdown
from algorithm.simulated_annealing.lns_accept_move import lns_accept_move
from algorithm.large_neighbourhood_search.lns_adaptive_selection import (
    init_ucb_state,
    choose_ucb_option,
    update_ucb_state,
    normalized_reward,
)
from algorithm.large_neighbourhood_search.lns_pick_remove_placements import (
    lns_pick_remove_placements,
)
from algorithm.large_neighbourhood_search.lns_placement_consensus_ratio import summarize_stable_assignments
from algorithm.large_neighbourhood_search.lns_repair_portfolio import repair_removed_tasks
from app.models.TaskDTO import TaskDTO
from app.utils.build_cache_cells import build_cells_cache
from constants.parameters import (
    SA_INITIAL_TEMPERATURE,
    SA_COOLING_RATE,
    LNS_DESTROY_OPERATORS,
    LNS_REPAIR_OPERATORS,
    LNS_REMOVAL_SIZE_OPTIONS,
)



def lns_improve(
        placements: List[Optional[Placement]],
        tasks: List[TaskDTO],
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache: List[List[Tuple[int, int]]],
        teacher_availabilities,
        teacher_task_counts,
        iters,
        log_every: int = 10,
        enforce_bachelor_third_year_free_day: bool = False,
        metrics: dict | None = None,
        elite_placement_frequencies: dict | None = None,
) -> List[Optional[Placement]]:
    """
    Improves a timetable with large neighbourhood search

    Args:
        placements: Initial placement list
        tasks: All tasks from the timetable instance
        base_matrix: Base matrix with blocked cells
        rooms: All available rooms
        days: All timetable days
        timeslots: All timetable timeslots
        cells_cache: Cached candidate cells by task
        teacher_availabilities: Teacher availability rules
        teacher_task_counts: Number of tasks per teacher
        iters: Number of LNS iterations
        log_every: Progress logging interval
        enforce_bachelor_third_year_free_day: Whether to enforce third-year free-day penalties
        metrics: Mutable metrics output map
        elite_placement_frequencies: Elite placement frequencies from GA

    Returns:
        Best placement list found by LNS
    """

    def print_breakdown(label: str, solution: List[Optional[Placement]]):
        """
        Prints the score breakdown for a solution

        Args:
            label: Log label prefix
            solution: Solution to inspect

        Returns:
            None
        """
        breakdown = score_solution_breakdown(
            solution,
            timeslots,
            teacher_availabilities,
            enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
        )
        print(f"[{label}] breakdown:")
        for key, value in breakdown.items():
            print(f"[{label}] {key}={value}")

    t0 = time.perf_counter()
    best_time_seconds = 0.0

    if len(cells_cache) != len(tasks) or any(c is None for c in cells_cache):
        cells_cache = build_cells_cache(
            tasks,
            base_matrix,
            rooms,
            days,
            timeslots,
            teacher_availabilities,
            teacher_task_counts,
        )

    cur = placements.copy()
    cur_score = score_solution(
        cur,
        timeslots,
        teacher_availabilities,
        enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
    )

    fin_best = cur.copy()
    fin_best_score = cur_score

    temp = SA_INITIAL_TEMPERATURE

    prog = Progress("LNS", every=log_every)
    history = metrics.setdefault("lns_history", []) if metrics is not None else None
    destroy_selector = init_ucb_state(LNS_DESTROY_OPERATORS)
    repair_selector = init_ucb_state(LNS_REPAIR_OPERATORS)
    size_selector = init_ucb_state([str(k) for k in LNS_REMOVAL_SIZE_OPTIONS])

    if metrics is not None:
        metrics["lns_destroy_operator_choices"] = []
        metrics["lns_repair_operator_choices"] = []

    it = 1
    stagnation = 0
    while it <= iters:
        cand = cur.copy()

        destroy_mode = (os.getenv("LNS_DESTROY_MODE") or "adaptive").strip().lower()
        repair_mode = (os.getenv("LNS_REPAIR_MODE") or "adaptive").strip().lower()
        size_mode = (os.getenv("LNS_SIZE_MODE") or "adaptive").strip().lower()

        destroy_operator = choose_ucb_option(destroy_selector, LNS_DESTROY_OPERATORS) if destroy_mode == "adaptive" else destroy_mode
        repair_operator = choose_ucb_option(repair_selector, LNS_REPAIR_OPERATORS) if repair_mode == "adaptive" else repair_mode
        size_arm = choose_ucb_option(size_selector, [str(k) for k in LNS_REMOVAL_SIZE_OPTIONS]) if size_mode == "adaptive" else size_mode

        remove_k = int(size_arm)
        if stagnation >= 25:
            remove_k = max(remove_k, LNS_REMOVAL_SIZE_OPTIONS[-1])

        # Destroy
        original_cand = cand.copy()
        remove = lns_pick_remove_placements(
            cand,
            timeslots,
            teacher_availabilities,
            tasks=tasks,
            enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
            remove_k=remove_k,
            elite_placement_frequencies=elite_placement_frequencies,
            destroy_operator=destroy_operator,
        )
        for idx in remove:
            cand[idx] = None

        # Repair
        prev_cur_score = cur_score
        repaired_count, unrepaired_count = repair_removed_tasks(
            remove,
            tasks,
            cand,
            base_matrix,
            rooms,
            days,
            timeslots,
            cells_cache,
            teacher_availabilities,
            teacher_task_counts,
            repair_operator=repair_operator,
            enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
            original_placements=original_cand,
        )

        accepted = False
        cand_score = cur_score
        improved_best = False

        if repaired_count > 0:
            cand_score = score_solution(
                cand,
                timeslots,
                teacher_availabilities,
                enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
            )
            accepted = lns_accept_move(cand_score, cur_score, temp)
            if accepted:
                cur = cand
                cur_score = cand_score

                if cur_score < fin_best_score:
                    fin_best = cur.copy()
                    fin_best_score = cur_score
                    improved_best = True
                    best_time_seconds = time.perf_counter() - t0
                    stagnation = 0
                    print_breakdown("LNS-BEST", fin_best)
                else:
                    stagnation += 1
            else:
                stagnation += 1
        else:
            stagnation += 1

        reward = normalized_reward(prev_cur_score, cand_score, accepted, improved_best)
        if destroy_mode == "adaptive":
            update_ucb_state(destroy_selector, destroy_operator, reward)
        if repair_mode == "adaptive":
            update_ucb_state(repair_selector, repair_operator, reward)
        if size_mode == "adaptive":
            update_ucb_state(size_selector, str(remove_k), reward)

        prog.tick(
            best_score=fin_best_score,
            cur_score=cur_score,
            accepted=accepted,
            removed_k=len(remove),
        )

        if metrics is not None:
            metrics.setdefault("lns_destroy_operator_choices", []).append(destroy_operator)
            metrics.setdefault("lns_repair_operator_choices", []).append(repair_operator)

        if history is not None and (it % 50 == 0 or it == iters):
            stable_assignment_stats = summarize_stable_assignments(elite_placement_frequencies, cur)
            history.append(
                {
                    "iteration": it,
                    "elapsed_seconds": round(time.perf_counter() - t0, 4),
                    "best_fitness": fin_best_score,
                    "current_fitness": cur_score,
                    "destroy_operator": destroy_operator,
                    "repair_operator": repair_operator,
                    "remove_k": remove_k,
                    "accepted": bool(accepted),
                    "reward": reward,
                    "repaired_count": repaired_count,
                    "unrepaired_count": unrepaired_count,
                    "stable_assignment_count": stable_assignment_stats["stable_assignment_count"],
                    "stable_assignment_ratio": stable_assignment_stats["stable_assignment_ratio"],
                    "destroy_mode": destroy_mode,
                    "repair_mode": repair_mode,
                    "size_mode": size_mode,
                    "destroy_counts": dict(destroy_selector.get("counts", {})),
                    "repair_counts": dict(repair_selector.get("counts", {})),
                    "size_counts": dict(size_selector.get("counts", {})),
                }
            )

        temp *= SA_COOLING_RATE
        it += 1

    if metrics is not None:
        metrics["lns_destroy_selector"] = destroy_selector
        metrics["lns_repair_selector"] = repair_selector
        metrics["lns_size_selector"] = size_selector
        metrics["time_to_best_seconds"] = round(best_time_seconds, 4)

    print_breakdown("LNS-FINAL", fin_best)
    return fin_best
