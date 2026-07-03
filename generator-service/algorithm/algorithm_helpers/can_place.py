from typing import List, Optional, Any

from algorithm.algorithm_classes.Occ import Occ
from algorithm.algorithm_helpers.flexible_groups import flex_group_pool_key, is_flexible_mandatory_labsem
from algorithm.algorithm_helpers.task_segments import iter_task_segments
from algorithm.hard_constraints.dct_allowed_row import dct_allowed_row
from algorithm.hard_constraints.teacher_option_allows_row import teacher_option_allows_row
from algorithm.soft_constraints.optional_overlap_allowed import optional_overlap_allowed
from app.models.RoomDTO import RoomDTO
from app.models.TaskDTO import TaskDTO
from app.utils.build_teacher_rules import allowed_teacher_rows

from app.models.TimeslotDTO import TimeslotDTO
from constants.algorithm import MASTER_MIN_SLOT_INDEX
from algorithm.hard_constraints.room_allows_task import room_allows_task
from helpers.module import is_master_module, is_course, task_is_roomless, discipline_uuid
from helpers.task_module_target import module_target, target_semantics_for_study_year
from helpers.teacher import teacher_uuid
from helpers.timetable import is_cell_blocked, row_to_day_time


def can_place(
        occ: Occ,
        task: TaskDTO,
        row: int,
        col: int,
        parity_mask: int,
        module_order: tuple[int, ...] | None,
        base_matrix: List[List[Optional[Any]]],
        rooms: List[RoomDTO],
        timeslots: List[TimeslotDTO],
        teacher_rules: dict,
        teacher_task_counts: dict,
        days=None,
) -> bool:
    """
    Checks whether a task can be placed in a candidate slot

    Args:
        occ: Current occupancy state
        task: Task to place
        row: Candidate row
        col: Candidate room column
        parity_mask: Candidate parity mask
        module_order: Module order used for segmented tasks
        base_matrix: Base matrix with blocked cells
        rooms: All available rooms
        timeslots: All timetable timeslots
        teacher_rules: Teacher availability rules
        teacher_task_counts: Number of tasks per teacher
        days: Optional day metadata used by day constraints

    Returns:
        True if the task can be placed in the candidate position
    """
    if not task_is_roomless(task):
        if col < 0 or col >= len(rooms):
            return False
        if not room_allows_task(rooms[col], task, rooms):
            return False

    for m, segment_row, segment_mask, _module_index in iter_task_segments(
        task,
        row,
        parity_mask,
        module_order,
    ):
        target = module_target(task, _module_index)
        target_study_year_ids = tuple(str(x) for x in (target.get("studyYearsIds") or ()))
        target_common = bool(target.get("common", task.common))
        target_group_index = target.get("groupIndex", task.groupIndex)

        if not task_is_roomless(task) and is_cell_blocked(base_matrix, segment_row, col):
            return False

        _, slot_idx = row_to_day_time(segment_row, timeslots)
        if is_master_module(m) and slot_idx < MASTER_MIN_SLOT_INDEX:
            return False
        if days is not None and not dct_allowed_row(m, segment_row, days, timeslots):
            return False

        if not task_is_roomless(task) and Occ._mask_has_overlap(occ.room_mask.get((segment_row, col), 0), segment_mask):
            return False

        tid = teacher_uuid(m)
        if tid and Occ._mask_has_overlap(occ.teacher_row_mask.get((tid, segment_row), 0), segment_mask):
            return False

        if tid and not teacher_option_allows_row(teacher_rules, tid, segment_row):
            return False

        if tid and tid in teacher_rules:
            allowed_rows = allowed_teacher_rows(
                teacher_rules,
                tid,
                teacher_task_counts.get(tid, 0),
                len(base_matrix),
                len(timeslots),
            )
            if allowed_rows is not None and segment_row not in allowed_rows:
                return False

        if is_course(m):
            for sy in target_study_year_ids:
                semantics = target_semantics_for_study_year(task, _module_index, sy, m)
                target_optional = bool(semantics.get("optional", False))
                target_pack = semantics.get("pack", None)
                target_discipline_id = str(semantics.get("disciplineId") or discipline_uuid(m) or "")
                existing_course = Occ._mask_has_overlap(
                    occ.sy_course_row_mask.get((sy, segment_row), 0), segment_mask
                )

                existing_lab = Occ._mask_has_overlap(
                    occ.sy_any_lab_row_mask.get((sy, segment_row), 0), segment_mask
                )
                existing_mandatory_course = Occ._mask_has_overlap(
                    occ.sy_mandatory_course_row_mask.get((sy, segment_row), 0), segment_mask
                )
                existing_mandatory_lab = Occ._mask_has_overlap(
                    occ.sy_mandatory_any_lab_row_mask.get((sy, segment_row), 0), segment_mask
                )
                existing_common = Occ._mask_has_overlap(
                    occ.sy_common_row_mask.get((sy, segment_row), 0), segment_mask
                )
                existing_noncommon = Occ._mask_has_overlap(
                    occ.sy_noncommon_row_mask.get((sy, segment_row), 0), segment_mask
                )

                if target_common:
                    if existing_noncommon:
                        return False
                else:
                    if existing_common:
                        return False

                if not target_optional:
                    if existing_course or existing_lab:
                        return False
                else:
                    if existing_mandatory_course or existing_mandatory_lab:
                        return False
                    if existing_course or existing_lab:
                        if not optional_overlap_allowed(
                            occ,
                            segment_row,
                            segment_mask,
                            sy,
                            target_pack,
                            target_discipline_id,
                        ):
                            return False

            continue

        sy_list = target_study_year_ids if target_common else ((target_study_year_ids[0],) if target_study_year_ids else ())
        gi = target_group_index
        if gi is None:
            return False

        if is_flexible_mandatory_labsem(task):
            pool_key = flex_group_pool_key(task)
            if occ.flex_group_used.get((pool_key, int(gi)), 0) > 0:
                return False

        for sy in sy_list:
            semantics = target_semantics_for_study_year(task, _module_index, sy, m)
            target_optional = bool(semantics.get("optional", False))
            target_pack = semantics.get("pack", None)
            target_discipline_id = str(semantics.get("disciplineId") or discipline_uuid(m) or "")
            existing_course = Occ._mask_has_overlap(
                occ.sy_course_row_mask.get((sy, segment_row), 0), segment_mask
            )

            existing_group = Occ._mask_has_overlap(
                occ.sy_group_row_mask.get((sy, int(gi), segment_row), 0), segment_mask
            )
            existing_mandatory_course = Occ._mask_has_overlap(
                occ.sy_mandatory_course_row_mask.get((sy, segment_row), 0), segment_mask
            )
            existing_mandatory_group = Occ._mask_has_overlap(
                occ.sy_mandatory_group_row_mask.get((sy, int(gi), segment_row), 0), segment_mask
            )
            existing_common = Occ._mask_has_overlap(
                occ.sy_common_row_mask.get((sy, segment_row), 0), segment_mask
            )
            existing_noncommon = Occ._mask_has_overlap(
                occ.sy_noncommon_row_mask.get((sy, segment_row), 0), segment_mask
            )

            if target_common:
                if existing_noncommon:
                    return False
            else:
                if existing_common:
                    return False

            if not target_optional:
                if existing_course or existing_group:
                    return False
                continue

            if existing_mandatory_course or existing_mandatory_group:
                return False
            if existing_course or existing_group:
                if not optional_overlap_allowed(
                    occ,
                    segment_row,
                    segment_mask,
                    sy,
                    target_pack,
                    target_discipline_id,
                ):
                    return False

    return True
