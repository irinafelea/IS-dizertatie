from algorithm.algorithm_classes.Occ import Occ
from constants.penalties import PEN_TEACHER_EXTRA_GAP, PEN_TEACHER_WIDE_SPAN


def teacher_day_compactness_parts(bits: int) -> tuple[int, int, int, int]:
    """
    Computes the compactness parts for one teacher day bitmask

    Args:
        bits: Teacher day occupancy bitmask

    Returns:
        Extra-gap penalty, extra-gap count, wide-span penalty, and wide-span count
    """
    if bits == 0:
        return 0, 0, 0, 0

    first_teaching_slot = (bits & -bits).bit_length() - 1
    last_teaching_slot = bits.bit_length() - 1

    teaching_runs: list[int] = []
    gap_runs: list[int] = []

    slot = first_teaching_slot
    while slot <= last_teaching_slot:
        teaching_run = 0
        while slot <= last_teaching_slot and ((bits >> slot) & 1) != 0:
            teaching_run += 1
            slot += 1
        if teaching_run > 0:
            teaching_runs.append(teaching_run)

        gap_run = 0
        while slot <= last_teaching_slot and ((bits >> slot) & 1) == 0:
            gap_run += 1
            slot += 1
        if gap_run > 0:
            gap_runs.append(gap_run)

    extra_gap_count = 0
    wide_span_count = 0

    for index, gap_length in enumerate(gap_runs):
        left_teaching_run = teaching_runs[index]
        right_teaching_run = teaching_runs[index + 1]

        if gap_length == 1 and left_teaching_run == 1 and right_teaching_run == 1:
            extra_gap_count += 1

        if gap_length > 1:
            wide_span_count += 1

    extra_gap_penalty = extra_gap_count * PEN_TEACHER_EXTRA_GAP
    wide_span_penalty = wide_span_count * PEN_TEACHER_WIDE_SPAN
    return extra_gap_penalty, extra_gap_count, wide_span_penalty, wide_span_count


def teacher_day_compactness_penalty(bits: int) -> int:
    """
    Computes the total compactness penalty for one teacher day

    Args:
        bits: Teacher day occupancy bitmask

    Returns:
        Total compactness penalty
    """
    extra_gap_penalty, _extra_gap_count, wide_span_penalty, _wide_span_count = teacher_day_compactness_parts(bits)
    return extra_gap_penalty + wide_span_penalty


def teacher_compactness_breakdown(occ: Occ) -> dict[str, int]:
    """
    Computes the teacher compactness breakdown

    Args:
        occ: Current occupancy state

    Returns:
        Teacher compactness penalties and counts
    """
    total_penalty = 0
    total_count = 0
    extra_gap_count = 0
    wide_span_count = 0

    for bits in occ.t_day_bits.values():
        extra_gap_penalty, current_extra_gap_count, wide_span_penalty, current_wide_span_count = teacher_day_compactness_parts(bits)
        total_penalty += extra_gap_penalty + wide_span_penalty
        total_count += current_extra_gap_count + current_wide_span_count
        extra_gap_count += current_extra_gap_count
        wide_span_count += current_wide_span_count

    return {
        "penalty": total_penalty,
        "count": total_count,
        "extra_gap_count": extra_gap_count,
        "wide_span_count": wide_span_count,
    }
