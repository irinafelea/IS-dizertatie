from typing import Dict, List, Optional, Tuple

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers.task_segments import iter_task_segments
from app.models.TimeslotDTO import TimeslotDTO
from constants.algorithm import EVEN, ODD
from constants.penalties import PEN_ONSITE_ONLINE_NO_PAUSE
from helpers.teacher import teacher_uuid
from helpers.timetable import row_to_day_time


def _parity_labels(mask: int) -> list[str]:
    """
    Converts a parity mask into parity labels

    Args:
        mask: Parity mask to convert

    Returns:
        Present parity labels
    """
    out: list[str] = []
    if mask & ODD:
        out.append("O")
    if mask & EVEN:
        out.append("E")
    return out


def onsite_online_no_pause_penalty(
    placements: List[Optional[Placement]],
    timeslots: List[TimeslotDTO],
) -> tuple[int, int]:
    """
    Computes the onsite-online no-pause penalty

    Args:
        placements: Current placement list
        timeslots: All timetable timeslots

    Returns:
        Penalty and violation count
    """
    teacher_day_slots: Dict[Tuple[str, int, str], List[Tuple[int, bool]]] = {}
    student_day_slots: Dict[Tuple[str, int, str], List[Tuple[int, bool]]] = {}

    for placement in placements:
        if placement is None:
            continue

        for module, row, mask, _module_index in iter_task_segments(
            placement.task,
            placement.row,
            placement.parity_mask,
            placement.module_order,
        ):
            day_idx, slot_idx = row_to_day_time(row, timeslots)
            online = bool(placement.task.online)

            tid = teacher_uuid(module)
            if tid:
                for parity in _parity_labels(mask):
                    teacher_day_slots.setdefault((tid, day_idx, parity), []).append((slot_idx, online))

            for sy in placement.task.studyYearsIds:
                for parity in _parity_labels(mask):
                    student_day_slots.setdefault((str(sy), day_idx, parity), []).append((slot_idx, online))

    def count_violations(buckets: Dict[Tuple[str, int, str], List[Tuple[int, bool]]]) -> int:
        violations = 0
        for values in buckets.values():
            values = sorted(values)
            seen_slots: dict[int, set[bool]] = {}
            for slot_idx, online in values:
                seen_slots.setdefault(slot_idx, set()).add(online)

            ordered = sorted((slot, next(iter(modalities)) if len(modalities) == 1 else None) for slot, modalities in seen_slots.items())
            for i in range(1, len(ordered)):
                prev_slot, prev_online = ordered[i - 1]
                cur_slot, cur_online = ordered[i]
                if cur_slot - prev_slot != 1:
                    continue
                if prev_online is None or cur_online is None:
                    continue
                if prev_online != cur_online:
                    violations += 1
        return violations

    violations = count_violations(teacher_day_slots) + count_violations(student_day_slots)
    return violations * PEN_ONSITE_ONLINE_NO_PAUSE, violations
