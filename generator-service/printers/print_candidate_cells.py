from typing import List

from app.models.RoomDTO import RoomDTO
from app.models.TaskDTO import TaskDTO
from app.models.TimeslotDTO import TimeslotDTO


def print_candidate_cells(task: TaskDTO, cells, rooms: List[RoomDTO], timeslots: List[TimeslotDTO], max_lines=20):
    """
    Prints candidate cells for one task

    Args:
        task: Source task
        cells: Candidate cells
        rooms: Available rooms
        timeslots: Generation timeslots
        max_lines: Maximum printed candidate rows

    Returns:
        None
    """
    print("\n" + "=" * 80)
    print(f"[TASK] {getattr(task.module, 'title', getattr(task.module, 'acronym', task.id))} {task.module.id}")
    print(f"Group: {task.group_index} | Kind: {task.kind} | Category: {task.module.category} | Students: {task.number_of_students} | sy={task.study_years_labels}")

    if getattr(task, "pair_group_key", None):
        print(f"Pair: {task.pair_group_key} ({task.pair_role})")

    print("-" * 80)

    slots_per_day = len(timeslots)

    for i, (r, c) in enumerate(cells[:max_lines]):
        day_idx = r // slots_per_day
        slot_idx = r % slots_per_day

        ts = timeslots[slot_idx]
        start = ts.startHour
        end = ts.endHour

        room = rooms[c]
        room_name = room.officialName

        print(f"{i:03d} | row={r:3d}, col={c:3d} | day={day_idx} | {start}-{end} | room={room_name}")

    if len(cells) > max_lines:
        print(f"... ({len(cells) - max_lines} more)")

    print("=" * 80)
