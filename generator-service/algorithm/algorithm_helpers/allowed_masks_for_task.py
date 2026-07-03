from typing import List

from app.models.ModuleDTO import ModuleDTO
from constants.algorithm import BOTH, ODD, EVEN
from helpers.module import module_hours


def allowed_masks_for_task(m: ModuleDTO) -> List[int]:
    """
    Returns the parity masks allowed for a module

    Args:
        m: Module to evaluate

    Returns:
        Parity masks that can be used for the module
    """

    h = module_hours(m)
    if h >= 2:
        return [BOTH]

    return [ODD, EVEN]
