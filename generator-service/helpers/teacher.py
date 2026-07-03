from typing import Optional

from helpers._dget import _dget
from app.models.ModuleDTO import ModuleDTO


def teacher_id(m: ModuleDTO) -> Optional[str]:
    """
    Returns the normalized teacher id used in occupancy keys

    Args:
        m: Source module

    Returns:
        Normalized teacher id when present
    """

    t = _dget(m, "teacher", None)
    tid = _dget(t, "id", None)
    return f"ID:{tid}" if tid else None


def teacher_uuid(m: ModuleDTO) -> Optional[str]:
    """
    Returns the raw teacher uuid stored on the module

    Args:
        m: Source module

    Returns:
        Raw teacher uuid when present
    """
    tid = _dget(m, "tid", None)
    return str(tid) if tid else None
