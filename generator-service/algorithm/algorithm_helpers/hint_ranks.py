from typing import List

from algorithm.algorithm_classes.Occ import Occ
from algorithm.algorithm_helpers.task_segments import logical_module_count
from algorithm.soft_constraints.teacher_compactness_penalty import teacher_day_compactness_penalty
from app.models.TaskDTO import TaskDTO
from app.models.TimeslotDTO import TimeslotDTO
from app.utils.build_teacher_rules import teacher_availability_priority
from constants.algorithm import BOTH, EVEN, ODD
from helpers.module import discipline_uuid, is_course, is_optional, kind_tag, module_hours, module_pack
from helpers.task_module_target import module_target, target_study_year_entries
from helpers.teacher import teacher_uuid
from helpers.timetable import row_to_day_time


def shares_students(first_task: TaskDTO, second_task: TaskDTO) -> bool:
    """
    Checks if two tasks affect the same students

    Args:
        first_task: First task
        second_task: Second task

    Returns:
        True if the tasks affect the same students
    """
    first_study_year_ids = set(str(x) for x in (first_task.studyYearsIds or ()))
    second_study_year_ids = set(str(x) for x in (second_task.studyYearsIds or ()))
    common_study_year_ids = first_study_year_ids & second_study_year_ids
    if not common_study_year_ids:
        return False

    if first_task.category == "course" or second_task.category == "course":
        return True

    if first_task.groupIndex is None or second_task.groupIndex is None:
        return False

    first_group_span = int(first_task.groupSpan or 1)
    second_group_span = int(second_task.groupSpan or 1)
    first_groups = set(range(int(first_task.groupIndex), int(first_task.groupIndex) + first_group_span))
    second_groups = set(range(int(second_task.groupIndex), int(second_task.groupIndex) + second_group_span))
    return bool(first_groups & second_groups)


def teacher_pair_rank(occ: Occ, row: int, parity_mask: int, module) -> int:
    """
    Returns the teacher pair rank for a candidate

    Args:
        occ: Current occupancy
        row: Candidate row
        parity_mask: Candidate parity
        module: Candidate module

    Returns:
        Teacher pair rank for the candidate
    """
    teacher_id = teacher_uuid(module)
    if not teacher_id or parity_mask not in (ODD, EVEN):
        return 1

    existing_mask = occ.teacher_row_mask.get((teacher_id, row), 0)
    if parity_mask == ODD and (existing_mask & EVEN):
        return 0
    if parity_mask == EVEN and (existing_mask & ODD):
        return 0
    return 1


def mixed_parity_study_year_rank(
    occ: Occ,
    task: TaskDTO,
    row: int,
    parity_mask: int,
    module,
    count_all: bool = True,
) -> int:
    """
    Returns the mixed parity rank for a study year candidate

    Args:
        occ: Current occupancy
        task: Candidate task
        row: Candidate row
        parity_mask: Candidate parity
        module: Candidate module
        count_all: Whether to count all conflicts or stop at the first one

    Returns:
        Mixed parity rank for the study year
    """
    if parity_mask not in (ODD, EVEN):
        return 0

    candidate_kind = kind_tag(module)
    study_year_ids = task.studyYearsIds if is_course(module) else (task.studyYearsIds[0],)
    count = 0

    for study_year_id in study_year_ids:
        parity_by_week = occ.sy_row_kind.get((study_year_id, row), {})
        other_kind = parity_by_week.get("E") if parity_mask == ODD else parity_by_week.get("O")
        if other_kind and other_kind != candidate_kind:
            if not count_all:
                return 1
            count += 1

    return count


def teacher_compactness_delta_rank(
    occ: Occ,
    row: int,
    parity_mask: int,
    timeslots: List[TimeslotDTO],
    module,
) -> int:
    """
    Returns the teacher compactness delta for a candidate

    Args:
        occ: Current occupancy
        row: Candidate row
        parity_mask: Candidate parity
        timeslots: All timeslots
        module: Candidate module

    Returns:
        Teacher compactness delta for the candidate
    """
    teacher_id = teacher_uuid(module)
    if not teacher_id:
        return 0

    day_index, slot_index = row_to_day_time(row, timeslots)
    bit = 1 << slot_index

    def delta_for(parity_key: str) -> int:
        key = (teacher_id, day_index, parity_key)
        before = occ.t_day_bits.get(key, 0)
        after = before | bit
        return teacher_day_compactness_penalty(after) - teacher_day_compactness_penalty(before)

    if parity_mask == ODD:
        return delta_for("O")
    if parity_mask == EVEN:
        return delta_for("E")
    if parity_mask == BOTH:
        return delta_for("O") + delta_for("E")
    return 0


