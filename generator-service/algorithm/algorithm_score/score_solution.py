from typing import Dict, List, Optional

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers.rebuild_occ import rebuild_occ
from algorithm.soft_constraints.bachelor_third_year_course_days_penalty import (
    bachelor_third_year_course_days_penalty,
    bachelor_third_year_modules_days_penalty,
)
from algorithm.soft_constraints.daily_load_penalty import daily_load_penalty, daily_load_penalty_parts
from algorithm.soft_constraints.illegal_pack_overlap_penalty import illegal_pack_overlap_penalty
from algorithm.soft_constraints.late_slot_penalty import late_slot_total_penalty
from algorithm.soft_constraints.mixed_parity_pair_penalty import (
    mixed_parity_pair_group_penalty,
    mixed_parity_pair_study_year_penalty,
)
from algorithm.soft_constraints.group_week_parity_imbalance_penalty import group_week_parity_imbalance_penalty
from algorithm.soft_constraints.onsite_online_no_pause_penalty import onsite_online_no_pause_penalty
from algorithm.soft_constraints.pair_group_different_room_penalty import pair_group_different_room_penalty
from algorithm.soft_constraints.room_single_parity_one_hour_penalty import room_single_parity_one_hour_penalty
from algorithm.soft_constraints.student_compactness_penalty import (
    student_compactness_breakdown,
)
from algorithm.soft_constraints.teacher_compactness_penalty import (
    teacher_compactness_breakdown,
)
from algorithm.soft_constraints.teacher_too_many_days_penalty import teacher_too_many_days_penalty
from algorithm.soft_constraints.teacher_row_penalty import (
    teacher_mandatory_missed_row_penalty,
    teacher_preferred_not_used_row_penalty,
)
from algorithm.soft_constraints.unplaced_penalty import unplaced_penalty
from app.models.TimeslotDTO import TimeslotDTO


