from typing import List

from app.models.TaskDTO import TaskDTO
from algorithm.algorithm_helpers.task_segments import iter_task_segments, rows_fit_same_day
from algorithm.hard_constraints.dct_allowed_row import dct_allowed_row
from app.utils.build_teacher_rules import allowed_teacher_rows
from app.utils.build_cache_cells import is_teacher_available_for_row
from constants.algorithm import MASTER_MIN_SLOT_INDEX
from algorithm.hard_constraints.room_allows_task import room_allows_task
from helpers._dget import _dget
from helpers.module import is_master_module
from helpers.teacher import teacher_uuid
from helpers.timetable import row_to_day_time, is_cell_blocked


def diagnose_zero_candidate_tasks(tasks: List[TaskDTO], base_matrix, rooms, days, timeslots, cells_cache, teacher_availabilities, teacher_task_counts):
    """
    Prints filter-by-filter diagnostics for tasks with zero candidates

    Args:
        tasks: Source tasks
        base_matrix: Base timetable matrix
        rooms: Available rooms
        days: Generation days
        timeslots: Generation timeslots
        cells_cache: Candidate-cell cache
        teacher_availabilities: Teacher rules map
        teacher_task_counts: Task counts by teacher

    Returns:
        None
    """
    rows = len(base_matrix)
    cols = len(base_matrix[0])
    slots_per_day = len(timeslots)

    bad = [i for i, c in enumerate(cells_cache) if not c]
    if bad:
        print("\n=== ZERO-CANDIDATE TASK DIAGNOSIS ===")
    for i in bad:
        t = tasks[i]
        m = t.modules[0]
        is_master = is_master_module(m)
        eff = int(t.numberOfStudents or 0)
        tid = teacher_uuid(m)
        task_count = teacher_task_counts.get(tid, 0) if tid else 0
        allowed_rows = (
            sorted(
                allowed_teacher_rows(
                    teacher_availabilities,
                    str(tid),
                    task_count,
                    rows,
                    slots_per_day,
                ) or []
            )
            if tid else []
        )

        total = rows * cols

        after_same_day = 0
        for r in range(rows):
            if not rows_fit_same_day(t, r, timeslots):
                continue
            after_same_day += cols

        after_master = 0
        for r in range(rows):
            if not rows_fit_same_day(t, r, timeslots):
                continue
            _, slot_idx = row_to_day_time(r, timeslots)
            if is_master and slot_idx < MASTER_MIN_SLOT_INDEX:
                continue
            after_master += cols

        after_dct = 0
        for r in range(rows):
            if not rows_fit_same_day(t, r, timeslots):
                continue
            _, slot_idx = row_to_day_time(r, timeslots)
            if is_master and slot_idx < MASTER_MIN_SLOT_INDEX:
                continue
            if not dct_allowed_row(m, r, days, timeslots):
                continue
            after_dct += cols

        after_teacher = 0
        for r in range(rows):
            if not rows_fit_same_day(t, r, timeslots):
                continue
            _, slot_idx = row_to_day_time(r, timeslots)
            if is_master and slot_idx < MASTER_MIN_SLOT_INDEX:
                continue
            if not dct_allowed_row(m, r, days, timeslots):
                continue
            if not is_teacher_available_for_row(t, r, teacher_availabilities, teacher_task_counts, rows, slots_per_day):
                continue
            after_teacher += cols

        after_fixed = 0
        segment_block_examples = []
        blocked_examples = []
        for r in range(rows):
            if not rows_fit_same_day(t, r, timeslots):
                continue
            _, slot_idx = row_to_day_time(r, timeslots)
            if is_master and slot_idx < MASTER_MIN_SLOT_INDEX:
                continue
            if not dct_allowed_row(m, r, days, timeslots):
                continue
            if not is_teacher_available_for_row(t, r, teacher_availabilities, teacher_task_counts, rows, slots_per_day):
                continue
            for c in range(cols):
                segments = iter_task_segments(t, r, 3, None)
                segment_ok = True
                for _module, rr, _mask, _module_index in segments:
                    if rr >= rows:
                        segment_ok = False
                        if len(segment_block_examples) < 8:
                            segment_block_examples.append((r, c, "row_out_of_range", rr))
                        break
                    if is_cell_blocked(base_matrix, rr, c):
                        segment_ok = False
                        if len(blocked_examples) < 8:
                            blocked_examples.append((r, c, rr))
                        break
                if not segment_ok:
                    continue
                after_fixed += 1

        after_capacity = 0
        for r in range(rows):
            if not rows_fit_same_day(t, r, timeslots):
                continue
            _, slot_idx = row_to_day_time(r, timeslots)
            if is_master and slot_idx < MASTER_MIN_SLOT_INDEX:
                continue
            if not dct_allowed_row(m, r, days, timeslots):
                continue
            if not is_teacher_available_for_row(t, r, teacher_availabilities, teacher_task_counts, rows, slots_per_day):
                continue
            for c in range(cols):
                segments = iter_task_segments(t, r, 3, None)
                segment_ok = True
                for _module, rr, _mask, _module_index in segments:
                    if rr >= rows or is_cell_blocked(base_matrix, rr, c):
                        segment_ok = False
                        break
                if not segment_ok:
                    continue
                if not room_allows_task(rooms[c], t, rooms):
                    continue
                after_capacity += 1

        cap_fail = []
        for c in range(cols):
            if not room_allows_task(rooms[c], t, rooms):
                cap_fail.append((c, _dget(rooms[c], "capacity", None)))

        print(f"\nTask index: {i} | id={t.id} | category={t.category} | sy={t.studyYearsLabels}")
        print(f"  Module={t.modules[0]}")
        print(f"  effective_students={eff} | is_master={is_master}")
        print(f"  teacher_id={tid} | teacher_task_count={task_count}")
        print(f"  total cells: {total}")
        print(f"  after same-day fit:  {after_same_day}")
        print(f"  after master rule:   {after_master}")
        print(f"  after dct rule:      {after_dct}")
        print(f"  after teacher rule:  {after_teacher}")
        if tid:
            teacher_rules = teacher_availabilities.get(str(tid), {})
            print(f"  teacher_rules: {teacher_rules}")
            print(f"  computed_allowed_rows: {allowed_rows}")
        print(f"  after fixed events:  {after_fixed}")
        print(f"  after capacity rule: {after_capacity}")
        if cap_fail:
            print(f"  rooms failing capacity: {cap_fail}")
        if segment_block_examples:
            print(f"  segment row failures: {segment_block_examples}")
        if blocked_examples:
            print(f"  blocked fixed cells: {blocked_examples}")
