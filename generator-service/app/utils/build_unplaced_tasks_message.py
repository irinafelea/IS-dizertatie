from collections import Counter
from typing import List, Optional

from algorithm.algorithm_classes.Placement import Placement
from app.models.TaskDTO import TaskDTO


def build_unplaced_summary_message(
    tasks: List[TaskDTO],
    placements: List[Optional[Placement]],
) -> str:
    """
    Builds the message for unplaced tasks

    Args:
        tasks: Source tasks
        placements: Generated placements

    Returns:
        Human-readable unplaced summary
    """
    missing_tasks = [
        tasks[i]
        for i, p in enumerate(placements)
        if p is None
    ]

    if not missing_tasks:
        return "All tasks were placed successfully."

    room_missing_tasks = [task for task in missing_tasks if not bool(getattr(task, "online", False))]
    by_students = Counter(int(t.numberOfStudents or 0) for t in room_missing_tasks)

    lines = [
        "Could not generate a fully feasible timetable.",
        f"{len(missing_tasks)} tasks remain unplaced.",
        "",
        "Required room capacities for the missing tasks:",
    ]

    if by_students:
        for students in sorted(by_students.keys(), reverse=True):
            count = by_students[students]
            lines.append(f"- {count} × {students} seats")
    else:
        lines.append("- none")

    lines.append("")
    lines.append("Unplaced tasks:")

    for task in missing_tasks:
        title = task.modules[0].title if task.modules else "Unknown module"
        teacher = task.modules[0].completeTeacher if task.modules else "Unknown module"
        online_suffix = " | online" if bool(getattr(task, "online", False)) else ""
        lines.append(
            f"- {title} - {teacher} | {task.studyYearsLabels} | "
            f"{task.numberOfStudents} students | {task.category} | {task.durationHours}h{online_suffix}"
        )

    return "\n".join(lines)
