from typing import List

from app.models.TaskDTO import TaskDTO
from app.models.TimeslotDTO import TimeslotDTO
from constants.algorithm import BOTH, ODD, EVEN
from helpers.module import module_hours


def logical_module_count(task: TaskDTO) -> int:
    """
    Returns the effective module count for a task

    Args:
        task: Task to inspect

    Returns:
        Effective number of logical modules in the task
    """
    explicit_count = int(getattr(task, "numberOfModules", 0) or 0)
    if explicit_count > 0:
        return min(explicit_count, len(task.modules))
    targets = list(getattr(task, "moduleTargets", None) or [])
    if targets:
        return min(len(targets), len(task.modules))
    return len(task.modules)


def task_module_orders(task: TaskDTO) -> list[tuple[int, ...]]:
    """
    Returns the valid module orders for a task

    Args:
        task: Task to inspect

    Returns:
        Module orders that can be used for the task
    """
    module_count = logical_module_count(task)
    if module_count <= 1:
        return [tuple(range(module_count))]

    natural_order = tuple(range(module_count))
    reversed_order = tuple(reversed(range(module_count)))

    if task.durationHours == 1 and module_count == 2:
        if all(module_hours(task.modules[index]) == 1 for index in range(module_count)):
            return [natural_order, reversed_order]

    if task.durationHours == 3 and module_count == 2:
        h0 = module_hours(task.modules[0])
        h1 = module_hours(task.modules[1])
        if {h0, h1} == {2, 1}:
            return [natural_order, reversed_order]

    return [natural_order]


def segment_mask(module, placement_parity_mask: int) -> int:
    """
    Resolves the parity mask for a task segment

    Args:
        module: Module placed in the segment
        placement_parity_mask: Parity mask chosen for the placement

    Returns:
        Effective parity mask for the segment
    """
    return BOTH if module_hours(module) >= 2 else placement_parity_mask


def normalize_module_order(
    task: TaskDTO,
    module_order: tuple[int, ...] | list[int] | list[list[int]] | tuple[tuple[int, ...], ...] | None = None,
) -> tuple[int, ...]:
    """
    Normalizes a module order into a valid tuple of indices

    Args:
        task: Task that owns the modules
        module_order: Candidate module order to normalize

    Returns:
        Valid normalized module order
    """
    default_order = task_module_orders(task)[0]
    order = module_order if module_order is not None else default_order

    def extract_indices(value) -> list[int]:
        if value is None:
            return []

        if isinstance(value, (list, tuple)):
            if not value:
                return []

            if all(item is None or isinstance(item, (list, tuple)) for item in value):
                for item in value:
                    nested = extract_indices(item)
                    if nested:
                        return nested
                return []

            out: list[int] = []
            for item in value:
                if item is None:
                    continue
                if isinstance(item, (list, tuple)):
                    nested = extract_indices(item)
                    if nested:
                        out.extend(nested)
                    continue
                try:
                    out.append(int(item))
                except (TypeError, ValueError):
                    continue
            return out

        try:
            return [int(value)]
        except (TypeError, ValueError):
            return []

    indices = extract_indices(order)
    module_count = logical_module_count(task)
    valid = [idx for idx in indices if 0 <= idx < module_count]

    if not valid:
        return tuple(default_order)

    return tuple(valid)


def iter_task_segments(
    task: TaskDTO,
    start_row: int,
    placement_parity_mask: int,
    module_order: tuple[int, ...] | None = None,
) -> list[tuple[object, int, int, int]]:
    """
    Expands a placement into its task segments

    Args:
        task: Task being expanded
        start_row: First placement row
        placement_parity_mask: Placement parity mask
        module_order: Module order used by the placement

    Returns:
        Segment list with module, row, mask, and module index
    """
    order = normalize_module_order(task, module_order)
    out: list[tuple[object, int, int, int]] = []

    module_count = logical_module_count(task)

    if task.durationHours == 1 and module_count == 2 and all(module_hours(task.modules[index]) == 1 for index in range(module_count)):
        parity_by_offset = [ODD, EVEN]
        for offset, module_index in enumerate(order[:2]):
            module = task.modules[module_index]
            out.append((module, start_row, parity_by_offset[offset], module_index))
        return out

    for offset, module_index in enumerate(order[:module_count]):
        module = task.modules[module_index]
        row = start_row + offset
        mask = segment_mask(module, placement_parity_mask)
        out.append((module, row, mask, module_index))

    return out


def rows_fit_same_day(task: TaskDTO, start_row: int, timeslots: List[TimeslotDTO]) -> bool:
    """
    Checks whether all task rows stay within the same day

    Args:
        task: Task to validate
        start_row: First candidate row
        timeslots: All timetable timeslots

    Returns:
        True if the task fits entirely within one day
    """
    if not task.modules:
        return False

    module_count = logical_module_count(task)

    if task.durationHours == 1 and module_count == 2 and all(module_hours(task.modules[index]) == 1 for index in range(module_count)):
        return True

    spd = len(timeslots)
    if spd <= 0:
        return False

    end_row = start_row + module_count - 1
    return (start_row // spd) == (end_row // spd)
