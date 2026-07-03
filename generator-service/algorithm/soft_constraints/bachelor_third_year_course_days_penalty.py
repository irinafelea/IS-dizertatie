from typing import Optional

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers.task_segments import iter_task_segments
from constants.penalties import (
    PEN_BACHELOR_THIRD_YEAR_COURSE_DAY_OVER_LIMIT,
    PEN_BACHELOR_THIRD_YEAR_MODULES_DAY_OVER_LIMIT,
)
from constants.algorithm import MAX_BACHELOR_THIRD_YEAR_DAYS
from helpers.module import is_course, is_master_module
from helpers.task_module_target import target_study_year_entries


def _is_third_year_entry(entry: dict) -> bool:
    """
    Checks whether a study year entry belongs to year three

    Args:
        entry: Study year entry to inspect

    Returns:
        True if the entry label ends with 3
    """
    label = str(entry.get("studyYearLabel") or "").strip()
    return label.endswith("3")


def _entry_study_year_id(entry: dict) -> str:
    """
    Returns the normalized study year identifier from an entry

    Args:
        entry: Study year entry to inspect

    Returns:
        Normalized study year identifier
    """
    return str(entry.get("studyYearId") or "").strip()


def _third_year_active_days(
    placements: list[Optional[Placement]],
    slots_per_day: int,
    *,
    courses_only: bool,
) -> dict[str, set[int]]:
    """
    Collects active days for third-year study years

    Args:
        placements: Current placement list
        slots_per_day: Number of timeslots per day
        courses_only: Whether to include only course segments

    Returns:
        Active day indices grouped by study year
    """
    if slots_per_day <= 0:
        return {}

    days_by_study_year: dict[str, set[int]] = {}

    for placement in placements:
        if placement is None:
            continue

        task = placement.task
        for module, row, _mask, module_index in iter_task_segments(
            task,
            placement.row,
            placement.parity_mask,
            placement.module_order,
        ):
            if is_master_module(module):
                continue
            if courses_only and not is_course(module):
                continue

            day_index = row // slots_per_day
            for entry in target_study_year_entries(task, module_index, module):
                if not _is_third_year_entry(entry):
                    continue
                study_year_id = _entry_study_year_id(entry)
                if not study_year_id:
                    continue
                days_by_study_year.setdefault(study_year_id, set()).add(day_index)

    return days_by_study_year


def _over_limit_count(days_by_study_year: dict[str, set[int]]) -> int:
    """
    Counts third-year study years that exceed the day limit

    Args:
        days_by_study_year: Active day indices grouped by study year

    Returns:
        Total number of days above the allowed limit
    """
    return sum(
        max(0, len(active_days) - MAX_BACHELOR_THIRD_YEAR_DAYS)
        for active_days in days_by_study_year.values()
    )


def bachelor_third_year_course_days_penalty(
    placements: list[Optional[Placement]],
    slots_per_day: int,
) -> tuple[int, int]:
    """
    Computes the third-year course-day penalty

    Args:
        placements: Current placement list
        slots_per_day: Number of timeslots per day

    Returns:
        Penalty and violation count
    """
    count = _over_limit_count(
        _third_year_active_days(
            placements,
            slots_per_day,
            courses_only=True,
        )
    )
    return count * PEN_BACHELOR_THIRD_YEAR_COURSE_DAY_OVER_LIMIT, count


def bachelor_third_year_modules_days_penalty(
    placements: list[Optional[Placement]],
    slots_per_day: int,
) -> tuple[int, int]:
    """
    Computes the third-year module-day penalty

    Args:
        placements: Current placement list
        slots_per_day: Number of timeslots per day

    Returns:
        Penalty and violation count
    """
    count = _over_limit_count(
        _third_year_active_days(
            placements,
            slots_per_day,
            courses_only=False,
        )
    )
    return count * PEN_BACHELOR_THIRD_YEAR_MODULES_DAY_OVER_LIMIT, count


def _placement_day_over_limit_burden(
    placement: Optional[Placement],
    days_by_study_year: dict[str, set[int]],
    slots_per_day: int,
    *,
    courses_only: bool,
) -> int:
    """
    Computes the local over-limit impact of one placement

    Args:
        placement: Placement being evaluated
        days_by_study_year: Active day indices grouped by study year
        slots_per_day: Number of timeslots per day
        courses_only: Whether to include only course segments

    Returns:
        Local over-limit impact of the placement
    """
    if placement is None or slots_per_day <= 0:
        return 0

    burden = 0
    task = placement.task
    for module, row, _mask, module_index in iter_task_segments(
        task,
        placement.row,
        placement.parity_mask,
        placement.module_order,
    ):
        if is_master_module(module):
            continue
        if courses_only and not is_course(module):
            continue

        day_index = row // slots_per_day
        for entry in target_study_year_entries(task, module_index, module):
            if not _is_third_year_entry(entry):
                continue
            study_year_id = _entry_study_year_id(entry)
            active_days = days_by_study_year.get(study_year_id, set())
            over_limit = len(active_days) - MAX_BACHELOR_THIRD_YEAR_DAYS
            if over_limit > 0 and day_index in active_days:
                burden += over_limit

    return burden


def bachelor_third_year_course_day_over_limit_burden(
    placement: Optional[Placement],
    placements: list[Optional[Placement]],
    slots_per_day: int,
) -> int:
    """
    Computes the local course-day over-limit impact of one placement

    Args:
        placement: Placement being evaluated
        placements: Current placement list
        slots_per_day: Number of timeslots per day

    Returns:
        Local course-day over-limit impact
    """
    days_by_study_year = _third_year_active_days(
        placements,
        slots_per_day,
        courses_only=True,
    )
    return _placement_day_over_limit_burden(
        placement,
        days_by_study_year,
        slots_per_day,
        courses_only=True,
    )


def bachelor_third_year_modules_day_over_limit_burden(
    placement: Optional[Placement],
    placements: list[Optional[Placement]],
    slots_per_day: int,
) -> int:
    """
    Computes the local module-day over-limit impact of one placement

    Args:
        placement: Placement being evaluated
        placements: Current placement list
        slots_per_day: Number of timeslots per day

    Returns:
        Local module-day over-limit impact
    """
    days_by_study_year = _third_year_active_days(
        placements,
        slots_per_day,
        courses_only=False,
    )
    return _placement_day_over_limit_burden(
        placement,
        days_by_study_year,
        slots_per_day,
        courses_only=False,
    )
