from collections import defaultdict
from typing import List, Dict, Tuple

from app.models.ModuleDTO import ModuleDTO
from app.models.TaskDTO import TaskDTO
from helpers._dget import _dget
from helpers.module import (
    module_category,
    module_hours,
    total_students,
    groups_count,
    study_year_id,
    study_year_acr,
    is_optional,
    discipline_id,
    common_key,
    module_degree_level,
)
from helpers.task_module_target import task_has_optional_semantics, task_primary_pack


def split_groups_evenly(total_groups: int, module_count: int) -> List[Tuple[int, ...]]:
    """
    Splits group indexes into contiguous chunks with near-even sizes

    Args:
        total_groups: Total number of groups to distribute
        module_count: Number of task chunks to build

    Returns:
        Contiguous group-index chunks
    """
    if module_count <= 0 or total_groups <= 0:
        return []

    base = total_groups // module_count
    extra = total_groups % module_count

    chunks: List[Tuple[int, ...]] = []
    start = 0
    for i in range(module_count):
        size = base + (1 if i < extra else 0)
        end = start + size
        chunks.append(tuple(range(start, end)))
        start = end

    return chunks


def prefer_two_hour_first(pair_index: int) -> bool:
    """
    Alternates the 2h+1h ordering when building 3h tasks

    Args:
        pair_index: Pair position inside the bucket

    Returns:
        True when the 2h module should come first
    """

    return (pair_index % 2) == 0


def module_teacher_id(module: ModuleDTO) -> str:
    """
    Returns the normalized teacher id used for pairing buckets

    Args:
        module: Source module

    Returns:
        Normalized teacher id
    """
    teacher = _dget(module, "teacher", {}) or {}
    return str(_dget(teacher, "id", "NO_TEACHER"))


def build_module_target(
    module: ModuleDTO,
    *,
    common: bool,
    group_index: int | None,
    group_span: int,
    number_of_students: int,
    number_of_groups: int,
    study_year_ids: tuple[str, ...] | list[str] | None = None,
    study_year_labels: str | None = None,
    study_year_entries: list[dict] | None = None,
) -> dict:
    """
    Builds the scheduling target metadata for one module inside a task

    Args:
        module: Source module
        common: Whether the target is common
        group_index: First covered group index
        group_span: Number of covered groups
        number_of_students: Covered student count
        number_of_groups: Total group count
        study_year_ids: Target study-year ids
        study_year_labels: Target study-year labels
        study_year_entries: Explicit study-year entries

    Returns:
        Module target dictionary
    """
    return {
        "common": bool(common),
        "groupIndex": group_index,
        "groupSpan": int(group_span or 1),
        "numberOfStudents": int(number_of_students or 0),
        "numberOfGroups": int(number_of_groups or 0),
        "studyYearsIds": [str(x) for x in (study_year_ids if study_year_ids is not None else [study_year_id(module)])],
        "studyYearsLabels": str(study_year_labels if study_year_labels is not None else study_year_acr(module)),
        "studyYearEntries": list(study_year_entries or [{
            "studyYearId": study_year_id(module),
            "studyYearLabel": study_year_acr(module),
            "optional": bool(is_optional(module)),
            "pack": _dget(module, "pack", None),
            "disciplineId": discipline_id(module),
            "moduleId": str(_dget(module, "id", "M?")),
        }]),
    }


def build_study_year_entries(modules: List[ModuleDTO]) -> list[dict]:
    """
    Builds distinct study-year entries from a module list

    Args:
        modules: Source modules

    Returns:
        Distinct study-year entry dictionaries
    """
    by_sy: dict[str, dict] = {}
    for module in modules:
        sy_id = study_year_id(module)
        if sy_id in by_sy:
            continue
        by_sy[sy_id] = {
            "studyYearId": sy_id,
            "studyYearLabel": study_year_acr(module),
            "optional": bool(is_optional(module)),
            "pack": _dget(module, "pack", None),
            "disciplineId": discipline_id(module),
            "moduleId": str(_dget(module, "id", "M?")),
        }
    return [by_sy[sy_id] for sy_id in sorted(by_sy)]


def ordered_common_modules(representatives: List[ModuleDTO], all_modules: List[ModuleDTO]) -> List[ModuleDTO]:
    """
    Preserves representative modules first, then appends the remaining common modules

    Args:
        representatives: Modules that should be kept first
        all_modules: Full module bucket

    Returns:
        Ordered common modules without duplicates
    """
    ordered: List[ModuleDTO] = []
    seen: set[str] = set()

    for module in list(representatives) + list(all_modules):
        module_id = str(_dget(module, "id", "M?"))
        if module_id in seen:
            continue
        seen.add(module_id)
        ordered.append(module)

    return ordered


def simple_duration_bucket_key(module: ModuleDTO) -> Tuple:
    """
    Builds the grouping key for non-common modules by study year and discipline

    Args:
        module: Source module

    Returns:
        Grouping key for simple-module duration buckets
    """
    return (
        study_year_id(module),
        discipline_id(module),
        module_degree_level(module),
    )


def task_pair_bucket_key(task: TaskDTO) -> Tuple:
    """
    Builds the pairing bucket key used for 1h and 3h task pairing

    Args:
        task: Source task

    Returns:
        Pairing bucket key
    """
    first_module = task.modules[0]
    category = str(task.category or "")

    if category == "course":
        return (
            module_teacher_id(first_module),
            module_degree_level(first_module),
        )

    return (
        category,
        module_teacher_id(first_module),
        int(task.numberOfStudents or 0),
        str(discipline_id(first_module) or "NO_DISCIPLINE"),
        bool(task.common),
        int(task.numberOfGroups or 0),
        int(task.groupSpan or 0),
        bool(task_has_optional_semantics(task)),
        task_primary_pack(task),
    )


