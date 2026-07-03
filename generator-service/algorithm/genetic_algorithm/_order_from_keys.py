from typing import List

from algorithm.algorithm_helpers.task_priority import task_priority
from app.models.TaskDTO import TaskDTO


def _order_from_keys(tasks: List[TaskDTO], cells_cache, keys: List[float]) -> List[int]:
    """
    Builds the task construction order from random keys

    Args:
        tasks: All tasks from the timetable instance
        cells_cache: Cached candidate cells by task
        keys: Random-key priorities for each task

    Returns:
        Task indices sorted by scheduling priority and random keys
    """
    return sorted(
        range(len(tasks)),
        key=lambda i: (
            task_priority(tasks[i], len(cells_cache[i]), cells_cache[i]),
            keys[i]
        )
    )
