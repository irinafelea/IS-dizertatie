from collections import Counter

from helpers.teacher import teacher_uuid


def build_teacher_task_counts(tasks):
    """
    Counts tasks for each teacher

    Args:
        tasks: Timetable tasks

    Returns:
        Task counts by teacher id
    """
    counts = Counter()
    for task in tasks:
        tid = teacher_uuid(task.modules[0])
        if tid:
            counts[tid] += 1
    return dict(counts)
