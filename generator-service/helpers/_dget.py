from typing import Any


def _dget(obj: Any, key: str, default=None):
    """
    Safely reads a dictionary key or object attribute

    Args:
        obj: Source object or dictionary
        key: Field name to retrieve
        default: Fallback value when the field is missing

    Returns:
        Retrieved value or the fallback value
    """

    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, key):
        val = getattr(obj, key)
        return default if val is None else val
    d = getattr(obj, "__dict__", None)
    if isinstance(d, dict) and key in d:
        val = d.get(key)
        return default if val is None else val
    return default
