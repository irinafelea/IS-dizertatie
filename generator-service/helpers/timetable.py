from typing import List, Optional, Any, Tuple
from app.models.TimeslotDTO import TimeslotDTO


def row_to_day_time(row_index: int, timeslots: List[TimeslotDTO]) -> Tuple[int, int]:
    """
    Converts a matrix row index into day and timeslot indexes

    Args:
        row_index: Matrix row index
        timeslots: Ordered timeslot list

    Returns:
        Tuple of day index and timeslot index
    """

    spd = len(timeslots)
    return row_index // spd, row_index % spd


def is_cell_blocked(base_matrix: List[List[Optional[Any]]], row: int, col: int) -> bool:
    """
    Checks whether a matrix cell is occupied by a fixed event

    Args:
        base_matrix: Timetable matrix
        row: Matrix row
        col: Matrix column

    Returns:
        True when the cell is already occupied
    """
    return base_matrix[row][col] is not None
