from typing import List

from algorithm.algorithm_classes.GAIndividual import GAIndividual
from algorithm.algorithm_score.score_solution import score_solution
from algorithm.genetic_algorithm._order_from_keys import _order_from_keys
from algorithm.genetic_algorithm.construct_feasible_solution import construct_feasible_solution
from algorithm.soft_constraints.unplaced_penalty import unplaced_penalty
from app.models.TaskDTO import TaskDTO


def _score_constructed_solution(
        tasks: List[TaskDTO],
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache,
        teachers_availabilities,
        teacher_task_counts,
        order,
        enforce_bachelor_third_year_free_day: bool = False,
) -> int:
    """
    Scores a timetable constructed from a candidate task order

    Args:
        tasks: All tasks from the timetable instance
        base_matrix: Base matrix with blocked cells
        rooms: All available rooms
        days: All timetable days
        timeslots: All timetable timeslots
        cells_cache: Cached candidate cells by task
        teachers_availabilities: Teacher availability rules
        teacher_task_counts: Number of tasks per teacher
        order: Candidate task construction order
        enforce_bachelor_third_year_free_day: Whether to enforce third-year free-day penalties

    Returns:
        Penalty score of the constructed solution
    """
    placements = construct_feasible_solution(
        tasks,
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache,
        order,
        teachers_availabilities,
        teacher_task_counts,
    )

    missing_penalty, _missing_count = unplaced_penalty(placements)
    if missing_penalty > 0:
        return missing_penalty

    return score_solution(
        placements,
        timeslots,
        teachers_availabilities,
        enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
    )


def _evaluate_initial_individual(
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
) -> int:
    """
    Evaluates a GA individual during the initial population phase

    Args:
        ind: Individual to evaluate
        tasks: All tasks from the timetable instance
        base_matrix: Base matrix with blocked cells
        rooms: All available rooms
        days: All timetable days
        timeslots: All timetable timeslots
        cells_cache: Cached candidate cells by task
        teachers_availabilities: Teacher availability rules
        teacher_task_counts: Number of tasks per teacher
        enforce_bachelor_third_year_free_day: Whether to enforce third-year free-day penalties

    Returns:
        Fitness score of the individual
    """
    order = _order_from_keys(tasks, cells_cache, ind.keys)
    return _score_constructed_solution(
        tasks,
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache,
        teachers_availabilities,
        teacher_task_counts,
        order,
        enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
    )


def _evaluate_individual(
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
) -> int:
    """
    Evaluates a GA individual

    Args:
        ind: Individual to evaluate
        tasks: All tasks from the timetable instance
        base_matrix: Base matrix with blocked cells
        rooms: All available rooms
        days: All timetable days
        timeslots: All timetable timeslots
        cells_cache: Cached candidate cells by task
        teachers_availabilities: Teacher availability rules
        teacher_task_counts: Number of tasks per teacher
        enforce_bachelor_third_year_free_day: Whether to enforce third-year free-day penalties

    Returns:
        Fitness score of the individual
    """

    order = _order_from_keys(tasks, cells_cache, ind.keys)
    return _score_constructed_solution(
        tasks,
        base_matrix,
        rooms,
        days,
        timeslots,
        cells_cache,
        teachers_availabilities,
        teacher_task_counts,
        order,
        enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
    )
