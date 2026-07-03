from typing import List, Optional

from algorithm.algorithm_classes.Placement import Placement
from app.models.ModuleDTO import ModuleDTO
from app.models.TimeslotDTO import TimeslotDTO
from constants.penalties import (
    PEN_LATE_LAST,
    PEN_LATE_COURSE_BACHELOR,
    PEN_LATE_COURSE_MASTER,
    PEN_LATE_LAB_SEM_BACHELOR,
    PEN_LATE_LAB_SEM_MASTER,
)
from helpers.module import is_lab_or_sem, module_category, is_master_module
from helpers.teacher import teacher_uuid
from helpers.timetable import row_to_day_time


def late_slot_penalty(
    slot_idx: int,
    spd: int,
    m: ModuleDTO,
    row: int | None = None,
    teacher_rule: dict | None = None,
) -> int:
    """
    Computes the penalty for placing a module in the last slot

    Args:
        slot_idx: Candidate slot index
        spd: Number of timeslots per day
        m: Module being evaluated
        row: Candidate row
        teacher_rule: Teacher availability rule

    Returns:
        Late-slot penalty for the module
    """
    last = spd - 1
    if slot_idx == last:
        base = PEN_LATE_LAST
    else:
        return 0

    if teacher_rule is not None and row is not None:
        mandatory_rows = set(teacher_rule.get("mandatory_rows", set()))
        preferred_rows = teacher_rule.get("preferred_rows", {})
        if row in mandatory_rows or row in preferred_rows:
            return 0

    cat = module_category(m)
    is_master = is_master_module(m)
    if cat == "course":
        return int(base * (PEN_LATE_COURSE_MASTER if is_master else PEN_LATE_COURSE_BACHELOR))
    if is_lab_or_sem(m):
        return int(base * (PEN_LATE_LAB_SEM_MASTER if is_master else PEN_LATE_LAB_SEM_BACHELOR))
    return base


def late_slot_total_penalty(
    placements: List[Optional[Placement]],
    timeslots: List[TimeslotDTO],
    teachers_availabilities: dict,
) -> tuple[int, int]:
    """
    Computes the total late-slot penalty for a solution

    Args:
        placements: Current placement list
        timeslots: All timetable timeslots
        teachers_availabilities: Teacher availability rules

    Returns:
        Total penalty and violation count
    """
    slots_per_day = len(timeslots)
    total_penalty = 0
    violation_count = 0

    for placement in placements:
        if placement is None:
            continue

        module = placement.module
        _day_index, slot_index = row_to_day_time(placement.row, timeslots)
        teacher_id = teacher_uuid(module)
        teacher_rule = teachers_availabilities.get(teacher_id) if teacher_id else None

        penalty = late_slot_penalty(
            slot_index,
            slots_per_day,
            module,
            row=placement.row,
            teacher_rule=teacher_rule,
        )
        if penalty > 0:
            violation_count += 1
        total_penalty += penalty

    return total_penalty, violation_count
