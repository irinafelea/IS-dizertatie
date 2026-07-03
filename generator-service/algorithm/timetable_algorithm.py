import os
import random
import time
from typing import List, Any

from algorithm.algorithm_score.score_solution import score_solution, score_solution_breakdown
from algorithm.genetic_algorithm.ga_search_initial_solution import ga_search_best_initial_solution
from algorithm.large_neighbourhood_search.lns_improve import lns_improve
from app.models.DayDTO import DayDTO
from app.models.RoomDTO import RoomDTO
from app.models.TaskDTO import TaskDTO
from app.models.TimeslotDTO import TimeslotDTO
from app.utils.build_unplaced_tasks_message import build_unplaced_summary_message
from constants.parameters import LNS_FINAL_ITERATIONS


def timetable_algorithm(tasks: List[TaskDTO], base_matrix: list[list[Any | None]], rooms: list[RoomDTO],
                        days: list[DayDTO], timeslots: list[TimeslotDTO], cells_cache: list[list[tuple[int, int]]],
                        teachers_availabilities: dict[str, dict], teacher_task_counts,
                        enforce_bachelor_third_year_free_day: bool = False, seed: int | None = None):
    t_start = time.perf_counter()
    metrics: dict[str, Any] = {"lns_history": []}

    if seed is None:
        raw_seed = (os.getenv("TIMETABLE_SEED") or "").strip()
        if raw_seed:
            try:
                seed = int(raw_seed)
            except ValueError:
                print(f"[SEED] ignoring invalid TIMETABLE_SEED={raw_seed!r}")
                seed = None

    if seed is not None:
        random.seed(seed)
        try:
            import numpy as np  # optional
            np.random.seed(seed)
        except Exception:
            pass
        print(f"[SEED] using seed={seed}")

    metrics["seed"] = seed
    metrics["instance_name"] = (os.getenv("TIMETABLE_INSTANCE_NAME") or "").strip()
    metrics["method_name"] = ((os.getenv("TIMETABLE_METHOD_NAME") or "").strip() or "initial")
    metrics["lns_destroy_mode"] = (os.getenv("LNS_DESTROY_MODE") or "adaptive").strip().lower()
    metrics["lns_repair_mode"] = (os.getenv("LNS_REPAIR_MODE") or "adaptive").strip().lower()
    metrics["lns_size_mode"] = (os.getenv("LNS_SIZE_MODE") or "adaptive").strip().lower()

    print("\n-------------------------------- START ------------------------------------ ")
    t_start_ga = time.perf_counter()
    initial, ga_fit, ga_metadata = ga_search_best_initial_solution(
        tasks,
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache,
        teachers_availabilities,
        teacher_task_counts,
        enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
    )
    ga_runtime_seconds = time.perf_counter() - t_start_ga

    if any(p is None for p in initial):
        message = build_unplaced_summary_message(tasks, initial)
        # raise RuntimeError(message)
        print(message)
    print(
        f"[GA-INIT] fitness={ga_fit} score={score_solution(initial, timeslots, teachers_availabilities, enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day)}"
    )
    metrics["ga_final_fitness"] = ga_fit
    metrics["ga_final_runtime"] = round(ga_runtime_seconds, 4)
    metrics["ga_elite_solution_count"] = int((ga_metadata or {}).get("elite_solution_count") or 0)

    t_start_lns = time.perf_counter()
    best = lns_improve(
        initial,
        tasks,
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache,
        teachers_availabilities,
        teacher_task_counts,
        iters=LNS_FINAL_ITERATIONS,
        enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
        metrics=metrics,
        elite_placement_frequencies=(
            (ga_metadata or {}).get("elite_placement_frequencies")
            or (ga_metadata or {}).get("population_consensus")
        ),
    )
    lns_runtime_seconds = time.perf_counter() - t_start_lns

    final_breakdown = score_solution_breakdown(
        best,
        timeslots,
        teachers_availabilities,
        enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
    )
    final_fitness = final_breakdown["total"]
    print(f"[FINAL] penalty={final_fitness}")

    t_end = time.perf_counter()
    print(f"[TOTAL] runtime = {t_end - t_start:.2f} s")
    metrics["final_breakdown"] = final_breakdown
    metrics["lns_fitness"] = final_fitness
    metrics["lns_runtime"] = round(lns_runtime_seconds, 4)
    metrics["final_fitness"] = final_fitness
    metrics["runtime_seconds"] = round(t_end - t_start, 2)

    return best, metrics
