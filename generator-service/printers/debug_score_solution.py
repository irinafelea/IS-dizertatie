from typing import List, Optional

from algorithm.algorithm_classes.GAIndividual import GAIndividual
from algorithm.algorithm_classes.Placement import Placement
from algorithm.genetic_algorithm._order_from_keys import _order_from_keys
from algorithm.genetic_algorithm.construct_feasible_solution import construct_feasible_solution
from algorithm.algorithm_score.score_solution import score_solution_breakdown
from app.models.TaskDTO import TaskDTO
from app.models.TimeslotDTO import TimeslotDTO
from constants.penalties import PEN_UNPLACED


def debug_score_solution(
        placements: List[Optional[Placement]],
        timeslots: List[TimeslotDTO],
        teachers_availabilities,
        enforce_bachelor_third_year_free_day: bool = False,
):
    """
    Builds the score breakdown for a placement list

    Args:
        placements: Candidate placements
        timeslots: Generation timeslots
        teachers_availabilities: Teacher rules map
        enforce_bachelor_third_year_free_day: Whether to enforce the free-day rule

    Returns:
        Score breakdown dictionary
    """
    return score_solution_breakdown(
        placements,
        timeslots,
        teachers_availabilities,
        enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
    )


def debug_evaluate_individual(
        ind: GAIndividual,
        tasks: List[TaskDTO],
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache,
        teachers_availabilities,
        teacher_task_counts,
        enforce_bachelor_third_year_free_day: bool = False,
):
    """
    Evaluates one GA individual and returns its debug breakdown

    Args:
        ind: GA individual
        tasks: Source tasks
        base_matrix: Base timetable matrix
        rooms: Available rooms
        days: Generation days
        timeslots: Generation timeslots
        cells_cache: Candidate-cell cache
        teachers_availabilities: Teacher rules map
        teacher_task_counts: Task counts by teacher
        enforce_bachelor_third_year_free_day: Whether to enforce the free-day rule

    Returns:
        Debug breakdown for the individual
    """
    order = _order_from_keys(tasks, cells_cache, ind.keys)
    placements = construct_feasible_solution(tasks, base_matrix, rooms, days, timeslots, cells_cache, order,
                                             teachers_availabilities, teacher_task_counts)

    missing = sum(1 for p in placements if p is None)
    if missing > 0:
        return {
            "reason": "unplaced",
            "missing": missing,
            "total_penalty": missing * PEN_UNPLACED,
        }

    return debug_score_solution(
        placements,
        timeslots,
        teachers_availabilities,
        enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
    )


def log_debug_individual(
        ind,
        tasks,
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache,
        teachers_availabilities,
        teacher_task_counts,
        enforce_bachelor_third_year_free_day: bool = False,
        prefix="[GA]",
):
    """
    Prints the debug breakdown for one GA individual

    Args:
        ind: GA individual
        tasks: Source tasks
        base_matrix: Base timetable matrix
        rooms: Available rooms
        days: Generation days
        timeslots: Generation timeslots
        cells_cache: Candidate-cell cache
        teachers_availabilities: Teacher rules map
        teacher_task_counts: Task counts by teacher
        enforce_bachelor_third_year_free_day: Whether to enforce the free-day rule
        prefix: Printed line prefix

    Returns:
        None
    """
    breakdown = debug_evaluate_individual(
        ind,
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

    print(f"{prefix} DEBUG:")
    for k, v in breakdown.items():
        print(f"{prefix} {k}: {v}")
