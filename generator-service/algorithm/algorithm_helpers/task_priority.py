from helpers.module import module_hours, is_course, is_master_module
from helpers.task_module_target import task_has_optional_semantics
from app.models.TaskDTO import TaskDTO


def _split_labels(value: str | None) -> list[str]:
    """
    Splits a combined study year label string

    Args:
        value: Combined study year labels

    Returns:
        Individual non-empty study year labels
    """
    return [part.strip() for part in str(value or "").split("+") if part.strip()]


def _is_third_year_task(task: TaskDTO) -> bool:
    """
    Checks whether a task belongs to third-year students

    Args:
        task: Task to evaluate

    Returns:
        True if the task targets third-year students
    """
    return any(label.endswith("3") for label in _split_labels(task.studyYearsLabels))


def _common_study_year_count(task: TaskDTO) -> int:
    """
    Counts the study years covered by a task

    Args:
        task: Task to evaluate

    Returns:
        Number of study years covered by the task
    """
    return max(1, len(tuple(str(x) for x in (task.studyYearsIds or ()))))


def _phase_rank(task: TaskDTO) -> int:
    """
    Returns the scheduling phase rank for a task

    Args:
        task: Task to rank

    Returns:
        Phase rank used in task prioritization
    """
    m = task.modules[0]
    master = is_master_module(m)
    course = is_course(m)
    third_year = _is_third_year_task(task)

    if master and course:
        return 0
    if master and not course:
        return 1
    if (not master) and course and third_year:
        return 2
    if (not master) and course:
        return 3
    if (not master) and (not course) and third_year:
        return 4
    return 5


def task_priority(task: TaskDTO, candidate_count: int, candidate_cells):
    """
    Builds the scheduling priority tuple for a task

    Args:
        task: Task to prioritize
        candidate_count: Number of candidate cells
        candidate_cells: Candidate row and room cells

    Returns:
        Priority tuple where lower values should be scheduled earlier
    """
    m = task.modules[0]
    h = module_hours(m)

    unique_rooms = {c for (_, c) in candidate_cells}
    unique_rows = {r for (r, _) in candidate_cells}
    room_count = len(unique_rooms)
    available_timeslot_count = len(unique_rows)
    common_count = _common_study_year_count(task)
    phase_rank = _phase_rank(task)
    one_room_rank = 0 if room_count == 1 else 1
    optional_rank = 1 if task_has_optional_semantics(task) else 0

    return (
        available_timeslot_count,
        room_count,
        phase_rank,
        -common_count if phase_rank in (0, 1) else 0,
        one_room_rank,
        candidate_count,
        -h,
        optional_rank,
        str(task.studyYearsLabels or ""),
        int(task.groupIndex or 0),
    )
