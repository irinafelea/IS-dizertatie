from dataclasses import dataclass
from typing import Optional

from algorithm.algorithm_helpers.task_segments import normalize_module_order
from app.models.ModuleDTO import ModuleDTO
from app.models.TaskDTO import TaskDTO


@dataclass
class Placement:
    """
    Stores the chosen placement of one task
    """
    task: TaskDTO
    row: int
    col: int
    parity_mask: int
    module_order: tuple[int, ...] | None = None

    @property
    def module(self) -> ModuleDTO:
        """
        Returns the first effective module of the placement

        Args:
            None

        Returns:
            Effective first module
        """
        if self.module_order:
            order = normalize_module_order(self.task, self.module_order)
            return self.task.modules[order[0]]
        return self.task.modules[0]

    @property
    def ordered_modules(self) -> list[ModuleDTO]:
        """
        Returns the placement modules in effective order

        Args:
            None

        Returns:
            Ordered module list
        """
        if not self.module_order:
            return list(self.task.modules)
        order = normalize_module_order(self.task, self.module_order)
        return [self.task.modules[i] for i in order]

    @property
    def group_index(self) -> Optional[int]:
        """
        Returns the effective group index of the placement

        Args:
            None

        Returns:
            Effective group index
        """
        return self.task.groupIndex
