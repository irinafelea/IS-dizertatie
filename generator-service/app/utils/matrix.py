from typing import List, Optional, Any

from app.models.DayDTO import DayDTO
from app.models.EventDTO import EventDTO
from app.models.RoomDTO import RoomDTO
from app.models.TimeslotDTO import TimeslotDTO
from algorithm.matrix_classes.MatrixCell import MatrixCell


def empty_matrix(cols: int, rows: int) -> List[List[Optional[Any]]]:
    """
    Creates an empty timetable matrix

    Args:
        cols: Number of columns
        rows: Number of rows

    Returns:
        Empty matrix
    """

    return [[None for _ in range(cols)] for _ in range(rows)]

def build_room_index_map(rooms: List[RoomDTO]):
    """
    Builds a room id to column index map

    Args:
        rooms: Available rooms

    Returns:
        Room index map
    """
    rooms = [RoomDTO(**r) if isinstance(r, dict) else r for r in rooms]
    return {rooms[i].id: i for i in range(len(rooms))}


def build_day_index_map(days: List[DayDTO]):
    """
    Builds a day name to index map

    Args:
        days: Generation days

    Returns:
        Day index map
    """
    days = [DayDTO(**d) if isinstance(d, dict) else d for d in days]
    return {d.name.lower(): i for i, d in enumerate(days)}


def build_timeslot_index_map(timeslots: List[TimeslotDTO]):
    """
    Builds a timeslot tuple to index map

    Args:
        timeslots: Generation timeslots

    Returns:
        Timeslot index map
    """
    timeslots = [TimeslotDTO(**t) if isinstance(t, dict) else t for t in timeslots]
    return {(ts.startHour, ts.endHour): i for i, ts in enumerate(timeslots)}

def place_events_into_matrix(matrix, rooms, days, timeslots, events):
    """
    Places fixed events into the base matrix

    Args:
        matrix: Base timetable matrix
        rooms: Available rooms
        days: Generation days
        timeslots: Generation timeslots
        events: Fixed events

    Returns:
        Matrix with blocked event cells
    """
    events = [EventDTO(**e) if isinstance(e, dict) else e for e in events]

    room_index = build_room_index_map(rooms)
    day_index = build_day_index_map(days)
    slot_index = build_timeslot_index_map(timeslots)

    for ev in events:
        room = ev.room
        day = ev.day
        hour = ev.hour

        if room.id not in room_index:
            continue

        col = room_index[room.id]
        d = day_index.get(day.name.lower() if day != None else None)
        if d is None:
            continue

        s = slot_index.get((hour.startHour, hour.endHour))
        if s is None:
            continue

        row = d * len(timeslots) + s

        matrix[row][col] = MatrixCell(
            event=ev,
            module=None,
            fixed=True,
            eventId=ev.id,
            title=ev.eventTitle,
            room=room,
            day=day,
            hour=hour,
            row=row,
            col=col,
            evenWeek=getattr(ev, "evenWeek", True),
            oddWeek=getattr(ev, "oddWeek", True),
        )

    return matrix
