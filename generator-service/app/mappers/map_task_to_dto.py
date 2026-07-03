from uuid import UUID

from app.entities.TimetableTask import TimetableTask
from app.models.DisciplineForModuleDTO import DisciplineForModuleDTO
from app.models.ModuleDTO import ModuleDTO
from app.models.TaskDTO import TaskDTO
from app.models.TeacherDTO import TeacherDTO


def map_task_to_dto(task: TimetableTask, modules_map: dict[str, ModuleDTO]) -> TaskDTO:
    """
    Maps a timetable task entity to a task DTO

    Args:
        task: Timetable task entity
        modules_map: Module map by id

    Returns:
        Task DTO
    """
    modules = []

    for module_id in (task.module_ids or []):
        raw: ModuleDTO = modules_map.get(str(module_id), {})
        teacher: TeacherDTO = raw.get("teacher") or {}
        discipline = raw.get("discipline") or {}

        teacher_name = " ".join(
            part
            for part in [
                teacher.get("title"),
                teacher.get("firstName"),
                teacher.get("lastName"),
            ]
            if part
        ) or None

        teacherDto = TeacherDTO(
            id=teacher.get("id"),
            title=teacher.get("title"),
            firstName=teacher.get("firstName"),
            lastName=teacher.get("lastName"),
            email=teacher.get("email"),
            phone=teacher.get("phone"),
            intern=teacher.get("intern"),
        )

        disciplineDto = DisciplineForModuleDTO(
            id=discipline.get("id"),
            degreeLevel=discipline.get("degreeLevel"),
            title=discipline.get("title"),
            acronym=discipline.get("acronym"),
            color=discipline.get("color"),
        )

        modules.append(
            ModuleDTO(
                id=UUID(str(module_id)),
                tid=UUID(str(teacher.get("id"))) if teacher.get("id") else None,
                title=raw.get("title"),
                acronym=raw.get("acronym"),
                category=raw.get("category"),
                numberOfHours=raw.get("numberOfHours"),
                typeOfDiscipline=raw.get("typeOfDiscipline"),
                completeTeacher=teacher_name,
                teacher=teacherDto,
                degreeLevel=discipline.get("degreeLevel"),
                discipline=disciplineDto,
            )
        )

    return TaskDTO(
        id=task.id,
        modules=modules,
        category=task.category,
        durationHours=task.duration_hours,
        numberOfModules=task.number_of_modules,
        common=task.common,
        groupIndex=task.group_index,
        groupSpan=task.group_span,
        numberOfStudents=task.number_of_students,
        numberOfGroups=task.number_of_groups,
        studyYearsIds=tuple(str(x) for x in (task.study_years_ids or [])),
        studyYearsLabels=task.study_years_labels,
        moduleTargets=list(task.module_targets or []) if task.module_targets else None,
        pairGroupKey=task.pair_group_key,
        online=task.online,
    )
