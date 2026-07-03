from typing import List, Tuple

from app.models.TimeslotDTO import TimeslotDTO
from helpers.timetable import row_to_day_time


def _cell_key_early(rc: Tuple[int, int], timeslots: List[TimeslotDTO]) -> Tuple[int, int, int]:
    """
    Builds a sorting key that prefers earlier candidate cells

    Args:
        rc: Candidate row and column
        timeslots: All timetable timeslots

    Returns:
        Tuple used to sort candidate cells
    """

    r, c = rc
    day, slot = row_to_day_time(r, timeslots)
    return (slot, day, c)
