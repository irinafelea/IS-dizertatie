from uuid import UUID

from app.entities.TimetableTask import TimetableTask
from app.models.TaskDTO import TaskDTO
from helpers.task_module_target import task_has_optional_semantics, task_primary_pack


def task_to_entity(task: TaskDTO, domain_id: UUID, semester_id: UUID) -> TimetableTask:
    """
    Maps a task DTO to a timetable task entity

    Args:
        task: Task DTO
        domain_id: Domain id
        semester_id: Semester id

    Returns:
        Timetable task entity
    """
    return TimetableTask(
        module_ids=[str(m.id) for m in task.modules],
        domain_id=domain_id,
        semester_id=semester_id,
        category=task.category,
        duration_hours=task.durationHours,
        number_of_modules=task.numberOfModules,
        common=task.common,
        optional=task_has_optional_semantics(task),
        pack=task_primary_pack(task),
        group_index=task.groupIndex,
        group_span=task.groupSpan,
        number_of_students=task.numberOfStudents,
        number_of_groups=task.numberOfGroups,
        study_years_ids=[str(x) for x in task.studyYearsIds],
        study_years_labels=task.studyYearsLabels,
        module_targets=task.moduleTargets,
        pair_group_key=task.pairGroupKey,
        online=task.online,
    )