def task_sort_key(task: TaskDTO) -> Tuple:
    """
    Builds the stable ordering key used inside pairing buckets

    Args:
        task: Source task

    Returns:
        Stable task ordering key
    """
    if task.category == "course":
        return (
            -int(task.numberOfStudents or 0),
            str(task.studyYearsLabels or ""),
            int(task.groupIndex or 0),
            str(task.id or ""),
        )

    return (
        str(task.studyYearsLabels or ""),
        int(task.groupIndex or 0),
        -int(task.numberOfStudents or 0),
        str(task.id or ""),
    )


def sort_courses_by_students_desc(tasks: List[TaskDTO]) -> List[TaskDTO]:
    """
    Orders course tasks by student count in descending order

    Args:
        tasks: Course tasks to order

    Returns:
        Sorted course tasks
    """
    return sorted(tasks, key=lambda task: (-int(task.numberOfStudents or 0), str(task.id or "")))


def print_course_order(label: str, tasks: List[TaskDTO]) -> None:
    """
    Prints the current course ordering used during task construction

    Args:
        label: Printed bucket label
        tasks: Tasks to print

    Returns:
        None
    """
    print(f"[COURSE ORDER] {label}")
    for index, task in enumerate(tasks, start=1):
        module = task.modules[0] if task.modules else None
        title = str(_dget(module, "title", "") or "")
        teacher = str(_dget(_dget(module, "teacher", {}) or {}, "lastName", "") or "")
        print(
            f"  {index}. students={int(task.numberOfStudents or 0)} "
            f"studyYears={task.studyYearsLabels} "
            f"groups={task.groupIndex}/{task.groupSpan} "
            f"teacher={teacher} "
            f"title={title}"
        )


def extract_simple_and_common_modules(modules: List[ModuleDTO]) -> tuple[List[ModuleDTO], Dict[Tuple[str, str, str, bool], List[ModuleDTO]], List[ModuleDTO], Dict[Tuple[str, str, str, bool], List[ModuleDTO]]]:
    """
    Splits modules into simple/common and course/lab-sem buckets

    Args:
        modules: Source modules

    Returns:
        Simple courses, common courses, simple lab-sem modules, and common lab-sem buckets
    """
    common_modules: Dict[Tuple[str, str, str, bool], List[ModuleDTO]] = {}
    simple_modules: List[ModuleDTO] = []

    for m in modules:
        ck = common_key(m)
        if ck is None:
            simple_modules.append(m)
        else:
            common_modules.setdefault(ck, []).append(m)

    simple_courses: List[ModuleDTO] = []
    simple_labsem: List[ModuleDTO] = []

    common_courses: Dict[Tuple[str, str, str, bool], List[ModuleDTO]] = {}
    common_labsem: Dict[Tuple[str, str, str, bool], List[ModuleDTO]] = {}

    for m in simple_modules:
        cat = module_category(m)
        if cat == "course":
            simple_courses.append(m)
        elif cat in ("laboratory", "seminar"):
            simple_labsem.append(m)

    for key, items in common_modules.items():
        if not items:
            continue

        cat = module_category(items[0])

        if cat == "course":
            common_courses[key] = items
        elif cat in ("laboratory", "seminar"):
            common_labsem[key] = items

    return simple_courses, common_courses, simple_labsem, common_labsem


def split_simple_modules_by_duration(modules: List[ModuleDTO]) -> tuple[List[ModuleDTO], List[ModuleDTO], Dict[Tuple, List[ModuleDTO]]]:
    """
    Splits simple modules into 1h, 2h, and mixed 3h buckets

    Args:
        modules: Simple modules to split

    Returns:
      - one_hour_modules: modules from buckets that contain only 1h modules
      - two_hour_modules: modules from buckets that contain only 2h modules
      - three_hour_buckets: buckets that contain both 1h and 2h modules,
        grouped by (study_year_id, discipline_id)
    """
    grouped: Dict[Tuple, List[ModuleDTO]] = {}
    for m in modules:
        key = simple_duration_bucket_key(m)
        grouped.setdefault(key, []).append(m)

    one_hour_modules: List[ModuleDTO] = []
    two_hour_modules: List[ModuleDTO] = []
    three_hour_buckets: Dict[Tuple, List[ModuleDTO]] = {}

    for key, items in grouped.items():
        has_1h = any(module_hours(m) == 1 for m in items)
        has_2h = any(module_hours(m) == 2 for m in items)

        if has_1h and has_2h:
            three_hour_buckets[key] = items
        elif has_1h:
            one_hour_modules.extend(items)
        elif has_2h:
            two_hour_modules.extend(items)

    return one_hour_modules, two_hour_modules, three_hour_buckets


def split_common_modules_by_duration(buckets: Dict[Tuple[str, str, str, bool], List[ModuleDTO]]) -> tuple[Dict[Tuple[str, str, str, bool], List[ModuleDTO]], Dict[Tuple[str, str, str, bool], List[ModuleDTO]], Dict[Tuple[str, str, str, bool], List[ModuleDTO]]]:
    """
    Splits common-module buckets into 1h, 2h, and mixed 3h buckets

    Args:
        buckets: Common-module buckets

    Returns:
      - one_hour_buckets: buckets that contain only 1h modules
      - two_hour_buckets: buckets that contain only 2h modules
      - three_hour_buckets: buckets that contain both 1h and 2h modules
    """

    one_hour_buckets: Dict[Tuple[str, str, str, bool], List[ModuleDTO]] = {}
    two_hour_buckets: Dict[Tuple[str, str, str, bool], List[ModuleDTO]] = {}
    three_hour_buckets: Dict[Tuple[str, str, str, bool], List[ModuleDTO]] = {}

    for key, items in buckets.items():
        has_1h = any(module_hours(m) == 1 for m in items)
        has_2h = any(module_hours(m) == 2 for m in items)

        if has_1h and has_2h:
            three_hour_buckets[key] = items
        elif has_1h:
            one_hour_buckets[key] = items
        elif has_2h:
            two_hour_buckets[key] = items

    return one_hour_buckets, two_hour_buckets, three_hour_buckets


