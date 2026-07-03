from collections import Counter

from helpers.module import module_category
from helpers.teacher import teacher_id


def final_summary(best):
    """
    Prints a short summary of the final solution

    Args:
        best: Final placement list

    Returns:
        None
    """
    teacher_load = Counter()
    placed_types = Counter()

    for p in best:
        if p is None:
            continue

        m = p.module
        cat = module_category(m)

        if cat == "course":
            placed_types["courses"] += 1
        elif cat in ("laboratory", "seminar"):
            placed_types["labs_seminars"] += 1
        else:
            placed_types["other"] += 1

        tid = teacher_id(m)
        if tid:
            teacher_load[tid] += 1

    print("\n=== SOLUTION SUMMARY ===")
    print(f"Placed courses: {placed_types['courses']}")
    print(f"Placed labs/seminars: {placed_types['labs_seminars']}")
    print(f"Placed other: {placed_types['other']}")
    print(f"Unplaced tasks: {sum(1 for p in best if p is None)}")
