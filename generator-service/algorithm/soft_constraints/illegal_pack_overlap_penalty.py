from typing import List, Optional

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers.task_segments import iter_task_segments
from constants.algorithm import EVEN, ODD
from constants.penalties import PEN_ILLEGAL_PACK_OVERLAP
from helpers.module import discipline_uuid, is_course
from helpers.task_module_target import module_target, target_semantics_for_study_year


def _group_range(group_index, group_span) -> set[int]:
    """
    Builds the set of group indices covered by a segment

    Args:
        group_index: Starting group index
        group_span: Number of covered groups

    Returns:
        Group indices covered by the segment
    """
    if group_index is None:
        return set()
    start = int(group_index)
    span = int(group_span or 1)
    return set(range(start, start + span))


def _segment_study_year_ids(task, module_index: int) -> tuple[str, ...]:
    """
    Returns the study year identifiers for one task segment

    Args:
        task: Task that owns the segment
        module_index: Segment module index

    Returns:
        Study year identifiers covered by the segment
    """
    target = module_target(task, module_index)
    return tuple(str(x) for x in (target.get("studyYearsIds") or ()))


def _segment_group_range(task, module_index: int) -> set[int]:
    """
    Returns the covered group range for one task segment

    Args:
        task: Task that owns the segment
        module_index: Segment module index

    Returns:
        Group indices covered by the segment
    """
    target = module_target(task, module_index)
    return _group_range(
        target.get("groupIndex", getattr(task, "groupIndex", None)),
        target.get("groupSpan", getattr(task, "groupSpan", 1)),
    )


def _share_students(t1, m1, module_index_1: int, t2, m2, module_index_2: int) -> bool:
    """
    Checks whether two segments affect the same students

    Args:
        t1: First task
        m1: First module
        module_index_1: First module index
        t2: Second task
        m2: Second module
        module_index_2: Second module index

    Returns:
        True if the segments share students
    """
    sy1 = set(_segment_study_year_ids(t1, module_index_1))
    sy2 = set(_segment_study_year_ids(t2, module_index_2))
    common_sy = sy1 & sy2
    if not common_sy:
        return False

    if is_course(m1) or is_course(m2):
        return True

    return bool(_segment_group_range(t1, module_index_1) & _segment_group_range(t2, module_index_2))


def _allowed_overlap(p1: Placement, m1, module_index_1: int, p2: Placement, m2, module_index_2: int) -> bool:
    """
    Checks whether two overlapping optional segments are allowed

    Args:
        p1: First placement
        m1: First module
        module_index_1: First module index
        p2: Second placement
        m2: Second module
        module_index_2: Second module index

    Returns:
        True if the overlap is allowed
    """
    common_sy = set(_segment_study_year_ids(p1.task, module_index_1)) & set(_segment_study_year_ids(p2.task, module_index_2))
    if not common_sy:
        return False

    for sy in common_sy:
        semantics_1 = target_semantics_for_study_year(p1.task, module_index_1, sy, m1)
        semantics_2 = target_semantics_for_study_year(p2.task, module_index_2, sy, m2)

        if not bool(semantics_1.get("optional", False)) or not bool(semantics_2.get("optional", False)):
            continue

        pack_1 = semantics_1.get("pack", None)
        pack_2 = semantics_2.get("pack", None)

        if pack_1 is None or pack_2 is None:
            continue
        if int(pack_1) != int(pack_2):
            continue

        did1 = str(semantics_1.get("disciplineId") or discipline_uuid(m1) or "")
        did2 = str(semantics_2.get("disciplineId") or discipline_uuid(m2) or "")
        if did1 and did2 and did1 != did2:
            return True

    return False


def _parities_overlap(mask_1: int, mask_2: int) -> bool:
    """
    Checks whether two parity masks overlap

    Args:
        mask_1: First parity mask
        mask_2: Second parity mask

    Returns:
        True if the masks share at least one parity
    """
    return bool(mask_1 & mask_2 & (ODD | EVEN))


def illegal_pack_overlap_penalty(
    placements: List[Optional[Placement]],
) -> tuple[int, int]:
    """
    Computes the illegal optional-pack overlap penalty

    Args:
        placements: Current placement list

    Returns:
        Penalty and violation count
    """
    violations = 0
    placed = [p for p in placements if p is not None]

    for i in range(len(placed)):
        p1 = placed[i]
        segments_1 = iter_task_segments(p1.task, p1.row, p1.parity_mask, p1.module_order)

        for j in range(i + 1, len(placed)):
            p2 = placed[j]
            segments_2 = iter_task_segments(p2.task, p2.row, p2.parity_mask, p2.module_order)

            for m1, row_1, mask_1, module_index_1 in segments_1:
                for m2, row_2, mask_2, module_index_2 in segments_2:
                    if row_1 != row_2:
                        continue
                    if not _parities_overlap(mask_1, mask_2):
                        continue
                    if not _share_students(p1.task, m1, module_index_1, p2.task, m2, module_index_2):
                        continue
                    if _allowed_overlap(p1, m1, module_index_1, p2, m2, module_index_2):
                        continue

                    violations += 1

    return violations * PEN_ILLEGAL_PACK_OVERLAP, violations