def score_solution_breakdown(
    placements: List[Optional[Placement]],
    timeslots: List[TimeslotDTO],
    teachers_availabilities,
    enforce_bachelor_third_year_free_day: bool = False,
) -> Dict[str, int | float]:
    """
    Computes the full score breakdown for a timetable

    Args:
        placements: Current placement list
        timeslots: All timetable timeslots
        teachers_availabilities: Teacher availability rules
        enforce_bachelor_third_year_free_day: Whether to enforce third-year free-day penalties

    Returns:
        Breakdown with all penalty counts and the total score
    """
    spd = len(timeslots)
    penalty = 0

    unplaced_penalty_value, unplaced_count = unplaced_penalty(placements)
    placed_count = len(placements) - unplaced_count
    penalty += unplaced_penalty_value

    late_penalty, late_count = late_slot_total_penalty(placements, timeslots, teachers_availabilities)
    penalty += late_penalty

    occ = rebuild_occ(placements, timeslots, teachers_availabilities)

    mixed_parity_group_pen, mixed_parity_group_count = mixed_parity_pair_group_penalty(occ)
    mixed_parity_study_year_pen, mixed_parity_study_year_count = mixed_parity_pair_study_year_penalty(occ)
    daily_load_pen, daily_load_count = daily_load_penalty(occ)
    daily_load_parts = daily_load_penalty_parts(occ)
    student_compactness_parts = student_compactness_breakdown(occ)
    teacher_compactness_parts = teacher_compactness_breakdown(occ)
    teacher_too_many_days_penalty_value, teacher_too_many_days_count = teacher_too_many_days_penalty(occ)
    pair_group_different_room_penalty_value, pair_group_different_room_count = pair_group_different_room_penalty(placements)
    illegal_pack_pen, illegal_pack_overlap_count = illegal_pack_overlap_penalty(placements)
    onsite_online_no_pause_pen, onsite_online_no_pause_count = onsite_online_no_pause_penalty(placements, timeslots)
    room_single_parity_pen, room_single_parity_count = room_single_parity_one_hour_penalty(placements)
    group_week_imbalance_pen, group_week_parity_imbalance_count = group_week_parity_imbalance_penalty(placements)
    teacher_mandatory_pen, teacher_mandatory_missed_count = teacher_mandatory_missed_row_penalty(
        placements,
        teachers_availabilities,
    )
    teacher_preferred_pen, teacher_preferred_missed_count = teacher_preferred_not_used_row_penalty(
        placements,
        teachers_availabilities,
    )

    bachelor_course_days_pen = 0
    bachelor_third_year_course_day_over_limit_count = 0
    bachelor_modules_days_pen = 0
    bachelor_third_year_modules_day_over_limit_count = 0
    if enforce_bachelor_third_year_free_day:
        bachelor_course_days_pen, bachelor_third_year_course_day_over_limit_count = (
            bachelor_third_year_course_days_penalty(placements, spd)
        )
        bachelor_modules_days_pen, bachelor_third_year_modules_day_over_limit_count = (
            bachelor_third_year_modules_days_penalty(placements, spd)
        )
    teacher_row_preference_penalty = teacher_mandatory_pen + teacher_preferred_pen

    penalty += mixed_parity_group_pen
    penalty += mixed_parity_study_year_pen
    penalty += daily_load_pen
    penalty += student_compactness_parts["penalty"]
    penalty += teacher_compactness_parts["penalty"]
    penalty += teacher_too_many_days_penalty_value
    penalty += pair_group_different_room_penalty_value
    penalty += illegal_pack_pen
    penalty += onsite_online_no_pause_pen
    penalty += room_single_parity_pen
    penalty += group_week_imbalance_pen
    penalty += bachelor_course_days_pen
    penalty += bachelor_modules_days_pen
    penalty += teacher_row_preference_penalty

    return {
        "placed_count": placed_count,
        "unplaced_count": unplaced_count,
        "late_slots_count": late_count,
        "mixed_parity_pair_group_count": mixed_parity_group_count,
        "mixed_parity_pair_study_year_count": mixed_parity_study_year_count,
        "daily_load_count": daily_load_count,
        "students_daily_overload_count": daily_load_parts["student_total_count"],
        "students_daily_courses_overload_count": daily_load_parts["student_course_count"],
        "teachers_daily_overload_count": daily_load_parts["teacher_total_count"],
        "teachers_daily_courses_overload_count": daily_load_parts["teacher_course_count"],
        "students_extra_gap_count": student_compactness_parts["extra_gap_count"],
        "student_wide_span_count": student_compactness_parts["wide_span_count"],
        "teachers_extra_gap_count": teacher_compactness_parts["extra_gap_count"],
        "teacher_wide_span_count": teacher_compactness_parts["wide_span_count"],
        "teacher_too_many_days_count": teacher_too_many_days_count,
        "pair_group_different_room_count": pair_group_different_room_count,
        "illegal_pack_overlap_count": illegal_pack_overlap_count,
        "onsite_online_no_pause_count": onsite_online_no_pause_count,
        "room_single_parity_one_hour_count": room_single_parity_count,
        "group_week_parity_imbalance_count": group_week_parity_imbalance_count,
        "bachelor_third_year_course_day_over_limit_count": bachelor_third_year_course_day_over_limit_count,
        "bachelor_third_year_modules_day_over_limit_count": bachelor_third_year_modules_day_over_limit_count,
        "teacher_mandatory_missed_count": teacher_mandatory_missed_count,
        "teacher_preferred_missed_count": teacher_preferred_missed_count,
        "total": penalty,
    }


def score_solution(
    placements: List[Optional[Placement]],
    timeslots: List[TimeslotDTO],
    teachers_availabilities,
    enforce_bachelor_third_year_free_day: bool = False,
) -> int:
    """
    Computes the total penalty of a timetable

    Args:
        placements: Current placement list
        timeslots: All timetable timeslots
        teachers_availabilities: Teacher availability rules
        enforce_bachelor_third_year_free_day: Whether to enforce third-year free-day penalties

    Returns:
        Total timetable penalty
    """
    return int(
        score_solution_breakdown(
            placements,
            timeslots,
            teachers_availabilities,
            enforce_bachelor_third_year_free_day=enforce_bachelor_third_year_free_day,
        )["total"]
    )
