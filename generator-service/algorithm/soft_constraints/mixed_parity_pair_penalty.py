from algorithm.algorithm_classes.Occ import Occ
from constants.penalties import PEN_MIXED_PARITY_PAIR_GROUP, PEN_MIXED_PARITY_PAIR_SY
from helpers.module import is_course


def mixed_parity_pair_group_penalty(occ: Occ) -> tuple[int, int]:
    """
    Computes the mixed-parity pair penalty at group level

    Args:
        occ: Current occupancy state

    Returns:
        Penalty and violation count
    """
    count = 0

    for parity_by_week in occ.sy_group_row_kind.values():
        odd_kind = parity_by_week.get("O")
        even_kind = parity_by_week.get("E")

        if _is_mixed_course_and_lab_pair(odd_kind, even_kind):
            count += 1

    return count * PEN_MIXED_PARITY_PAIR_GROUP, count


def mixed_parity_pair_study_year_penalty(occ: Occ) -> tuple[int, int]:
    """
    Computes the mixed-parity pair penalty at study year level

    Args:
        occ: Current occupancy state

    Returns:
        Penalty and violation count
    """
    count = 0

    for parity_by_week in occ.sy_row_kind.values():
        odd_kind = parity_by_week.get("O")
        even_kind = parity_by_week.get("E")

        if _is_mixed_course_and_lab_pair(odd_kind, even_kind):
            count += 1

    return count * PEN_MIXED_PARITY_PAIR_SY, count


def _is_mixed_course_and_lab_pair(odd_kind: str | None, even_kind: str | None) -> bool:
    """
    Checks whether two parity kinds form a mixed course and lab pair

    Args:
        odd_kind: Odd-week activity kind
        even_kind: Even-week activity kind

    Returns:
        True if the pair mixes course and non-course activities
    """
    return (
        odd_kind is not None
        and even_kind is not None
        and odd_kind != even_kind
        and (is_course(odd_kind) or is_course(even_kind))
    )
