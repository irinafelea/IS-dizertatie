from typing import Dict, Tuple, List

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers.flexible_groups import flex_group_pool_key, is_flexible_mandatory_labsem
from algorithm.algorithm_helpers.task_segments import iter_task_segments
from app.models.TimeslotDTO import TimeslotDTO
from constants.algorithm import ODD, EVEN
from helpers.module import (
    is_course,
    kind_tag,
    module_hours,
    module_category,
    discipline_uuid,
)
from helpers.teacher import teacher_uuid
from helpers.timetable import row_to_day_time
from helpers.task_module_target import module_target
from helpers.task_module_target import target_semantics_for_study_year

class Occ:
    """
    Tracks timetable occupancy and soft-constraint counters
    """
    def __init__(self):
        """
        Initializes the occupancy state

        Args:
            None

        Returns:
            None
        """
        self.room_mask: Dict[Tuple[int, int], int] = {}

        self.teacher_row_mask: Dict[Tuple[str, int], int] = {}
        self.sy_course_row_mask: Dict[Tuple[str, int], int] = {}
        self.sy_any_lab_row_mask: Dict[Tuple[str, int], int] = {}
        self.sy_common_row_mask: Dict[Tuple[str, int], int] = {}
        self.sy_noncommon_row_mask: Dict[Tuple[str, int], int] = {}
        self.sy_mandatory_course_row_mask: Dict[Tuple[str, int], int] = {}
        self.sy_mandatory_any_lab_row_mask: Dict[Tuple[str, int], int] = {}

        self.sy_group_row_mask: Dict[Tuple[str, int, int], int] = {}
        self.sy_mandatory_group_row_mask: Dict[Tuple[str, int, int], int] = {}


        self.sy_row_kind: Dict[Tuple[str, int], Dict[str, str]] = {}
        self.sy_group_row_kind: Dict[Tuple[str, int, int], Dict[str, str]] = {}

        self.sy_day_total_h: Dict[Tuple[str, int, str], int] = {}
        self.sy_day_course_h: Dict[Tuple[str, int, str], int] = {}
        self.sy_group_week_h: Dict[Tuple[str, int, str], int] = {}
        self.sy_day_optional_pack_sum_h: Dict[Tuple[str, int, str, int, str], int] = {}
        self.sy_day_optional_pack_max_h: Dict[Tuple[str, int, str, int, str], int] = {}
        self.t_day_total_h: Dict[Tuple[str, int, str], int] = {}
        self.t_day_course_h: Dict[Tuple[str, int, str], int] = {}

        self.sy_day_bits: Dict[Tuple[str, int, str], int] = {}
        self.t_day_bits: Dict[Tuple[str, int, str], int] = {}
        self.t_day_has_any: Dict[Tuple[str, int, str], bool] = {}

        self.teacher_mandatory_used: Dict[str, int] = {}

        self.sy_optional_entries: Dict[Tuple[str, int], List[Tuple[int, str, int, Placement]]] = {}
        self.flex_group_used: Dict[Tuple[Tuple, int], int] = {}

    @staticmethod
    def _mask_has_overlap(a: int, b: int) -> bool:
        """
        Checks whether two parity masks overlap

        Args:
            a: First parity mask
            b: Second parity mask

        Returns:
            True when the masks overlap
        """
        return (a & b) != 0

    @staticmethod
    def _parities(mask: int) -> List[str]:
        """
        Expands a parity mask into parity labels

        Args:
            mask: Parity mask

        Returns:
            Present parity labels
        """
        ps: List[str] = []
        if mask & ODD:
            ps.append("O")
        if mask & EVEN:
            ps.append("E")
        return ps

    def add(self, p: Placement, timeslots: List[TimeslotDTO], teacher_availabilities: dict) -> None:
        """
        Adds one placement into the occupancy state

        Args:
            p: Placement to register
            timeslots: Generation timeslots
            teacher_availabilities: Teacher rules map

        Returns:
            None
        """
        if is_flexible_mandatory_labsem(p.task) and p.group_index is not None:
            pool_key = flex_group_pool_key(p.task)
            key = (pool_key, int(p.group_index))
            self.flex_group_used[key] = self.flex_group_used.get(key, 0) + 1

        for m, row, mask, _module_index in iter_task_segments(
            p.task,
            p.row,
            p.parity_mask,
            p.module_order,
        ):
            target = module_target(p.task, _module_index)
            target_study_year_ids = tuple(str(x) for x in (target.get("studyYearsIds") or ()))
            target_common = bool(target.get("common", p.task.common))
            target_group_index = target.get("groupIndex", p.group_index)
            col = p.col

            if not p.task.online:
                self.room_mask[(row, col)] = self.room_mask.get((row, col), 0) | mask

            tid = teacher_uuid(m)
            if tid:
                self.teacher_row_mask[(tid, row)] = self.teacher_row_mask.get((tid, row), 0) | mask

                rules = teacher_availabilities.get(tid)
                if rules and row in rules["mandatory_rows"]:
                    self.teacher_mandatory_used[tid] = self.teacher_mandatory_used.get(tid, 0) + 1

            if is_course(m):
                for sy in target_study_year_ids:
                    semantics = target_semantics_for_study_year(p.task, _module_index, sy, m)
                    target_optional = bool(semantics.get("optional", False))
                    target_pack = semantics.get("pack", None)
                    target_discipline_id = str(semantics.get("disciplineId") or did if (did := discipline_uuid(m)) else "")
                    self.sy_course_row_mask[(sy, row)] = self.sy_course_row_mask.get((sy, row), 0) | mask
                    if target_common:
                        self.sy_common_row_mask[(sy, row)] = self.sy_common_row_mask.get((sy, row), 0) | mask
                    else:
                        self.sy_noncommon_row_mask[(sy, row)] = self.sy_noncommon_row_mask.get((sy, row), 0) | mask
                    if not target_optional:
                        self.sy_mandatory_course_row_mask[(sy, row)] = self.sy_mandatory_course_row_mask.get((sy, row), 0) | mask
                    elif target_pack is not None and target_discipline_id:
                        self.sy_optional_entries.setdefault((sy, row), []).append((int(target_pack), target_discipline_id, mask, p))
            else:
                sy_list = target_study_year_ids if target_common else ((target_study_year_ids[0],) if target_study_year_ids else ())
                gi = target_group_index
                for sy in sy_list:
                    semantics = target_semantics_for_study_year(p.task, _module_index, sy, m)
                    target_optional = bool(semantics.get("optional", False))
                    target_pack = semantics.get("pack", None)
                    target_discipline_id = str(semantics.get("disciplineId") or did if (did := discipline_uuid(m)) else "")
                    if gi is not None:
                        k = (sy, int(gi), row)
                        self.sy_group_row_mask[k] = self.sy_group_row_mask.get(k, 0) | mask
                        if not target_optional:
                            self.sy_mandatory_group_row_mask[k] = self.sy_mandatory_group_row_mask.get(k, 0) | mask
                    self.sy_any_lab_row_mask[(sy, row)] = self.sy_any_lab_row_mask.get((sy, row), 0) | mask
                    if target_common:
                        self.sy_common_row_mask[(sy, row)] = self.sy_common_row_mask.get((sy, row), 0) | mask
                    else:
                        self.sy_noncommon_row_mask[(sy, row)] = self.sy_noncommon_row_mask.get((sy, row), 0) | mask
                    if not target_optional:
                        self.sy_mandatory_any_lab_row_mask[(sy, row)] = self.sy_mandatory_any_lab_row_mask.get((sy, row), 0) | mask
                    elif target_pack is not None and target_discipline_id:
                        self.sy_optional_entries.setdefault((sy, row), []).append((int(target_pack), target_discipline_id, mask, p))

            tag = kind_tag(m)
            for parity in self._parities(mask):
                if is_course(m):
                    for sy in target_study_year_ids:
                        self.sy_row_kind.setdefault((sy, row), {})[parity] = tag
                else:
                    sy = target_study_year_ids[0]
                    self.sy_row_kind.setdefault((sy, row), {})[parity] = tag
                    if target_group_index is not None:
                        self.sy_group_row_kind.setdefault((sy, int(target_group_index), row), {})[parity] = tag

            day_idx, slot_idx = row_to_day_time(row, timeslots)
            bit = 1 << slot_idx
            h = module_hours(m)

            for parity in self._parities(mask):
                if is_course(m):
                    for sy in target_study_year_ids:
                        semantics = target_semantics_for_study_year(p.task, _module_index, sy, m)
                        target_optional = bool(semantics.get("optional", False))
                        target_pack = semantics.get("pack", None)
                        self.sy_day_total_h[(sy, day_idx, parity)] = self.sy_day_total_h.get((sy, day_idx, parity), 0) + h
                        self.sy_day_bits[(sy, day_idx, parity)] = self.sy_day_bits.get((sy, day_idx, parity), 0) | bit
                        if module_category(m) == "course":
                            self.sy_day_course_h[(sy, day_idx, parity)] = self.sy_day_course_h.get((sy, day_idx, parity), 0) + h
                        if target_optional and target_pack is not None:
                                key = (sy, day_idx, parity, int(target_pack), "course")
                                self.sy_day_optional_pack_sum_h[key] = self.sy_day_optional_pack_sum_h.get(key, 0) + h
                                self.sy_day_optional_pack_max_h[key] = max(self.sy_day_optional_pack_max_h.get(key, 0), h)
                else:
                    sy = target_study_year_ids[0]
                    semantics = target_semantics_for_study_year(p.task, _module_index, sy, m)
                    target_optional = bool(semantics.get("optional", False))
                    target_pack = semantics.get("pack", None)
                    self.sy_day_total_h[(sy, day_idx, parity)] = self.sy_day_total_h.get((sy, day_idx, parity), 0) + h
                    self.sy_day_bits[(sy, day_idx, parity)] = self.sy_day_bits.get((sy, day_idx, parity), 0) | bit
                    if target_group_index is not None:
                        gk = (sy, int(target_group_index), parity)
                        self.sy_group_week_h[gk] = self.sy_group_week_h.get(gk, 0) + h
                    if target_optional and target_pack is not None:
                            key = (sy, day_idx, parity, int(target_pack), "labsem")
                            self.sy_day_optional_pack_sum_h[key] = self.sy_day_optional_pack_sum_h.get(key, 0) + h
                            self.sy_day_optional_pack_max_h[key] = max(self.sy_day_optional_pack_max_h.get(key, 0), h)

                if tid:
                    self.t_day_total_h[(tid, day_idx, parity)] = self.t_day_total_h.get((tid, day_idx, parity), 0) + h
                    if is_course(m):
                        self.t_day_course_h[(tid, day_idx, parity)] = self.t_day_course_h.get((tid, day_idx, parity), 0) + h
                    key = (tid, day_idx, parity)
                    self.t_day_bits[key] = self.t_day_bits.get(key, 0) | bit
                    self.t_day_has_any[key] = True