def build_simple_three_hour_tasks(buckets: Dict[Tuple, List[ModuleDTO]]) -> List[TaskDTO]:
    """
    Builds 3h tasks for non-common modules by pairing one 1h and one 2h module

    Args:
        buckets: Mixed-duration simple-module buckets

    Returns:
        Built 3h tasks
    """
    tasks: List[TaskDTO] = []

    for _, items in buckets.items():
        if not items:
            continue

        first = items[0]
        sy_id = study_year_id(first)

        one_hour_modules = [m for m in items if module_hours(m) == 1]
        two_hour_modules = [m for m in items if module_hours(m) == 2]

        if not one_hour_modules or not two_hour_modules:
            continue

        one_hour_modules = sorted(one_hour_modules, key=lambda x: str(_dget(x, "id", "")))
        two_hour_modules = sorted(two_hour_modules, key=lambda x: str(_dget(x, "id", "")))

        category = "course" if module_category(first) == "course" else "labsem"
        optional = is_optional(first)

        sy_label = study_year_acr(first)
        total_group_count = max(1, int(groups_count(first) or 1))
        total_student_count = int(total_students(first) or 0)

        per_group = (total_student_count + total_group_count - 1) // total_group_count if total_student_count > 0 else 0
        if optional:
            per_group = max(1, per_group // 2)

        pair_count = min(len(one_hour_modules), len(two_hour_modules))
        group_spans = split_groups_evenly(total_group_count, pair_count)

        for i in range(pair_count):
            groups_for_task = group_spans[i] if i < len(group_spans) else ()
            if not groups_for_task:
                continue

            one_h = one_hour_modules[i]
            two_h = two_hour_modules[i]
            if prefer_two_hour_first(i):
                m1, m2 = two_h, one_h
            else:
                m1, m2 = one_h, two_h

            id1 = str(_dget(m1, "id", "M?"))
            id2 = str(_dget(m2, "id", "M?"))
            main_group = groups_for_task[0]

            students = int((per_group * len(groups_for_task)) or 0)
            numberOfStudentsNotCourse = students if students <= 30 and category != "course" else 30
            numberOfStudentsCourse = students if students <= 270 and category == "course" else 270

            tasks.append(
                TaskDTO(
                    id=f"T:3H:{id1}:{id2}:G{main_group}",
                    modules=[m1, m2],
                    category=category,
                    durationHours=3,
                    numberOfModules=2,
                    common=False,
                    groupIndex=main_group,
                    groupSpan=len(groups_for_task),
                    numberOfStudents=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                    numberOfGroups=total_group_count,
                    studyYearsIds=(sy_id,),
                    studyYearsLabels=sy_label,
                    moduleTargets=[
                        build_module_target(
                            m1,
                            common=False,
                            group_index=main_group,
                            group_span=len(groups_for_task),
                            number_of_students=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                            number_of_groups=total_group_count,
                        ),
                        build_module_target(
                            m2,
                            common=False,
                            group_index=main_group,
                            group_span=len(groups_for_task),
                            number_of_students=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                            number_of_groups=total_group_count,
                        ),
                    ],
                    pairGroupKey=None,
                    online=False,
                )
            )

    return tasks


def build_common_three_hour_tasks(buckets: Dict[Tuple[str, str, str, bool], List[ModuleDTO]]) -> List[TaskDTO]:
    """
    Builds 3h tasks for common-module buckets

    Args:
        buckets: Mixed-duration common-module buckets

    Returns:
        Built common 3h tasks
    """
    tasks: List[TaskDTO] = []

    for _, items in buckets.items():
        if not items:
            continue

        first = items[0]
        study_year_entries = build_study_year_entries(items)

        one_hour_modules = [m for m in items if module_hours(m) == 1]
        two_hour_modules = [m for m in items if module_hours(m) == 2]

        if not one_hour_modules or not two_hour_modules:
            continue

        one_hour_modules = sorted(one_hour_modules, key=lambda x: str(_dget(x, "id", "")))
        two_hour_modules = sorted(two_hour_modules, key=lambda x: str(_dget(x, "id", "")))

        category = "course" if module_category(first) == "course" else "labsem"
        optional = is_optional(first)
        studyYearsIds = tuple(sorted({study_year_id(m) for m in items}))
        studyYearsLabels = "+".join(sorted({study_year_acr(m) for m in items}))

        pairs_by_sy: Dict[str, set[str]] = defaultdict(set)

        for m in items:
            if module_hours(m) != 2:
                continue

            sy_id = study_year_id(m)
            mid = str(_dget(m, "id", "M?"))
            pairs_by_sy[sy_id].add(mid)

        pair_count = max(len(moduleIds) for moduleIds in pairs_by_sy.values())

        total_student_count = sum(int(total_students(m) or 0) for m in items)

        per_group = (total_student_count + pair_count - 1) // pair_count if total_student_count > 0 else 0
        if optional:
            per_group = max(1, per_group // 2)

        group_spans = split_groups_evenly(pair_count, pair_count)

        for i in range(pair_count):
            groups_for_task = group_spans[i] if i < len(group_spans) else ()
            if not groups_for_task:
                continue

            one_h = one_hour_modules[i]
            two_h = two_hour_modules[i]
            if prefer_two_hour_first(i):
                m1, m2 = two_h, one_h
            else:
                m1, m2 = one_h, two_h

            id1 = str(_dget(m1, "id", "M?"))
            id2 = str(_dget(m2, "id", "M?"))
            main_group = groups_for_task[0]

            students = int((per_group * len(groups_for_task)) or 0)
            numberOfStudentsNotCourse = students if students <= 30 and category != "course" else 30
            numberOfStudentsCourse = students if students <= 270 and category == "course" else 270

            tasks.append(
                TaskDTO(
                    id=f"T:COMMON:3H:{id1}:{id2}:G{main_group}",
                    modules=ordered_common_modules([m1, m2], items),
                    category=category,
                    durationHours=3,
                    numberOfModules=2,
                    common=True,
                    groupIndex=main_group,
                    groupSpan=len(groups_for_task),
                    numberOfStudents=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                    numberOfGroups=pair_count,
                    studyYearsIds=studyYearsIds,
                    studyYearsLabels=studyYearsLabels,
                    moduleTargets=[
                        build_module_target(
                            m1,
                            common=True,
                            group_index=main_group,
                            group_span=len(groups_for_task),
                            number_of_students=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                            number_of_groups=pair_count,
                            study_year_ids=studyYearsIds,
                            study_year_labels=studyYearsLabels,
                            study_year_entries=study_year_entries,
                        ),
                        build_module_target(
                            m2,
                            common=True,
                            group_index=main_group,
                            group_span=len(groups_for_task),
                            number_of_students=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                            number_of_groups=pair_count,
                            study_year_ids=studyYearsIds,
                            study_year_labels=studyYearsLabels,
                            study_year_entries=study_year_entries,
                        ),
                    ],
                    pairGroupKey=None,
                    online=False,
                )
            )

    return tasks


def build_three_hour_pair_key(t1: TaskDTO, t2: TaskDTO) -> str:
    """
    Builds the pair key used by paired 3h tasks

    Args:
        t1: First task
        t2: Second task

    Returns:
        Pair-group key
    """
    teacher_id = str(t1.teacher_id or "NO_TEACHER")
    discipline_id = str(t1.discipline_id or "NO_DISCIPLINE")

    m1 = "+".join(sorted(str(m.id) for m in t1.modules))
    m2 = "+".join(sorted(str(m.id) for m in t2.modules))

    module_a, module_b = sorted([m1, m2])

    g1 = int(t1.groupIndex)
    g2 = int(t2.groupIndex)
    group_a, group_b = sorted([g1, g2])

    return f"PAIR:{teacher_id}+{discipline_id}+{module_a}+{module_b}:{group_a}+{group_b}"


def pair_three_hour_tasks(tasks: List[TaskDTO]) -> List[TaskDTO]:
    """
    Pairs compatible 3h tasks inside their pairing buckets

    Args:
        tasks: Candidate 3h tasks

    Returns:
        Paired and untouched 3h tasks
    """

    groups: Dict[Tuple, List[TaskDTO]] = defaultdict(list)

    for task in tasks:
        if task.durationHours != 3:
            continue
        if task.groupIndex is None:
            continue

        groups[task_pair_bucket_key(task)].append(task)

    paired_task_ids = set()
    result: List[TaskDTO] = []

    untouched_tasks = [t for t in tasks if t.durationHours != 3 or t.groupIndex is None]

    def can_pair(bucket_task_a: TaskDTO, bucket_task_b: TaskDTO) -> bool:
        if bucket_task_a.category == "course":
            return True

        return bucket_task_a.groupIndex != bucket_task_b.groupIndex

    for bucket_key, bucket_tasks in groups.items():
        if bucket_tasks and bucket_tasks[0].category == "course":
            teacher_id = str(bucket_key[0] or "NO_TEACHER")
            did = "MULTI_DISCIPLINE"
        else:
            teacher_id = str(bucket_key[1] or "NO_TEACHER")
            did = str(bucket_key[3] if len(bucket_key) > 3 else discipline_id(bucket_tasks[0].modules[0]) or "NO_DISCIPLINE")
        bucket_tasks.sort(key=task_sort_key)

        i = 0
        while i < len(bucket_tasks):
            t1 = bucket_tasks[i]

            if t1.id in paired_task_ids:
                i += 1
                continue

            partner_index = None

            for j in range(i+1, len(bucket_tasks)):
                t2 = bucket_tasks[j]

                if t2.id in paired_task_ids:
                    continue

                if not can_pair(t1, t2):
                    continue

                partner_index = j
                break

            if partner_index is None:
                result.append(t1)
                i += 1
                continue

            t2 = bucket_tasks[partner_index]

            modules_1 = "+".join(sorted(str(m.id) for m in t1.modules))
            modules_2 = "+".join(sorted(str(m.id) for m in t2.modules))

            modules_part_1, modules_part_2 = sorted([modules_1, modules_2])

            g1, g2 = sorted([int(t1.groupIndex), int(t2.groupIndex)])

            pair_key = (
                f"PAIR:{teacher_id}+{did}+"
                f"{modules_part_1}+{modules_part_2}:"
                f"{g1}+{g2}"
            )

            result.append(
                TaskDTO(
                    id=t1.id,
                    modules=t1.modules,
                    category=t1.category,
                    durationHours=t1.durationHours,
                    numberOfModules=t1.numberOfModules,
                    common=t1.common,
                    groupIndex=t1.groupIndex,
                    groupSpan=t1.groupSpan,
                    numberOfStudents=t1.numberOfStudents,
                    numberOfGroups=t1.numberOfGroups,
                    studyYearsIds=t1.studyYearsIds,
                    studyYearsLabels=t1.studyYearsLabels,
                    moduleTargets=t1.moduleTargets,
                    pairGroupKey=pair_key,
                    online=t1.online,
                )
            )

            result.append(
                TaskDTO(
                    id=t2.id,
                    modules=t2.modules,
                    category=t2.category,
                    durationHours=t2.durationHours,
                    numberOfModules=t2.numberOfModules,
                    common=t2.common,
                    groupIndex=t2.groupIndex,
                    groupSpan=t2.groupSpan,
                    numberOfStudents=t2.numberOfStudents,
                    numberOfGroups=t2.numberOfGroups,
                    studyYearsIds=t2.studyYearsIds,
                    studyYearsLabels=t2.studyYearsLabels,
                    moduleTargets=t2.moduleTargets,
                    pairGroupKey=pair_key,
                    online=t2.online,
                )
            )

            paired_task_ids.add(t1.id)
            paired_task_ids.add(t2.id)
            i += 1

    return untouched_tasks + result


def build_simple_one_hour_tasks(modules: List[ModuleDTO]) -> List[TaskDTO]:
    """
    Builds 1h tasks for non-common modules

    Args:
        modules: Simple 1h modules

    Returns:
        Built 1h tasks
    """
    tasks: List[TaskDTO] = []

    grouped: Dict[Tuple, List[ModuleDTO]] = defaultdict(list)
    for m in modules:
        key = simple_duration_bucket_key(m)
        grouped[key].append(m)

    for _, items in grouped.items():
        if not items:
            continue

        items = sorted(items, key=lambda x: str(_dget(x, "id", "")))
        first = items[0]
        sy_id = study_year_id(first)

        category = "course" if module_category(first) == "course" else "labsem"
        optional = is_optional(first)
        sy_label = study_year_acr(first)
        total_group_count = max(1, int(groups_count(first) or 1))
        total_student_count = int(total_students(first) or 0)

        per_group = (total_student_count + total_group_count - 1) // total_group_count if total_student_count > 0 else 0
        if optional:
            per_group = max(1, per_group // 2)

        group_spans = split_groups_evenly(total_group_count, len(items))

        for i, m in enumerate(items):
            groups_for_task = group_spans[i] if i < len(group_spans) else ()
            if not groups_for_task:
                continue

            mid = str(_dget(m, "id", "M?"))
            main_group = groups_for_task[0]

            students = int((per_group * len(groups_for_task)) or 0)
            numberOfStudentsNotCourse = students if students <= 30 and category != "course" else 30
            numberOfStudentsCourse = students if students <= 270 and category == "course" else 270

            tasks.append(
                TaskDTO(
                    id=f"T:1H:{mid}:G{main_group}",
                    modules=[m],
                    category=category,
                    durationHours=1,
                    numberOfModules=1,
                    common=False,
                    groupIndex=main_group,
                    groupSpan=len(groups_for_task),
                    numberOfStudents=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                    numberOfGroups=total_group_count,
                    studyYearsIds=(sy_id,),
                    studyYearsLabels=sy_label,
                    moduleTargets=[
                        build_module_target(
                            m,
                            common=False,
                            group_index=main_group,
                            group_span=len(groups_for_task),
                            number_of_students=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                            number_of_groups=total_group_count,
                        )
                    ],
                    pairGroupKey=None,
                    online=False,
                )
            )

    return tasks


def build_common_one_hour_tasks(buckets: Dict[Tuple[str, str, str, bool], List[ModuleDTO]]) -> List[TaskDTO]:
    """
    Builds 1h tasks for common-module buckets

    Args:
        buckets: Common 1h module buckets

    Returns:
        Built common 1h tasks
    """
    tasks: List[TaskDTO] = []

    for _, items in buckets.items():
        if not items:
            continue

        items = sorted(items, key=lambda x: str(_dget(x, "id", "")))
        first = items[0]
        study_year_entries = build_study_year_entries(items)

        category = "course" if module_category(first) == "course" else "labsem"
        optional = is_optional(first)
        studyYearsIds = tuple(sorted({study_year_id(m) for m in items}))
        studyYearsLabels = "+".join(sorted({study_year_acr(m) for m in items}))

        total_group_count = max(
                len({str(_dget(m, "id", "M?")) for m in items if study_year_id(m) == sy})
                for sy in studyYearsIds
        )

        total_student_count = sum(int(total_students(m) or 0) for m in items)

        per_group = (total_student_count + total_group_count - 1) // total_group_count if total_student_count > 0 else 0
        if optional:
            per_group = max(1, per_group // 2)

        group_spans = split_groups_evenly(total_group_count, len(items))

        for i, m in enumerate(items):
            groups_for_task = group_spans[i] if i < len(group_spans) else ()
            if not groups_for_task:
                continue

            mid = str(_dget(m, "id", "M?"))
            main_group = groups_for_task[0]

            students = int((per_group * len(groups_for_task)) or 0)
            numberOfStudentsNotCourse = students if students <= 30 and category != "course" else 30
            numberOfStudentsCourse = students if students <= 270 and category == "course" else 270

            tasks.append(
                TaskDTO(
                    id=f"T:COMMON:1H:{mid}:G{main_group}",
                    modules=ordered_common_modules([m], items),
                    category=category,
                    durationHours=1,
                    numberOfModules=1,
                    common=True,
                    groupIndex=main_group,
                    groupSpan=len(groups_for_task),
                    numberOfStudents=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                    numberOfGroups=total_group_count,
                    studyYearsIds=studyYearsIds,
                    studyYearsLabels=studyYearsLabels,
                    moduleTargets=[
                        build_module_target(
                            m,
                            common=True,
                            group_index=main_group,
                            group_span=len(groups_for_task),
                            number_of_students=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                            number_of_groups=total_group_count,
                            study_year_ids=studyYearsIds,
                            study_year_labels=studyYearsLabels,
                            study_year_entries=study_year_entries,
                        )
                    ],
                    pairGroupKey=None,
                    online=False,
                )
            )

    return tasks


def module_target(task: TaskDTO) -> dict:
    """
    Builds a task-level target snapshot for merged paired tasks

    Args:
        task: Source task

    Returns:
        Task-level target dictionary
    """
    return {
        "common": task.common,
        "groupIndex": task.groupIndex,
        "groupSpan": task.groupSpan,
        "numberOfStudents": task.numberOfStudents,
        "numberOfGroups": task.numberOfGroups,
        "studyYearsIds": [str(x) for x in (task.studyYearsIds or ())],
        "studyYearsLabels": task.studyYearsLabels,
    }


def merge_paired_tasks(t1: TaskDTO, t2: TaskDTO, pair_key: str) -> TaskDTO:
    """
    Merges two paired 1h tasks into a single paired task

    Args:
        t1: First task
        t2: Second task
        pair_key: Pair-group key

    Returns:
        Merged paired task
    """
    merged_study_year_ids = tuple(
        sorted({str(x) for x in (t1.studyYearsIds or ())} | {str(x) for x in (t2.studyYearsIds or ())})
    )
    merged_labels = "+".join(
        sorted(
            {
                part.strip()
                for part in (str(t1.studyYearsLabels or "") + "+" + str(t2.studyYearsLabels or "")).split("+")
                if part.strip()
            }
        )
    )

    return TaskDTO(
        id=f"T:PAIR:1H:{pair_key}",
        modules=ordered_common_modules([t1.modules[0], t2.modules[0]], list(t1.modules) + list(t2.modules)),
        category=t1.category,
        durationHours=1,
        numberOfModules=2,
        common=t1.common or t2.common,
        groupIndex=t1.groupIndex,
        groupSpan=t1.groupSpan,
        numberOfStudents=max(int(t1.numberOfStudents or 0), int(t2.numberOfStudents or 0)),
        numberOfGroups=max(int(t1.numberOfGroups or 0), int(t2.numberOfGroups or 0)),
        studyYearsIds=merged_study_year_ids,
        studyYearsLabels=merged_labels,
        moduleTargets=[module_target(t1), module_target(t2)],
        pairGroupKey=pair_key,
        online=t1.online or t2.online,
    )


def pair_one_hour_tasks(tasks: List[TaskDTO]) -> List[TaskDTO]:
    """
    Pairs compatible 1h tasks inside their pairing buckets

    Args:
        tasks: Candidate 1h tasks

    Returns:
        Paired and untouched 1h tasks
    """
    groups: Dict[Tuple, List[TaskDTO]] = defaultdict(list)

    for task in tasks:
        if task.durationHours != 1:
            continue
        if task.groupIndex is None:
            continue

        groups[task_pair_bucket_key(task)].append(task)

    untouched_tasks = [t for t in tasks if t.durationHours != 1 or t.groupIndex is None]
    result: List[TaskDTO] = []

    for bucket_key, bucket_tasks in groups.items():
        if bucket_tasks and bucket_tasks[0].category == "course":
            teacher_id = str(bucket_key[0] or "NO_TEACHER")
            did = "MULTI_DISCIPLINE"
        else:
            teacher_id = str(bucket_key[1] or "NO_TEACHER")
            did = str(bucket_key[3] if len(bucket_key) > 3 else discipline_id(bucket_tasks[0].modules[0]) or "NO_DISCIPLINE")
        bucket_tasks = sorted(bucket_tasks, key=task_sort_key)
        used: set[str] = set()

        if bucket_tasks and bucket_tasks[0].category == "course":
            i = 0
            while i < len(bucket_tasks):
                t1 = bucket_tasks[i]
                if t1.id in used:
                    i += 1
                    continue

                partner_index = None
                for j in range(i + 1, len(bucket_tasks)):
                    t2 = bucket_tasks[j]
                    if t2.id in used:
                        continue
                    partner_index = j
                    break

                if partner_index is None:
                    result.append(t1)
                    used.add(t1.id)
                    i += 1
                    continue

                t2 = bucket_tasks[partner_index]

                modules_1 = "+".join(sorted(str(m.id) for m in t1.modules))
                modules_2 = "+".join(sorted(str(m.id) for m in t2.modules))
                modules_part_1, modules_part_2 = sorted([modules_1, modules_2])

                g1, g2 = sorted([int(t1.groupIndex), int(t2.groupIndex)])

                pair_key = (
                    f"PAIR:{teacher_id}+{did}+"
                    f"{modules_part_1}+{modules_part_2}:"
                    f"{g1}+{g2}"
                )

                result.append(merge_paired_tasks(t1, t2, pair_key))
                used.add(t1.id)
                used.add(t2.id)
                i += 1

            continue

        # Pair within the same study year first
        for i in range(len(bucket_tasks)):
            t1 = bucket_tasks[i]
            if t1.id in used:
                continue

            partner_index = None
            for j in range(i + 1, len(bucket_tasks)):
                t2 = bucket_tasks[j]
                if t2.id in used:
                    continue

                if t1.studyYearsLabels != t2.studyYearsLabels:
                    continue

                if t1.category != "course" and t1.groupIndex == t2.groupIndex:
                    continue

                partner_index = j
                break

            if partner_index is None:
                continue

            t2 = bucket_tasks[partner_index]

            modules_1 = "+".join(sorted(str(m.id) for m in t1.modules))
            modules_2 = "+".join(sorted(str(m.id) for m in t2.modules))
            modules_part_1, modules_part_2 = sorted([modules_1, modules_2])

            g1, g2 = sorted([int(t1.groupIndex), int(t2.groupIndex)])

            pair_key = (
                f"PAIR:{teacher_id}+{did}+"
                f"{modules_part_1}+{modules_part_2}:"
                f"{g1}+{g2}"
            )

            result.append(merge_paired_tasks(t1, t2, pair_key))
            used.add(t1.id)
            used.add(t2.id)

        # Then pair across study years if needed
        remaining = [t for t in bucket_tasks if t.id not in used]

        for i in range(len(remaining)):
            t1 = remaining[i]
            if t1.id in used:
                continue

            partner_index = None
            for j in range(i + 1, len(remaining)):
                t2 = remaining[j]
                if t2.id in used:
                    continue

                if t1.studyYearsLabels == t2.studyYearsLabels:
                    continue
                if t1.groupIndex == t2.groupIndex:
                    continue

                partner_index = j
                break

            if partner_index is None:
                result.append(t1)
                used.add(t1.id)
                continue

            t2 = remaining[partner_index]

            modules_1 = "+".join(sorted(str(m.id) for m in t1.modules))
            modules_2 = "+".join(sorted(str(m.id) for m in t2.modules))
            modules_part_1, modules_part_2 = sorted([modules_1, modules_2])

            g1, g2 = sorted([int(t1.groupIndex), int(t2.groupIndex)])

            pair_key = (
                f"PAIR:{teacher_id}+{did}+"
                f"{modules_part_1}+{modules_part_2}:"
                f"{g1}+{g2}"
            )

            result.append(merge_paired_tasks(t1, t2, pair_key))
            used.add(t1.id)
            used.add(t2.id)

    return untouched_tasks + result


def build_simple_two_hour_tasks(modules: List[ModuleDTO]) -> List[TaskDTO]:
    """
    Builds 2h tasks for non-common modules

    Args:
        modules: Simple 2h modules

    Returns:
        Built 2h tasks
    """
    tasks: List[TaskDTO] = []

    grouped: Dict[Tuple, List[ModuleDTO]] = defaultdict(list)
    for m in modules:
        key = simple_duration_bucket_key(m)
        grouped[key].append(m)

    for _, items in grouped.items():
        if not items:
            continue

        items = sorted(items, key=lambda x: str(_dget(x, "id", "")))
        first = items[0]
        sy_id = study_year_id(first)

        category = "course" if module_category(first) == "course" else "labsem"
        optional = is_optional(first)
        sy_label = study_year_acr(first)
        total_group_count = max(1, int(groups_count(first) or 1))
        total_student_count = int(total_students(first) or 0)

        per_group = (total_student_count + total_group_count - 1) // total_group_count if total_student_count > 0 else 0
        if optional:
            per_group = max(1, per_group // 2)

        group_spans = split_groups_evenly(total_group_count, len(items))

        for i, m in enumerate(items):
            groups_for_task = group_spans[i]
            if not groups_for_task:
                continue
            mid = str(_dget(m, "id", "M?"))
            main_group = groups_for_task[0]

            students = int((per_group * len(groups_for_task)) or 0)
            numberOfStudentsNotCourse = students if students <= 30 and category != "course" else 30
            numberOfStudentsCourse = students if students <= 270 and category == "course" else 270

            tasks.append(
                TaskDTO(
                    id=f"T:2H:{mid}:G{main_group}",
                    modules=[m],
                    category=category,
                    durationHours=2,
                    numberOfModules=1,
                    common=False,
                    groupIndex=main_group,
                    groupSpan=len(groups_for_task),
                    numberOfStudents=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                    numberOfGroups=total_group_count,
                    studyYearsIds=(sy_id,),
                    studyYearsLabels=sy_label,
                    moduleTargets=[
                        build_module_target(
                            m,
                            common=False,
                            group_index=main_group,
                            group_span=len(groups_for_task),
                            number_of_students=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                            number_of_groups=total_group_count,
                        )
                    ],
                    pairGroupKey=None,
                    online=False,
                )
            )

    return tasks


def build_common_two_hour_tasks(buckets: Dict[Tuple[str, str, str, bool], List[ModuleDTO]]) -> List[TaskDTO]:
    """
    Builds 2h tasks for common-module buckets

    Args:
        buckets: Common 2h module buckets

    Returns:
        Built common 2h tasks
    """
    tasks: List[TaskDTO] = []

    for _, items in buckets.items():
        if not items:
            continue

        items = sorted(items, key=lambda x: str(_dget(x, "id", "")))
        first = items[0]
        study_year_entries = build_study_year_entries(items)

        category = "course" if module_category(first) == "course" else "labsem"
        optional = is_optional(first)
        studyYearsIds = tuple(sorted({study_year_id(m) for m in items}))
        studyYearsLabels = "+".join(sorted({study_year_acr(m) for m in items}))

        total_group_count = max(
            len({str(_dget(m, "id", "M?")) for m in items if study_year_id(m) == sy})
            for sy in studyYearsIds
        )

        total_student_count = sum(int(total_students(m) or 0) for m in items)

        per_group = (total_student_count + total_group_count - 1) // total_group_count if total_student_count > 0 else 0
        if optional:
            per_group = max(1, per_group // 2)

        group_spans = split_groups_evenly(total_group_count, len(items))

        for i, m in enumerate(items):
            groups_for_task = group_spans[i] if i < len(group_spans) else ()
            if not groups_for_task:
                continue

            mid = str(_dget(m, "id", "M?"))
            main_group = groups_for_task[0]

            students = int((per_group * len(groups_for_task)) or 0)
            numberOfStudentsNotCourse = students if students <= 30 and category != "course" else 30
            numberOfStudentsCourse = students if students <= 270 and category == "course" else 270

            tasks.append(
                TaskDTO(
                    id=f"T:COMMON:2H:{mid}:G{main_group}",
                    modules=ordered_common_modules([m], items),
                    category=category,
                    durationHours=2,
                    numberOfModules=1,
                    common=True,
                    groupIndex=main_group,
                    groupSpan=len(groups_for_task),
                    numberOfStudents=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                    numberOfGroups=total_group_count,
                    studyYearsIds=studyYearsIds,
                    studyYearsLabels=studyYearsLabels,
                    moduleTargets=[
                        build_module_target(
                            m,
                            common=True,
                            group_index=main_group,
                            group_span=len(groups_for_task),
                            number_of_students=numberOfStudentsNotCourse if category != "course" else numberOfStudentsCourse,
                            number_of_groups=total_group_count,
                            study_year_ids=studyYearsIds,
                            study_year_labels=studyYearsLabels,
                            study_year_entries=study_year_entries,
                        )
                    ],
                    pairGroupKey=None,
                    online=False,
                )
            )

    return tasks


def build_tasks(modules: List[ModuleDTO]) -> List[TaskDTO]:
    """
    Builds the final schedulable task list from raw modules

    Args:
        modules: Source modules

    Returns:
        Final schedulable tasks
    """
    tasks: List[TaskDTO] = []

    simple_courses, common_courses, simple_labsem, common_labsem = extract_simple_and_common_modules(modules)

    simple_courses_1h, simple_courses_2h, simple_courses_3h = split_simple_modules_by_duration(simple_courses)
    simple_labsem_1h, simple_labsem_2h, simple_labsem_3h = split_simple_modules_by_duration(simple_labsem)

    common_courses_1h, common_courses_2h, common_courses_3h = split_common_modules_by_duration(common_courses)
    common_labsem_1h, common_labsem_2h, common_labsem_3h = split_common_modules_by_duration(common_labsem)

    simple_three_hour_courses = build_simple_three_hour_tasks(simple_courses_3h)
    simple_three_hour_labsem = build_simple_three_hour_tasks(simple_labsem_3h)
    final_simple_three_hour_courses = pair_three_hour_tasks(simple_three_hour_courses)
    final_simple_three_hour_labsem = pair_three_hour_tasks(simple_three_hour_labsem)

    common_three_hour_courses = build_common_three_hour_tasks(common_courses_3h)
    common_three_hour_labsem = build_common_three_hour_tasks(common_labsem_3h)
    final_common_three_hour_courses = pair_three_hour_tasks(common_three_hour_courses)
    final_common_three_hour_labsem = pair_three_hour_tasks(common_three_hour_labsem)

    simple_one_hour_courses = build_simple_one_hour_tasks(simple_courses_1h)
    simple_one_hour_labsem = build_simple_one_hour_tasks(simple_labsem_1h)
    common_one_hour_courses = build_common_one_hour_tasks(common_courses_1h)
    common_one_hour_labsem = build_common_one_hour_tasks(common_labsem_1h)

    one_hour_courses = simple_one_hour_courses + common_one_hour_courses
    one_hour_labsem = simple_one_hour_labsem + common_one_hour_labsem

    final_one_hour_courses = pair_one_hour_tasks(one_hour_courses)
    final_one_hour_labsem = pair_one_hour_tasks(one_hour_labsem)

    final_simple_two_hour_courses = build_simple_two_hour_tasks(simple_courses_2h)
    final_simple_two_hour_labsem = build_simple_two_hour_tasks(simple_labsem_2h)

    final_common_two_hour_courses = build_common_two_hour_tasks(common_courses_2h)
    final_common_two_hour_labsem = build_common_two_hour_tasks(common_labsem_2h)

    final_simple_three_hour_courses = sort_courses_by_students_desc(final_simple_three_hour_courses)
    final_common_three_hour_courses = sort_courses_by_students_desc(final_common_three_hour_courses)
    final_one_hour_courses = sort_courses_by_students_desc(final_one_hour_courses)
    final_simple_two_hour_courses = sort_courses_by_students_desc(final_simple_two_hour_courses)
    final_common_two_hour_courses = sort_courses_by_students_desc(final_common_two_hour_courses)

    print_course_order("simple_3h", final_simple_three_hour_courses)
    print_course_order("common_3h", final_common_three_hour_courses)
    print_course_order("simple_1h", final_one_hour_courses)
    print_course_order("simple_2h", final_simple_two_hour_courses)
    print_course_order("common_2h", final_common_two_hour_courses)

    tasks.extend(final_simple_three_hour_courses)
    tasks.extend(final_simple_three_hour_labsem)
    tasks.extend(final_common_three_hour_courses)
    tasks.extend(final_common_three_hour_labsem)
    tasks.extend(final_one_hour_courses)
    tasks.extend(final_one_hour_labsem)
    tasks.extend(final_simple_two_hour_courses)
    tasks.extend(final_simple_two_hour_labsem)
    tasks.extend(final_common_two_hour_courses)
    tasks.extend(final_common_two_hour_labsem)

    return tasks
