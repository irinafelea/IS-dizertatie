from typing import Dict, List, Optional, Set

from algorithm.algorithm_classes.Placement import Placement
from constants.penalties import PEN_MANDATORY_ROW_MISSED, PEN_PREFERRED_ROW_MISSED
from helpers.teacher import teacher_uuid


def teacher_mandatory_missed_row_penalty(
    placements: List[Optional[Placement]],
    teacher_availabilities: dict,
) -> tuple[int, int]:
    """
    Computes the penalty for unused mandatory teacher rows

    Args:
        placements: Current placement list
        teacher_availabilities: Teacher availability rules

    Returns:
        Penalty and missed mandatory-row count
    """

    teacher_used_rows: Dict[str, Set[int]] = {}
    teacher_placement_count: Dict[str, int] = {}

    for p in placements:
        if p is None:
            continue

        tid = teacher_uuid(p.module)
        if not tid:
            continue

        teacher_used_rows.setdefault(tid, set()).add(p.row)
        teacher_placement_count[tid] = teacher_placement_count.get(tid, 0) + 1

    penalty = 0
    missed_count = 0

    for tid, rules in teacher_availabilities.items():
        mandatory_rows = set(rules.get("mandatory_rows", set()))
        if not mandatory_rows:
            continue

        used_rows = teacher_used_rows.get(tid, set())
        used_mandatory_count = len(mandatory_rows & used_rows)
        placement_count = teacher_placement_count.get(tid, 0)
        required_mandatory_count = min(placement_count, len(mandatory_rows))
        missed = max(0, required_mandatory_count - used_mandatory_count)

        missed_count += missed
        penalty += missed * PEN_MANDATORY_ROW_MISSED

    return penalty, missed_count

def teacher_preference_row_bonus(teachers_availabilities: dict, teacher_id: str, row: int) -> float:
    """
    Returns the local bonus for a preferred row

    Args:
        teachers_availabilities: Teacher rules map
        teacher_id: Teacher id
        row: Candidate row

    Returns:
        Local bonus for a preferred row
    """
    if teacher_id not in teachers_availabilities:
        return 0.0

    pref = teachers_availabilities[teacher_id]["preferred_rows"]
    if row in pref:
        # preferred rows improve the solution, weighted by preference strength
        return -float(pref[row]) * PEN_PREFERRED_ROW_MISSED

    return 0.0


def teacher_mandatory_row_local_penalty(teachers_availabilities: dict, teacher_id: str, row: int) -> int:
    """
    Returns the local penalty for missing a mandatory row

    Args:
        teachers_availabilities: Teacher rules map
        teacher_id: Teacher id
        row: Candidate row

    Returns:
        Local penalty when the row misses a mandatory row
    """
    if teacher_id not in teachers_availabilities:
        return 0

    mandatory_rows = set(teachers_availabilities[teacher_id].get("mandatory_rows", set()))
    if mandatory_rows and row not in mandatory_rows:
        return PEN_MANDATORY_ROW_MISSED

    return 0


def teacher_preferred_not_used_row_penalty(
    placements: List[Optional[Placement]],
    teachers_availabilities: dict,
) -> tuple[int, int]:
    """
    Computes the penalty for unused preferred teacher rows

    Args:
        placements: Current placement list
        teachers_availabilities: Teacher availability rules

    Returns:
        Penalty and missed preferred-row count
    """
    penalty = 0
    preferred_missed_count = 0

    for p in placements:
        if p is None:
            continue

        tid = teacher_uuid(p.module)
        if not tid:
            continue

        teacher_rules = teachers_availabilities.get(tid, {})
        preferred_rows = teacher_rules.get("preferred_rows", {})
        if preferred_rows:
            if p.row not in preferred_rows:
                preferred_missed_count += 1
                penalty += PEN_PREFERRED_ROW_MISSED

    return penalty, preferred_missed_count
