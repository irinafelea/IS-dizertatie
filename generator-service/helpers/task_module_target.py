from typing import Any

from helpers._dget import _dget
from helpers.module import discipline_id, is_optional


def default_module_target(task) -> dict[str, Any]:
    """
    Builds the fallback module target for a task

    Args:
        task: Source task

    Returns:
        Default target dictionary
    """
    return {
        "common": bool(getattr(task, "common", False)),
        "groupIndex": getattr(task, "groupIndex", None),
        "groupSpan": getattr(task, "groupSpan", 1),
        "numberOfStudents": int(getattr(task, "numberOfStudents", 0) or 0),
        "numberOfGroups": int(getattr(task, "numberOfGroups", 0) or 0),
        "studyYearsIds": [str(x) for x in (getattr(task, "studyYearsIds", ()) or ())],
        "studyYearsLabels": str(getattr(task, "studyYearsLabels", "") or ""),
        "studyYearEntries": [],
    }


def module_target(task, module_index: int) -> dict[str, Any]:
    """
    Returns the target metadata for one module inside a task

    Args:
        task: Source task
        module_index: Module position inside the task

    Returns:
        Target dictionary for the requested module
    """
    targets = list(getattr(task, "moduleTargets", None) or [])
    if 0 <= module_index < len(targets) and isinstance(targets[module_index], dict):
        raw = targets[module_index]
        return {
            "common": bool(raw.get("common", getattr(task, "common", False))),
            "groupIndex": raw.get("groupIndex", getattr(task, "groupIndex", None)),
            "groupSpan": int(raw.get("groupSpan", getattr(task, "groupSpan", 1)) or 1),
            "numberOfStudents": int(raw.get("numberOfStudents", getattr(task, "numberOfStudents", 0)) or 0),
            "numberOfGroups": int(raw.get("numberOfGroups", getattr(task, "numberOfGroups", 0)) or 0),
            "studyYearsIds": [str(x) for x in (raw.get("studyYearsIds", getattr(task, "studyYearsIds", ())) or ())],
            "studyYearsLabels": str(raw.get("studyYearsLabels", getattr(task, "studyYearsLabels", "")) or ""),
            "studyYearEntries": list(raw.get("studyYearEntries", []) or []),
        }
    return default_module_target(task)


def target_study_year_entries(task, module_index: int, module=None) -> list[dict[str, Any]]:
    """
    Returns normalized study-year entries for one task module

    Args:
        task: Source task
        module_index: Module position inside the task
        module: Source module used for fallback values

    Returns:
        Normalized study-year entry list
    """
    target = module_target(task, module_index)
    raw_entries = list(target.get("studyYearEntries", []) or [])
    if raw_entries:
        return [
            {
                "studyYearId": str(entry.get("studyYearId") or ""),
                "studyYearLabel": str(entry.get("studyYearLabel") or ""),
                "optional": bool(entry.get("optional", getattr(task, "optional", False))),
                "pack": entry.get("pack", getattr(task, "pack", None)),
                "disciplineId": str(entry.get("disciplineId") or discipline_id(module) if module is not None else ""),
                "moduleId": str(entry.get("moduleId") or _dget(module, "id", "")),
            }
            for entry in raw_entries
        ]

    study_year_ids = [str(x) for x in (target.get("studyYearsIds") or ())]
    labels = [part.strip() for part in str(target.get("studyYearsLabels") or "").split("+") if part.strip()]
    entries: list[dict[str, Any]] = []
    for index, sy_id in enumerate(study_year_ids):
        entries.append(
            {
                "studyYearId": sy_id,
                "studyYearLabel": labels[index] if index < len(labels) else "",
                "optional": bool(is_optional(module)) if module is not None else bool(getattr(task, "optional", False)),
                "pack": _dget(module, "pack", None) if module is not None else getattr(task, "pack", None),
                "disciplineId": discipline_id(module) if module is not None else "",
                "moduleId": str(_dget(module, "id", "")) if module is not None else "",
            }
        )
    return entries


def target_semantics_for_study_year(task, module_index: int, study_year_id: str, module=None) -> dict[str, Any]:
    """
    Returns the normalized target semantics for one study year

    Args:
        task: Source task
        module_index: Module position inside the task
        study_year_id: Study-year id to resolve
        module: Source module used for fallback values

    Returns:
        Normalized study-year semantics
    """
    entries = target_study_year_entries(task, module_index, module)
    for entry in entries:
        if str(entry.get("studyYearId") or "") == str(study_year_id):
            return entry

    return {
        "studyYearId": str(study_year_id),
        "studyYearLabel": "",
        "optional": bool(is_optional(module)) if module is not None else bool(getattr(task, "optional", False)),
        "pack": _dget(module, "pack", None) if module is not None else getattr(task, "pack", None),
        "disciplineId": discipline_id(module) if module is not None else "",
        "moduleId": str(_dget(module, "id", "")) if module is not None else "",
    }


def task_has_optional_semantics(task) -> bool:
    """
    Checks whether a task carries optional semantics in any target or module

    Args:
        task: Source task

    Returns:
        True when any target or module is optional
    """
    targets = list(getattr(task, "moduleTargets", None) or [])
    for target in targets:
        for entry in list(target.get("studyYearEntries", []) or []):
            if bool(entry.get("optional", False)):
                return True

    modules = list(getattr(task, "modules", []) or [])
    return any(bool(is_optional(module)) for module in modules)


def task_primary_pack(task):
    """
    Returns the first available optional-pack value for a task

    Args:
        task: Source task

    Returns:
        First available optional-pack value, or None
    """
    targets = list(getattr(task, "moduleTargets", None) or [])
    for target in targets:
        for entry in list(target.get("studyYearEntries", []) or []):
            pack = entry.get("pack", None)
            if pack is not None:
                return pack

    modules = list(getattr(task, "modules", []) or [])
    for module in modules:
        pack = _dget(module, "pack", None)
        if pack is not None:
            return pack

    return None
