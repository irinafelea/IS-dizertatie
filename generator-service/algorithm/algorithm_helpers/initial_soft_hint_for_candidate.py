from typing import List, Tuple

from algorithm.algorithm_helpers.hint_ranks import (
    group_week_balance_rank,
    mixed_parity_study_year_rank,
    online_pack_overlap_rank,
    opens_new_teacher_day_rank,
    teacher_availability_rank,
    teacher_compactness_delta_rank,
    teacher_pair_rank,
)
from algorithm.algorithm_classes.Occ import Occ
from app.models.TaskDTO import TaskDTO
from app.models.TimeslotDTO import TimeslotDTO
from helpers.timetable import row_to_day_time
from algorithm.soft_constraints.late_slot_penalty import late_slot_penalty


def initial_soft_hint_for_candidate(
    occ: Occ,
    task: TaskDTO,
    row: int,
    parity_mask: int,
    timeslots: List[TimeslotDTO],
    teacher_rules: dict,
) -> Tuple[int, int, int, int, int, int, int, int]:
    """
    Builds the GA soft hint used to rank initial placement candidates

    Args:
        occ: Current occupancy state
        task: Task being evaluated
        row: Candidate row
        parity_mask: Candidate parity mask
        timeslots: All timetable timeslots
        teacher_rules: Teacher availability rules

    Returns:
        Ranking tuple where lower values mean a better candidate
    """

    m = task.modules[0]
    spd = len(timeslots)
    _, slot = row_to_day_time(row, timeslots)
    late = late_slot_penalty(slot, spd, m)

    pair = teacher_pair_rank(occ, row, parity_mask, m)
    mix = mixed_parity_study_year_rank(occ, task, row, parity_mask, m, count_all=False)
    teacher_compactness = teacher_compactness_delta_rank(occ, row, parity_mask, timeslots, m)
    new_day = opens_new_teacher_day_rank(occ, row, parity_mask, timeslots, m)
    teacher_avail = teacher_availability_rank(teacher_rules, row, m)
    online_pack_overlap = online_pack_overlap_rank(occ, task, row, m)
    group_week_balance = group_week_balance_rank(occ, task, parity_mask, m)

    return (teacher_avail, online_pack_overlap, group_week_balance, late, pair, mix, teacher_compactness, new_day)
