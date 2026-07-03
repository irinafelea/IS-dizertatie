from collections import Counter
from typing import List

from helpers.module import module_category, is_combined_course_task
from helpers.teacher import teacher_id
from app.models.TaskDTO import TaskDTO


def tasks_summary(tasks: List[TaskDTO]):
    """
    Prints a summary of task types and teacher coverage

    Args:
        tasks: Source tasks

    Returns:
        None
    """
    task_types = Counter()
    teachers = set()

    for t in tasks:
        m = t.module
        cat = module_category(m)
        is_common = len(getattr(t, "studyYearsIds", ())) > 1

        if cat == "course":
            task_types["courses"] += 1
            if is_combined_course_task(t) or is_common:
                task_types["common_courses"] += 1
            else:
                task_types["simple_courses"] += 1

        elif cat in ("laboratory", "seminar"):
            task_types["labs_seminars"] += 1
            if is_common:
                task_types["common_labs_seminars"] += 1
            else:
                task_types["simple_labs_seminars"] += 1

            if getattr(t, "pair_group_key", None):
                task_types["paired_3h_parts"] += 1

        else:
            task_types["other"] += 1

        tid = teacher_id(m)
        if tid:
            teachers.add(tid)

    print("\n=== TASK SUMMARY ===")
    print(f"Total tasks: {len(tasks)}")

    print(f"Courses: {task_types['courses']}")
    print(f"  Common courses: {task_types['common_courses']}")
    print(f"  Simple courses: {task_types['simple_courses']}")

    print(f"Labs/Seminars: {task_types['labs_seminars']}")
    print(f"  Common labs/seminars: {task_types['common_labs_seminars']}")
    print(f"  Simple labs/seminars: {task_types['simple_labs_seminars']}")

    print(f"3h paired parts: {task_types['paired_3h_parts']}")
    print(f"Other: {task_types['other']}")
    print(f"Teachers involved: {len(teachers)}")
