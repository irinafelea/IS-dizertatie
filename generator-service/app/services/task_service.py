from typing import List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.mappers.map_task_to_entity import task_to_entity
from app.models.ModuleDTO import ModuleDTO
from app.models.TaskBulkUpdate import TaskBulkUpdate
from app.models.TaskUpdate import TaskUpdate
from app.entities.TimetableTask import TimetableTask
from app.external_services.module_service import fetch_modules_for_generation
from app.utils.build_modules_map import build_modules_map
from app.utils.build_tasks import build_tasks


def _sync_module_targets_with_task(task: TimetableTask) -> None:
    """
    Syncs task group values into each module target

    Args:
        task: Timetable task entity

    Returns:
        None
    """
    targets = list(task.module_targets or [])
    if not targets:
        return

    synced = []
    for raw in targets:
        target = dict(raw or {})
        target["groupIndex"] = task.group_index
        target["groupSpan"] = task.group_span
        target["numberOfStudents"] = task.number_of_students
        target["numberOfGroups"] = task.number_of_groups
        synced.append(target)

    task.module_targets = synced


def generate_and_store_tasks(
    db: Session,
    semester_id: UUID,
    domain_id: UUID,
    replace_existing: bool = True,
) -> Tuple[List[TimetableTask], dict[str, ModuleDTO]]:
    """
    Generates tasks from modules and stores them

    Args:
        db: Database session
        semester_id: Semester id
        domain_id: Domain id
        replace_existing: Whether to delete existing tasks first

    Returns:
        Saved tasks and the module map
    """
    modules = fetch_modules_for_generation(
        semester_id=semester_id,
        domain_id=domain_id,
    )
    # modules = [m for m in modules if m.get("acronym") == "BTP"]

    modules_map = build_modules_map(modules)

    generated_tasks = build_tasks(modules)

    if replace_existing:
        delete_tasks_by_semester_and_domain(
            db=db,
            semester_id=semester_id,
            domain_id=domain_id,
        )

    entities = [
        task_to_entity(task, domain_id=domain_id, semester_id=semester_id)
        for task in generated_tasks
    ]

    if not entities:
        return [], modules_map

    db.add_all(entities)
    db.commit()

    for entity in entities:
        db.refresh(entity)

    return entities, modules_map

def update_task(
    db: Session,
    task_id: UUID,
    payload: TaskUpdate,
) -> TimetableTask | None:
    """
    Updates one timetable task

    Args:
        db: Database session
        task_id: Task id
        payload: Update payload

    Returns:
        Updated task or None
    """
    task = (
        db.query(TimetableTask)
        .filter(TimetableTask.id == task_id)
        .first()
    )

    if payload.online is not None:
        task.online = payload.online

    if payload.numberOfStudents is not None:
        task.number_of_students = payload.numberOfStudents

    if payload.numberOfGroups is not None:
        task.number_of_groups = payload.numberOfGroups

    if payload.groupSpan is not None:
        task.group_span = payload.groupSpan

    if payload.groupIndex is not None:
        task.group_index = payload.groupIndex

    _sync_module_targets_with_task(task)

    db.commit()
    db.refresh(task)

    return task

def bulk_update_tasks(db: Session, request: TaskBulkUpdate) -> list[TimetableTask]:
    """
    Applies updates to multiple tasks

    Args:
        db: Database session
        request: Bulk update request

    Returns:
        Updated tasks
    """
    if not request.tasks:
        return []

    ids = [item.id for item in request.tasks]

    existing_tasks = (
        db.query(TimetableTask)
        .filter(TimetableTask.id.in_(ids))
        .all()
    )

    tasks_by_id = {task.id: task for task in existing_tasks}

    for item in request.tasks:
        task = tasks_by_id.get(item.id)
        if task is None:
            continue

        if item.online is not None:
            task.online = item.online

        if item.numberOfStudents is not None:
            task.number_of_students = item.numberOfStudents

        if item.numberOfGroups is not None:
            task.number_of_groups = item.numberOfGroups

        if item.groupSpan is not None:
            task.group_span = item.groupSpan

        if item.groupIndex is not None:
            task.group_index = item.groupIndex

        _sync_module_targets_with_task(task)

    db.commit()

    for task in existing_tasks:
        db.refresh(task)

    return existing_tasks


def delete_task_by_id(
    db: Session,
    task_id: UUID,
) -> bool:
    """
    Deletes one task by id

    Args:
        db: Database session
        task_id: Task id

    Returns:
        True if the task was deleted
    """
    task = (
        db.query(TimetableTask)
        .filter(TimetableTask.id == task_id)
        .first()
    )

    if task is None:
        return False

    db.delete(task)
    db.commit()
    return True

def delete_tasks_by_semester_and_domain(
    db: Session,
    semester_id: UUID,
    domain_id: UUID,
) -> int:
    """
    Deletes all tasks for one semester and domain

    Args:
        db: Database session
        semester_id: Semester id
        domain_id: Domain id

    Returns:
        Number of deleted rows
    """
    count = (
        db.query(TimetableTask)
        .filter(
            TimetableTask.semester_id == semester_id,
            TimetableTask.domain_id == domain_id,
        )
        .delete()
    )
    db.commit()
    return count
