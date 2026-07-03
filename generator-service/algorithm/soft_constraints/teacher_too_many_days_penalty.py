import math
from typing import Dict, Tuple

from algorithm.algorithm_classes.Occ import Occ
from constants.penalties import PEN_TEACHER_TOO_MANY_DAYS


def teacher_too_many_days_penalty(occ: Occ) -> tuple[int, int]:
    """
    Computes the teacher too-many-days penalty

    Args:
        occ: Current occupancy state

    Returns:
        Penalty and violation count
    """
    days_and_hours_by_teacher_and_parity: Dict[Tuple[str, str], Dict[str, int]] = {}

    for (teacher_id, _day_index, parity), hours in occ.t_day_total_h.items():
        key = (teacher_id, parity)
        record = days_and_hours_by_teacher_and_parity.setdefault(key, {"hours": 0, "days": 0})
        record["hours"] += hours

    for (teacher_id, _day_index, parity), _has_any in occ.t_day_has_any.items():
        key = (teacher_id, parity)
        record = days_and_hours_by_teacher_and_parity.setdefault(key, {"hours": 0, "days": 0})
        record["days"] += 1

    penalty = 0
    count = 0

    for (_teacher_id, _parity), record in days_and_hours_by_teacher_and_parity.items():
        hours = record["hours"]
        days = record["days"]
        if hours <= 0:
            continue

        max_days = math.ceil(hours / 8.0)
        if days > max_days:
            penalty += (days - max_days) * PEN_TEACHER_TOO_MANY_DAYS
            count += 1

    return penalty, count
