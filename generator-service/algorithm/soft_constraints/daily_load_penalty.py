from algorithm.algorithm_classes.Occ import Occ
from constants.algorithm import MAX_COURSE_HOURS_PER_DAY_PER_SY, MAX_TOTAL_HOURS_PER_DAY_PER_SY, \
    MAX_TOTAL_HOURS_PER_DAY_PER_TEACHER, MAX_COURSE_HOURS_PER_DAY_PER_TEACHER
from constants.penalties import PEN_STUDENT_TOTAL_OVERLOAD_PER_DAY, PEN_STUDENT_COURSE_OVERLOAD_PER_DAY, \
    PEN_TEACHER_TOTAL_OVERLOAD_PER_DAY, PEN_TEACHER_COURSE_OVERLOAD_PER_DAY


def _optional_duplicate_adjustment(occ: Occ, sy: str, day: int, parity: str, category: str | None = None) -> int:
    """
    Removes duplicated optional-pack hours from day totals

    Args:
        occ: Current occupancy state
        sy: Study year identifier
        day: Day index
        parity: Week parity label
        category: Optional category filter

    Returns:
        Adjustment that should be subtracted from raw hours
    """
    duplicate_hours = 0

    for key, raw_sum in occ.sy_day_optional_pack_sum_h.items():
        key_sy, key_day, key_parity, _pack, key_category = key
        if key_sy != sy or key_day != day or key_parity != parity:
            continue
        if category is not None and key_category != category:
            continue

        max_h = occ.sy_day_optional_pack_max_h.get(key, 0)
        duplicate_hours += max(0, raw_sum - max_h)

    return duplicate_hours


def daily_load_penalty_parts(occ: Occ) -> dict[str, int]:
    """
    Computes the separate daily-load penalty components

    Args:
        occ: Current occupancy state

    Returns:
        Penalty parts and counts for students and teachers
    """
    student_course_penalty = 0
    student_course_count = 0
    student_total_penalty = 0
    student_total_count = 0
    teacher_total_penalty = 0
    teacher_total_count = 0
    teacher_course_penalty = 0
    teacher_course_count = 0

    for (study_year_id, day_index, parity), hours in occ.sy_day_course_h.items():
        adjusted_hours = hours - _optional_duplicate_adjustment(occ, study_year_id, day_index, parity, category="course")
        if adjusted_hours > MAX_COURSE_HOURS_PER_DAY_PER_SY:
            student_course_penalty += (adjusted_hours - MAX_COURSE_HOURS_PER_DAY_PER_SY) * PEN_STUDENT_COURSE_OVERLOAD_PER_DAY
            student_course_count += 1

    for (study_year_id, day_index, parity), hours in occ.sy_day_total_h.items():
        adjusted_hours = hours - _optional_duplicate_adjustment(occ, study_year_id, day_index, parity)
        if adjusted_hours > MAX_TOTAL_HOURS_PER_DAY_PER_SY:
            student_total_penalty += (adjusted_hours - MAX_TOTAL_HOURS_PER_DAY_PER_SY) * PEN_STUDENT_TOTAL_OVERLOAD_PER_DAY
            student_total_count += 1

    for (_teacher_id, _day_index, _parity), hours in occ.t_day_total_h.items():
        if hours > MAX_TOTAL_HOURS_PER_DAY_PER_TEACHER:
            teacher_total_penalty += (hours - MAX_TOTAL_HOURS_PER_DAY_PER_TEACHER) * PEN_TEACHER_TOTAL_OVERLOAD_PER_DAY
            teacher_total_count += 1

    for (_teacher_id, _day_index, _parity), hours in occ.t_day_course_h.items():
        if hours > MAX_COURSE_HOURS_PER_DAY_PER_TEACHER:
            teacher_course_penalty += (hours - MAX_COURSE_HOURS_PER_DAY_PER_TEACHER) * PEN_TEACHER_COURSE_OVERLOAD_PER_DAY
            teacher_course_count += 1

    return {
        "student_total_penalty": student_total_penalty,
        "student_total_count": student_total_count,
        "student_course_penalty": student_course_penalty,
        "student_course_count": student_course_count,
        "teacher_total_penalty": teacher_total_penalty,
        "teacher_total_count": teacher_total_count,
        "teacher_course_penalty": teacher_course_penalty,
        "teacher_course_count": teacher_course_count,
    }


def daily_load_penalty(occ: Occ) -> tuple[int, int]:
    """
    Computes the total daily-load penalty

    Args:
        occ: Current occupancy state

    Returns:
        Total penalty and total violation count
    """
    parts = daily_load_penalty_parts(occ)
    penalty = (
        parts["student_total_penalty"]
        + parts["student_course_penalty"]
        + parts["teacher_total_penalty"]
        + parts["teacher_course_penalty"]
    )
    count = (
        parts["student_total_count"]
        + parts["student_course_count"]
        + parts["teacher_total_count"]
        + parts["teacher_course_count"]
    )
    return penalty, count
