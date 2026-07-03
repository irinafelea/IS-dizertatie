from typing import List

from algorithm.algorithm_classes.Occ import Occ
from app.models.RoomDTO import RoomDTO
from app.models.TaskDTO import TaskDTO
from constants.algorithm import MIN_CAPACITY_RATIO, MAX_CAPACITY_RATIO, MAX_CAPACITY_OVERFLOW, MAX_ALLOWED_RATIO, \
    MIN_ALLOWED_RATIO
from helpers._dget import _dget


def _fits_capacity(cap: int, students: int) -> bool:
    """
    Checks whether a room fits the preferred capacity range

    Args:
        cap: Room capacity
        students: Number of students

    Returns:
        True if occupancy stays within the preferred capacity range
    """

    if students <= 0 or cap <= 0:
        return False
    ratio = float(students)/ float(cap)
    return MIN_CAPACITY_RATIO <= ratio <= MAX_CAPACITY_RATIO


def _can_host_all_students(cap: int, students: int) -> bool:
    """
    Checks whether a room can host all students

    Args:
        cap: Room capacity
        students: Number of students

    Returns:
        True if the room can host all students within the allowed ratio
    """
    ratio = float(cap) / float(students)
    return cap >= students and MIN_ALLOWED_RATIO <= ratio <= MAX_ALLOWED_RATIO


def _allows_small_overflow(cap: int, students: int) -> bool:
    """
    Checks whether a room can use the overflow fallback

    Args:
        cap: Room capacity
        students: Number of students

    Returns:
        True if the room stays within the allowed overflow threshold
    """
    if cap <= 0 or students <= 0:
        return False
    occupancy = float(students) / float(cap)
    return occupancy <= MAX_CAPACITY_OVERFLOW


def room_allows_task(room: RoomDTO, task: TaskDTO, rooms: List[RoomDTO]) -> bool:
    """
    Checks whether a room is allowed for a task

    Args:
        room: Candidate room
        task: Task being placed
        rooms: All available rooms

    Returns:
        True if the room satisfies the capacity hierarchy for the task
    """

    if task.online:
        return True

    students = int(task.numberOfStudents or 0)
    if students <= 0:
        return True

    cap = int(_dget(room, "capacity", 0) or 0)
    if cap <= 0:
        return False

    strict_exists = any(
        _fits_capacity(int(_dget(r, "capacity", 0) or 0), students)
        for r in rooms
    )
    if strict_exists:
        return _fits_capacity(cap, students)

    host_all_exists = any(
        _can_host_all_students(int(_dget(r, "capacity", 0) or 0), students)
        for r in rooms
    )
    if host_all_exists:
        return _can_host_all_students(cap, students)

    return _allows_small_overflow(cap, students)


def exceeds_all_rooms(task: TaskDTO, rooms: List[RoomDTO]) -> bool:
    """
    Checks whether a task exceeds every room capacity

    Args:
        task: Task being evaluated
        rooms: All available rooms

    Returns:
        True if no room can host all students
    """
    students = int(task.numberOfStudents or 0)
    if students <= 0:
        return False
    capacities = [int(_dget(r, "capacity", 0) or 0) for r in rooms]
    return all(cap < students for cap in capacities)


def room_pressure(occ: Occ, col: int, rows_to_check) -> int:
    """
    Counts existing room occupancy pressure for a column

    Args:
        occ: Current occupancy state
        col: Candidate room column
        rows_to_check: Rows that will be checked for placement

    Returns:
        Number of rows already occupied in the room column
    """
    return sum(1 for r in rows_to_check if occ.room_mask.get((r, col), 0) != 0)


def parity_pressure(occ: Occ, row: int, col: int, mask: int) -> int:
    """
    Returns the parity pressure for a candidate room cell

    Args:
        occ: Current occupancy state
        row: Candidate row
        col: Candidate room column
        mask: Candidate parity mask

    Returns:
        Rank where lower values are better for placement
    """
    existing = occ.room_mask.get((row, col), 0)
    if not Occ._mask_has_overlap(existing, mask):
        return 0
    return 2
