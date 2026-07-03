from typing import Optional

from app.models.ModuleDTO import ModuleDTO
from helpers._dget import _dget


def module_category(m: ModuleDTO) -> str:
    """
    Returns the normalized module category

    Args:
        m: Source module

    Returns:
        Lowercase module category
    """

    return str(_dget(m, "category", "") or "").lower()


def is_course(m: ModuleDTO) -> bool:
    """
    Checks whether a module should be treated as a course

    Args:
        m: Source module

    Returns:
        True when the module is course-like
    """

    cat = module_category(m)
    return (cat == "course") or (cat not in ("laboratory", "seminar"))


def is_lab_or_sem(m: ModuleDTO) -> bool:
    """
    Checks whether a module is a laboratory or seminar

    Args:
        m: Source module

    Returns:
        True when the module is a laboratory or seminar
    """

    return module_category(m) in ("laboratory", "seminar")


def module_hours(m: ModuleDTO) -> int:
    """
    Returns the weekly hour count of a module

    Args:
        m: Source module

    Returns:
        Weekly hour count
    """

    return int(_dget(m, "numberOfHours", 2) or 2)


def is_master_module(m: ModuleDTO) -> bool:
    """
    Checks whether a module belongs to a master's program

    Args:
        m: Source module

    Returns:
        True when the module belongs to a master's program
    """

    degree = _dget(m, "degreeLevel", {}) or {}
    return bool(degree) and str(degree).lower().startswith("m")


def module_degree_level(m: ModuleDTO) -> str:
    """
    Returns the normalized degree level label

    Args:
        m: Source module

    Returns:
        Degree level label
    """

    return "master" if is_master_module(m) else "bachelor"


def is_optional(m: ModuleDTO) -> bool:
    """
    Checks whether a module is optional

    Args:
        m: Source module

    Returns:
        True when the module is optional
    """

    t = str(_dget(m, "typeOfDiscipline", "mandatory") or "").lower()
    return t != "mandatory"


def module_pack(m: ModuleDTO) -> Optional[int]:
    """
    Returns the optional-pack index of a module

    Args:
        m: Source module

    Returns:
        Optional-pack index when present
    """
    pack = _dget(m, "pack", None)
    return int(pack) if pack is not None else None


def kind_tag(m: ModuleDTO) -> str:
    """
    Returns the short activity tag used in occupancy tracking

    Args:
        m: Source module

    Returns:
        "L" for laboratory or seminar modules, otherwise "C"
    """

    return "L" if is_lab_or_sem(m) else "C"


def module_code(m: ModuleDTO) -> Optional[str]:
    """
    Returns the non-empty module code when present

    Args:
        m: Source module

    Returns:
        Module code when present and non-empty
    """

    code = _dget(m, "code", None)
    if code is None:
        return None
    s = str(code).strip()
    return s if s else None


def common_key(m: ModuleDTO):
    """
    Builds the grouping key for common modules

    Args:
        m: Source module

    Returns:
        Grouping key for common modules, or None
    """
    common = bool(_dget(m, "common", False))
    code = module_code(m)

    if not common or not code:
        return None

    return (
        module_category(m),
        code,
        module_degree_level(m),
    )


def total_students(m: ModuleDTO) -> int:
    """
    Returns the student count of the module study year

    Args:
        m: Source module

    Returns:
        Study-year student count
    """

    sy = _dget(m, "studyYear", {}) or {}
    return int(_dget(sy, "numberOfStudents", 0) or 0)


def groups_count(m: ModuleDTO) -> int:
    """
    Returns the group count of the module study year

    Args:
        m: Source module

    Returns:
        Study-year group count
    """

    sy = _dget(m, "studyYear", {}) or {}
    return int(_dget(sy, "numberOfGroups", 0) or 0)


def study_year_id(m: ModuleDTO) -> str:
    """
    Returns the study-year id of a module

    Args:
        m: Source module

    Returns:
        Study-year id
    """

    sy = _dget(m, "studyYear", {}) or {}
    return str(_dget(sy, "id", "SY?"))


def study_year_acr(m: ModuleDTO) -> str:
    """
    Returns the study-year acronym of a module

    Args:
        m: Source module

    Returns:
        Study-year acronym
    """

    sy = _dget(m, "studyYear", {}) or {}
    return str(_dget(sy, "acronym", "SY?"))


def discipline_id(m: ModuleDTO) -> str:
    """
    Returns the discipline id of a module

    Args:
        m: Source module

    Returns:
        Discipline id
    """

    disc = _dget(m, "discipline", {}) or {}
    return str(_dget(disc, "id", "D?"))


def discipline_uuid(m: ModuleDTO) -> Optional[str]:
    """
    Returns the optional discipline uuid string of a module

    Args:
        m: Source module

    Returns:
        Discipline uuid string when present
    """
    disc = _dget(m, "discipline", None)
    did = _dget(disc, "id", None)
    return str(did) if did else None


def discipline_acr(m: ModuleDTO) -> str:
    """
    Returns the discipline acronym of a module

    Args:
        m: Source module

    Returns:
        Discipline acronym
    """

    disc = _dget(m, "discipline", {}) or {}
    return str(_dget(disc, "acronym", "") or _dget(m, "acronym", "") or "")


def is_combined_course_task(t) -> bool:
    """
    Checks whether a task is a combined common-course task

    Args:
        t: Source task

    Returns:
        True when the task is a combined common-course task
    """
    return str(t.id).startswith("T:COMMON:")


def is_dct_module(m: ModuleDTO) -> bool:
    """
    Checks whether a module belongs to the DCT discipline

    Args:
        m: Source module

    Returns:
        True when the module belongs to the DCT discipline
    """
    return discipline_acr(m).strip().lower() == "dct"


def task_is_roomless(task) -> bool:
    """
    Checks whether a task should be scheduled without a physical room

    Args:
        task: Source task

    Returns:
        True when the task should not use a physical room
    """
    if bool(getattr(task, "online", False)):
        return True
    modules = list(getattr(task, "modules", []) or [])
    return any(is_dct_module(module) for module in modules)


def build_show_discipline_title(m: ModuleDTO) -> str:
    """
    Builds the discipline title shown in timetable views

    Args:
        m: Source module

    Returns:
        Display title for the module
    """
    if is_course(m):
        return str(_dget(m, "title", "") or "").strip()

    disc = _dget(m, "discipline", {}) or {}
    acr = _dget(disc, "acronym", None)
    return str(acr or _dget(m, "acronym", "") or "")


def build_show_teacher(m: ModuleDTO) -> str:
    """
    Builds the teacher label shown in timetable views

    Args:
        m: Source module

    Returns:
        Display teacher label
    """
    teacher = _dget(m, "teacher", None)
    last_name = str(_dget(teacher, "lastName", "") or "").strip()
    first_name = str(_dget(teacher, "firstName", "") or "").strip()

    if is_course(m):
        if not teacher:
            return ""
        return f"{m.completeTeacher}".strip()

    if not last_name and not first_name:
        return ""

    return f"{last_name} {first_name[:1]}.".strip()
