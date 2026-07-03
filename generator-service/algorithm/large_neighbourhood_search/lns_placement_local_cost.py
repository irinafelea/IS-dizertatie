from typing import Optional, List

from algorithm.algorithm_classes.Placement import Placement
from algorithm.soft_constraints.bachelor_third_year_course_days_penalty import (
    bachelor_third_year_course_day_over_limit_burden,
    bachelor_third_year_modules_day_over_limit_burden,
)
from algorithm.soft_constraints.late_slot_penalty import late_slot_penalty
from algorithm.soft_constraints.teacher_row_penalty import (
    teacher_mandatory_row_local_penalty,
    teacher_preference_row_bonus,
)
from app.models.TimeslotDTO import TimeslotDTO
from constants.penalties import PEN_UNPLACED
from helpers.teacher import teacher_uuid
from helpers.timetable import row_to_day_time


def lns_placement_local_cost(
    p: Optional[Placement],
    timeslots: List[TimeslotDTO],
    placements: List[Optional[Placement]] | None = None,
    teachers_availabilities: dict | None = None,
    enforce_bachelor_third_year_free_day: bool = False,
) -> float:
    """
    Computes the local placement cost used in LNS removal ranking

    Args:
        p: Placement being evaluated
        timeslots: All timetable timeslots
        placements: Current placement list
        teachers_availabilities: Teacher availability rules
        enforce_bachelor_third_year_free_day: Whether to enforce third-year free-day penalties

    Returns:
        Local cost estimate for the placement
    """
    if p is None:
        return PEN_UNPLACED

    m = p.module
    spd = len(timeslots)
    _, slot = row_to_day_time(p.row, timeslots)
    cost = float(late_slot_penalty(slot, spd, m))

    if teachers_availabilities:
        tid = teacher_uuid(m)
        if tid:
            cost += float(teacher_mandatory_row_local_penalty(teachers_availabilities, tid, p.row))
            cost += float(teacher_preference_row_bonus(teachers_availabilities, tid, p.row))

    if enforce_bachelor_third_year_free_day and placements is not None:
        cost += float(bachelor_third_year_course_day_over_limit_burden(p, placements, spd))
        cost += float(bachelor_third_year_modules_day_over_limit_burden(p, placements, spd))

    return cost
