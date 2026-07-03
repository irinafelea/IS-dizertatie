from typing import Dict, List, Tuple

from app.models.TaskDTO import TaskDTO
from helpers.module import discipline_id
from helpers.task_module_target import task_has_optional_semantics
from helpers.teacher import teacher_uuid


def is_flexible_mandatory_labsem(task: TaskDTO) -> bool:
    """
    Checks whether a task can use flexible mandatory lab or seminar grouping

    Args:
        task: Task to evaluate

    Returns:
        True if the task supports flexible mandatory grouping
    """
    return (
        task.category == "labsem"
        and not task_has_optional_semantics(task)
        and not bool(task.common)
        and task.groupIndex is not None
        and not str(task.pairGroupKey or "").strip()
    )


def flex_group_pool_key(task: TaskDTO) -> Tuple:
    """
    Builds the grouping key for flexible mandatory lab or seminar tasks

    Args:
        task: Task used to build the grouping key

    Returns:
        Key used to group compatible flexible tasks
    """
    module = task.modules[0]
    return (
        teacher_uuid(module),
        discipline_id(module),
        tuple(str(x) for x in (task.studyYearsIds or ())),
        str(task.studyYearsLabels or ""),
        int(task.durationHours or 0),
        str(task.category or ""),
    )


def build_flexible_group_options(tasks: List[TaskDTO]) -> Dict[int, List[dict]]:
    """
    Builds reusable flexible group options for compatible tasks

    Args:
        tasks: All tasks from the timetable instance

    Returns:
        Flexible group options indexed by task index
    """
    grouped: Dict[Tuple, List[int]] = {}
    out: Dict[int, List[dict]] = {}

    for idx, task in enumerate(tasks):
        if not is_flexible_mandatory_labsem(task):
            continue
        grouped.setdefault(flex_group_pool_key(task), []).append(idx)

    for indices in grouped.values():
        options = []
        seen = set()
        for idx in indices:
            task = tasks[idx]
            option = (
                int(task.groupIndex or 0),
                int(task.groupSpan or 1),
                int(task.numberOfStudents or 0),
            )
            if option in seen:
                continue
            seen.add(option)
            options.append(
                {
                    "groupIndex": option[0],
                    "groupSpan": option[1],
                    "numberOfStudents": option[2],
                }
            )

        options.sort(key=lambda x: (x["groupIndex"], x["groupSpan"], x["numberOfStudents"]))

        for idx in indices:
            out[idx] = options

    return out
