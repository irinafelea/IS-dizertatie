from algorithm.algorithm_classes.Occ import Occ
from constants.penalties import PEN_STUDENT_EXTRA_GAP, PEN_STUDENT_WIDE_SPAN


def student_day_compactness_parts(bits: int) -> tuple[int, int, int, int]:
    """
    Computes the compactness parts for one student day bitmask

    Args:
        bits: Student day occupancy bitmask

    Returns:
        Extra-gap penalty, extra-gap count, wide-span penalty, and wide-span count
    """
    if bits == 0:
        return 0, 0, 0, 0

    first_teaching_slot = (bits & -bits).bit_length() - 1
    last_teaching_slot = bits.bit_length() - 1

    gap_run_count = 0
    wide_span_count = 0
    current_pause_run = 0

    for slot in range(first_teaching_slot, last_teaching_slot + 1):
        teaching_hour = ((bits >> slot) & 1) != 0

        if teaching_hour:
            if current_pause_run > 0:
                gap_run_count += 1
                if current_pause_run > 1:
                    wide_span_count += 1
                current_pause_run = 0
        else:
            current_pause_run += 1

    extra_gap_count = max(0, gap_run_count - 1)
    extra_gap_penalty = extra_gap_count * PEN_STUDENT_EXTRA_GAP
    wide_span_penalty = wide_span_count * PEN_STUDENT_WIDE_SPAN
    return extra_gap_penalty, extra_gap_count, wide_span_penalty, wide_span_count


def student_compactness_breakdown(occ: Occ) -> dict[str, int]:
    """
    Computes the student compactness breakdown

    Args:
        occ: Current occupancy state

    Returns:
        Student compactness penalties and counts
    """
    total_penalty = 0
    total_count = 0
    extra_gap_count = 0
    wide_span_count = 0

    for bits in occ.sy_day_bits.values():
        extra_gap_penalty, current_extra_gap_count, wide_span_penalty, current_wide_span_count = student_day_compactness_parts(bits)
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
