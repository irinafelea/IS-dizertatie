from collections import defaultdict
from typing import List, Dict

from app.models.AvailabilityDTO import AvailabilityDTO
from app.models.DayDTO import DayDTO
from app.models.TimeslotDTO import TimeslotDTO


def _expand_rows_around_seed_rows(
    seed_rows: set[int],
    forbidden_rows: set[int],
    total_rows: int,
    slots_per_day: int,
    required_count: int,
) -> set[int]:
    """
    Expands a seed set of rows until it reaches the required size

    Args:
        seed_rows: Anchor rows
        forbidden_rows: Forbidden rows
        total_rows: Total timetable rows
        slots_per_day: Number of slots per day
        required_count: Needed row count

    Returns:
        Expanded allowed rows
    """
    if required_count <= len(seed_rows):
        return set(seed_rows)

    if not seed_rows:
        return set()

    seed_days = {row // slots_per_day for row in seed_rows}

    def row_priority(candidate: int) -> tuple[int, int, int]:
        candidate_day = candidate // slots_per_day
        same_day_penalty = 0 if candidate_day in seed_days else 1
        distance = min(abs(candidate - seed) for seed in seed_rows)
        return same_day_penalty, distance, candidate

    expanded = set(seed_rows)
    candidates = [
        row
        for row in range(total_rows)
        if row not in forbidden_rows and row not in expanded
    ]
    for row in sorted(candidates, key=row_priority):
        expanded.add(row)
        if len(expanded) >= required_count:
            break

    return expanded


def allowed_teacher_rows(
    teacher_rules: dict,
    teacher_id: str,
    task_count: int,
    total_rows: int,
    slots_per_day: int,
) -> set[int] | None:
    """
    Computes the rows a teacher should be allowed to use

    Args:
        teacher_rules: Teacher rules map
        teacher_id: Teacher id
        task_count: Number of tasks for the teacher
        total_rows: Total timetable rows
        slots_per_day: Number of slots per day

    Returns:
        Allowed rows or None
    """
    teacher_id = str(teacher_id)
    rules = teacher_rules.get(teacher_id)
    if not rules:
        return None

    forbidden_rows = set(rules.get("forbidden_rows", set()))
    mandatory_rows = set(rules.get("mandatory_rows", set()))
    preferred_rows = set((rules.get("preferred_rows", {}) or {}).keys())

    if task_count <= 0:
        return None

    if not mandatory_rows:
        return None

    if mandatory_rows and len(mandatory_rows) >= task_count:
        return mandatory_rows

    anchor_rows = set(mandatory_rows)
    anchor_rows.update(preferred_rows)
    if len(anchor_rows) >= task_count:
        return anchor_rows

    expanded = _expand_rows_around_seed_rows(anchor_rows, forbidden_rows, total_rows, slots_per_day, task_count)
    if expanded:
        return expanded

    return None


def build_teacher_rules(availabilites: List[AvailabilityDTO], days: List[DayDTO], timeslots: List[TimeslotDTO]) -> Dict[str, dict]:
    """
    Builds row-based teacher rules from availability entries

    Args:
        availabilites: Availability DTOs
        days: Generation days
        timeslots: Generation timeslots

    Returns:
        Teacher rules indexed by teacher id
    """
    days = [DayDTO(**d) if isinstance(d, dict) else d for d in days]
    timeslots = [TimeslotDTO(**t) if isinstance(t, dict) else t for t in timeslots]
    availabilites = [AvailabilityDTO(**a) if isinstance(a, dict) else a for a in availabilites]

    day_index = {d.id: i for i, d in enumerate(days)}
    timeslot_index = {ts.id: i for i, ts in enumerate(timeslots)}
    slots_per_day = len(timeslots)

    rules = defaultdict(lambda: {
        "forbidden_rows": set(),
        "mandatory_rows": set(),
        "preferred_rows": {}
    })

    for avail in availabilites:
        tid = str(avail.teacherId)
        day_id = avail.dayId
        slot_id = avail.timeslotId
        availability = avail.availability
        weight = avail.weight

        if day_id not in day_index or slot_id not in timeslot_index:
            continue

        row = day_index[day_id] * slots_per_day + timeslot_index[slot_id]

        if availability == -1:
            rules[tid]["forbidden_rows"].add(row)
        elif availability == 2:
            rules[tid]["mandatory_rows"].add(row)
        elif availability == 1:
            rules[tid]["preferred_rows"][row] = max(
                rules[tid]["preferred_rows"].get(row, 0.0), weight
            )

    return dict(rules)

def teacher_availability_priority(teacher_rules: dict, teacher_id: str, row: int) -> int:
    """
    Returns the priority of a row for one teacher

    Args:
        teacher_rules: Teacher rules map
        teacher_id: Teacher id
        row: Timetable row

    Returns:
        Lower is better
        0 = mandatory row
        1 = preferred row
        2 = neutral row
        3 = forbidden row
    """
    teacher_id = str(teacher_id)
    if teacher_id not in teacher_rules:
        return 2

    rules = teacher_rules[teacher_id]

    if row in rules["forbidden_rows"]:
        return 3
    if row in rules["mandatory_rows"]:
        return 0
    if row in rules["preferred_rows"]:
        return 1
    return 2
