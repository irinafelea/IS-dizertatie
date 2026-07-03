from typing import List

from app.models.DayDTO import DayDTO
from app.models.RoomDTO import RoomDTO
from app.models.TimeslotDTO import TimeslotDTO


def get_total_rows(days: List[DayDTO], timeslots: List[TimeslotDTO]) -> int:
    """
    Computes the total number of timetable rows

    Args:
        days: Generation days
        timeslots: Generation timeslots

    Returns:
        Total row count
    """

    return len(days) * len(timeslots)


def get_total_columns(rooms: List[RoomDTO]) -> int:
    """
    Computes the total number of timetable columns

    Args:
        rooms: Available rooms

    Returns:
        Total column count
    """

    return len(rooms)
