from typing import List, Tuple, Optional, Any, Dict

from app.models.RoomDTO import RoomDTO
from app.models.TaskDTO import TaskDTO
from app.models.TimeslotDTO import TimeslotDTO
from algorithm.hard_constraints.dct_allowed_row import dct_allowed_row
from app.utils.build_teacher_rules import allowed_teacher_rows
from constants.algorithm import MASTER_MIN_SLOT_INDEX
from algorithm.hard_constraints.room_allows_task import room_allows_task
from algorithm.algorithm_helpers.task_segments import rows_fit_same_day, iter_task_segments
from helpers.module import is_master_module
from helpers.timetable import row_to_day_time, is_cell_blocked
from helpers.teacher import teacher_uuid


def is_teacher_available_for_row(task: TaskDTO, row: int, teacher_availabilities: Dict[str, dict],
                                 teacher_task_counts, total_rows: int, slots_per_day: int) -> bool:
    """
    Checks if a teacher can use a candidate row

    Args:
        task: Candidate task
        row: Candidate row
        teacher_availabilities: Teacher rules map
        teacher_task_counts: Task counts by teacher
        total_rows: Total timetable rows
        slots_per_day: Number of slots per day

    Returns:
        True if the teacher can use the row
    """
    m = task.modules[0]
    tid = teacher_uuid(m)

    if not tid:
        return True

    rules = teacher_availabilities.get(str(tid))
    if not rules:
        return True

    forbidden_rows = rules.get("forbidden_rows", set())
    if row in forbidden_rows:
        return False

    task_count = teacher_task_counts.get(tid, 0)
    allowed_rows = allowed_teacher_rows(
        teacher_availabilities,
        tid,
        task_count,
        total_rows,
        slots_per_day,
    )
    if allowed_rows is not None:
        return row in allowed_rows

    return True


def precompute_cells_for_task(
        task: TaskDTO,
        base_matrix: List[List[Optional[Any]]],
        rooms: List[RoomDTO],
        days,
        timeslots: List[TimeslotDTO],
        teacher_availabilities: Dict[str, dict],
        teacher_task_counts
) -> List[Tuple[int, int]]:
    """
    Precomputes candidate timetable cells for one task

    Args:
        task: Candidate task
        base_matrix: Base timetable matrix
        rooms: Available rooms
        days: Generation days
        timeslots: Generation timeslots
        teacher_availabilities: Teacher rules map
        teacher_task_counts: Task counts by teacher

    Returns:
        Candidate row and column pairs
    """

    m = task.modules[0]
    rows = len(base_matrix)
    cols = len(base_matrix[0])
    out: List[Tuple[int, int]] = []
    slots_per_day = len(timeslots)

    for r in range(rows):
        if not rows_fit_same_day(task, r, timeslots):
            continue

        _, slot_idx = row_to_day_time(r, timeslots)

        if is_master_module(m) and slot_idx < MASTER_MIN_SLOT_INDEX:
            continue

        if not dct_allowed_row(m, r, days, timeslots):
            continue

        if not is_teacher_available_for_row(task, r, teacher_availabilities, teacher_task_counts, rows, slots_per_day):
            continue

        if task.online:
            out.append((r, 0))
            continue

        for c in range(cols):
            segment_ok = True
            segments = iter_task_segments(task, r, 3, None)
            for _module, rr, _mask, _module_index in segments:
                if rr >= rows or is_cell_blocked(base_matrix, rr, c):
                    segment_ok = False
                    break
            if not segment_ok:
                continue
            if not room_allows_task(rooms[c], task, rooms):
                continue
            out.append((r, c))

    return out


def build_cells_cache(
        tasks: List[TaskDTO],
        base_matrix,
        rooms,
        days,
        timeslots,
        teacher_availabilities: Dict[str, dict],
        teacher_task_counts
) -> List[List[Tuple[int, int]]]:
    """
    Builds the candidate-cell cache for all tasks

    Args:
        tasks: Tasks to precompute
        base_matrix: Base timetable matrix
        rooms: Available rooms
        days: Generation days
        timeslots: Generation timeslots
        teacher_availabilities: Teacher rules map
        teacher_task_counts: Task counts by teacher

    Returns:
        Candidate cells for each task
    """

    return [
        precompute_cells_for_task(t, base_matrix, rooms, days, timeslots, teacher_availabilities, teacher_task_counts)
        for t in tasks
    ]
