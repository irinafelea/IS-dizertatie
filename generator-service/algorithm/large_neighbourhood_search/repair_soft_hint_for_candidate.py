from typing import List, Tuple

from algorithm.algorithm_classes.Occ import Occ
from algorithm.algorithm_helpers.hint_ranks import (
    group_week_balance_rank,
    mixed_parity_study_year_rank,
    online_pack_overlap_rank,
    opens_new_teacher_day_rank,
    optional_pack_alignment_rank,
    room_parity_fill_rank,
    teacher_availability_rank,
    teacher_compactness_delta_rank,
)
from algorithm.soft_constraints.late_slot_penalty import late_slot_penalty
from app.models.TaskDTO import TaskDTO
from app.models.TimeslotDTO import TimeslotDTO
from helpers.timetable import row_to_day_time


def repair_soft_hint_for_candidate(
        occ: Occ,
        task: TaskDTO,
        row: int,
        col: int,
        parity_mask: int,
        timeslots: List[TimeslotDTO],
        teachers_availabilities,
) -> Tuple[int, int, int, int, int, int, int, int, int, int]:
    """
    Builds the fast reinsertion hint for one LNS candidate

    Args:
        occ: Current occupancy state
        task: Task being evaluated
        row: Candidate row
        col: Candidate room column
        parity_mask: Candidate parity mask
        timeslots: All timetable timeslots
        teachers_availabilities: Teacher availability rules

    Returns:
        Ranking tuple where lower values mean a better candidate
    """
    m = task.modules[0]
    spd = len(timeslots)
    _day_idx, slot_idx = row_to_day_time(row, timeslots)

    late = late_slot_penalty(slot_idx, spd, m)

    room_bias = col
    mix = mixed_parity_study_year_rank(occ, task, row, parity_mask, m)
    teach_compact = teacher_compactness_delta_rank(occ, row, parity_mask, timeslots, m)
    new_day = opens_new_teacher_day_rank(occ, row, parity_mask, timeslots, m)
    room_parity_fill = room_parity_fill_rank(occ, row, col, parity_mask, m)
    optional_pack_alignment = optional_pack_alignment_rank(occ, task, row, m)
    online_pack_overlap = online_pack_overlap_rank(occ, task, row, m)
    teacher_avail = teacher_availability_rank(teachers_availabilities, row, m)
    group_week_balance = group_week_balance_rank(occ, task, parity_mask, m)

    return teacher_avail, online_pack_overlap, group_week_balance, optional_pack_alignment, room_parity_fill, late, mix, teach_compact, new_day, room_bias
