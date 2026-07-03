def decode(timeslots, rooms, row, col):
    """
    Decodes one candidate cell into day, timeslot, and room data

    Args:
        timeslots: Generation timeslots
        rooms: Available rooms
        row: Candidate row
        col: Candidate column

    Returns:
        Day index, timeslot, and room
    """
    slots_per_day = len(timeslots)
    day_idx = row // slots_per_day
    slot_idx = row % slots_per_day

    ts = timeslots[slot_idx]
    room = rooms[col]

    return day_idx, ts, room


def print_task_with_candidates(i, task, cells, count, current, limit_per_task, timeslots, rooms):
    """
    Prints candidate cells for one task when it matches the debug filter

    Args:
        i: Task index
        task: Source task
        cells: Candidate cells
        count: Candidate count
        current: Current candidate-count bucket
        limit_per_task: Maximum printed candidates
        timeslots: Generation timeslots
        rooms: Available rooms

    Returns:
        None
    """
    if count != current:
        current = count

    title = task.modules[0].title if task.modules else "N/A"
    teacher = task.modules[0].completeTeacher if task.modules else "N/A"

    if (title.__contains__("Limbaje formale")):
        print(
            f"[TASK] idx={i} | id={task.id} | {title} - {teacher} | "
            f"{task.category} | dur={task.durationHours} | sy={task.studyYearsLabels} (degreeLevel={task.modules[0].degreeLevel})"
        )

        for (row, col) in cells[:limit_per_task]:
            day_idx, ts, room = decode(timeslots, rooms, row, col)

            print(
                f"   → row_idx={row} day={day_idx} "
                f"time={ts.get('startHour')}-{ts.get('endHour')} "
                f"room={room.get('officialName')}"
            )

        if len(cells) > limit_per_task:
            print(f"   ... +{len(cells) - limit_per_task} more")


def print_tasks_with_candidates(onsite_tasks, cells_cache, timeslots, rooms, limit_per_task=30):
    """
    Prints candidate summaries for tasks

    Args:
        onsite_tasks: Tasks to inspect
        cells_cache: Candidate-cell cache
        timeslots: Generation timeslots
        rooms: Available rooms
        limit_per_task: Maximum printed candidates per task

    Returns:
        None
    """
    data = []
    for i, task in enumerate(onsite_tasks):
        cells = cells_cache[i] if i < len(cells_cache) else []
        data.append((i, task, cells, len(cells)))

    data.sort(key=lambda x: x[3])

    print("\n==================== DEBUG: TASK CANDIDATES ====================")

    print("\n===============================================================")