def opens_new_teacher_day_rank(
    occ: Occ,
    row: int,
    parity_mask: int,
    timeslots: List[TimeslotDTO],
    module,
) -> int:
    """
    Returns whether the candidate opens a new teacher day

    Args:
        occ: Current occupancy
        row: Candidate row
        parity_mask: Candidate parity
        timeslots: All timeslots
        module: Candidate module

    Returns:
        New teacher day rank for the candidate
    """
    teacher_id = teacher_uuid(module)
    if not teacher_id:
        return 0

    day_index, _slot_index = row_to_day_time(row, timeslots)

    def opens(parity_key: str) -> int:
        return 0 if occ.t_day_has_any.get((teacher_id, day_index, parity_key), False) else 1

    if parity_mask == ODD:
        return opens("O")
    if parity_mask == EVEN:
        return opens("E")
    if parity_mask == BOTH:
        return opens("O") + opens("E")
    return 0


def teacher_availability_rank(teacher_rules: dict, row: int, module) -> int:
    """
    Returns the teacher availability rank for a candidate

    Args:
        teacher_rules: Teacher availability rules
        row: Candidate row
        module: Candidate module

    Returns:
        Teacher availability rank for the candidate
    """
    teacher_id = teacher_uuid(module)
    if not teacher_id:
        return 2
    return teacher_availability_priority(teacher_rules, teacher_id, row)


def online_pack_overlap_rank(occ: Occ, task: TaskDTO, row: int, module) -> int:
    """
    Returns the online optional-pack overlap rank for a candidate

    Args:
        occ: Current occupancy
        task: Candidate task
        row: Candidate row
        module: Candidate module

    Returns:
        Online pack overlap rank for the candidate
    """
    if not bool(getattr(task, "online", False)):
        return 1

    for entry in target_study_year_entries(task, 0, module):
        if not bool(entry.get("optional", False)):
            continue
        pack = entry.get("pack", None)
        discipline_id = str(entry.get("disciplineId") or "")
        study_year_id = str(entry.get("studyYearId") or "")
        if pack is None or not discipline_id or not study_year_id:
            continue

        for placed_pack, placed_discipline_id, _placed_mask, placed_placement in occ.sy_optional_entries.get((study_year_id, row), []):
            if int(placed_pack) != int(pack):
                continue
            if str(placed_discipline_id) == discipline_id:
                continue
            if bool(getattr(placed_placement.task, "online", False)):
                continue
            if not shares_students(task, placed_placement.task):
                continue
            return 0

    return 1


def optional_pack_alignment_rank(occ: Occ, task: TaskDTO, row: int, module) -> int:
    """
    Returns the optional-pack alignment rank for a candidate

    Args:
        occ: Current occupancy
        task: Candidate task
        row: Candidate row
        module: Candidate module

    Returns:
        Optional-pack alignment rank for the candidate
    """
    if not is_optional(module):
        return 1

    pack = module_pack(module)
    discipline_id = discipline_uuid(module)
    if pack is None or not discipline_id:
        return 1

    study_year_ids = task.studyYearsIds if is_course(module) else (task.studyYearsIds[0],)
    for study_year_id in study_year_ids:
        for placed_pack, placed_discipline_id, _placed_mask, placed_placement in occ.sy_optional_entries.get((study_year_id, row), []):
            if int(placed_pack) != int(pack):
                continue
            if placed_discipline_id == discipline_id:
                continue
            if not shares_students(task, placed_placement.task):
                continue
            return 0

    return 1


def group_week_balance_rank(occ: Occ, task: TaskDTO, parity_mask: int, module) -> int:
    """
    Returns the group week balance rank for a candidate

    Args:
        occ: Current occupancy
        task: Candidate task
        parity_mask: Candidate parity
        module: Candidate module

    Returns:
        Group week balance rank for the candidate
    """
    if task.category != "labsem" or logical_module_count(task) != 1 or module_hours(module) != 1:
        return 0

    target = module_target(task, 0)
    study_year_ids = tuple(str(x) for x in (target.get("studyYearsIds") or ()))
    group_index = target.get("groupIndex", task.groupIndex)
    if not study_year_ids or group_index is None or parity_mask not in (ODD, EVEN):
        return 0

    parity_key = "O" if parity_mask == ODD else "E"
    return occ.sy_group_week_h.get((study_year_ids[0], int(group_index), parity_key), 0)


def room_parity_fill_rank(occ: Occ, row: int, col: int, parity_mask: int, module) -> int:
    """
    Returns the room parity fill rank for a candidate

    Args:
        occ: Current occupancy
        row: Candidate row
        col: Candidate column
        parity_mask: Candidate parity
        module: Candidate module

    Returns:
        Room parity fill rank for the candidate
    """
    if module_hours(module) != 1:
        return 1

    existing_room_mask = occ.room_mask.get((row, col), 0)
    if existing_room_mask and (existing_room_mask & parity_mask) == 0:
        return 0
    return 1
