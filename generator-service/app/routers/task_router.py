from http.client import HTTPException
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.mappers.map_task_to_dto import map_task_to_dto
from app.models.TaskBulkUpdate import TaskBulkUpdate
from app.models.TaskDTO import TaskDTO
from app.models.TaskUpdate import TaskUpdate
from app.entities.TimetableTask import TimetableTask
from app.external_services.module_service import fetch_modules_for_generation
from app.services.task_service import generate_and_store_tasks, update_task, bulk_update_tasks, delete_task_by_id
from app.utils.build_modules_map import build_modules_map

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{semester_id}/{domain_id}", response_model=list[TaskDTO])
def get_tasks_endpoint(
    semester_id: UUID,
    domain_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Returns tasks for one semester and domain

    Args:
        semester_id: Semester id
        domain_id: Domain id
        db: Database session

    Returns:
        Task DTO list
    """
    tasks = (
        db.query(TimetableTask)
        .filter(
            TimetableTask.semester_id == semester_id,
            TimetableTask.domain_id == domain_id,
        )
        .all()
    )

    modules = fetch_modules_for_generation(
        semester_id=semester_id,
        domain_id=domain_id,
    )
    modules_map = build_modules_map(modules)

    KIND_ORDER = {
        "course": 0,
        "seminar": 1,
        "laboratory": 2,
        "onehour": 3,
        "labsem": 4,
    }

    def get_task_sort_key(task: TimetableTask):
        module_ids = task.module_ids or []
        if not module_ids:
            return ("zzz", 999)

        module = modules_map.get(str(module_ids[0]), {})
        title = module.get("title", "").lower()
        kind_order = KIND_ORDER.get(task.category, 999)

        return (title, kind_order)

    tasks.sort(key=get_task_sort_key)

    return [map_task_to_dto(task, modules_map) for task in tasks]


@router.post("/build/{semester_id}/{domain_id}", response_model=list[TaskDTO])
def generate_tasks_endpoint(
    semester_id: UUID,
    domain_id: UUID,
    replace_existing: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Builds and stores tasks for one semester and domain

    Args:
        semester_id: Semester id
        domain_id: Domain id
        replace_existing: Whether existing tasks should be replaced
        db: Database session

    Returns:
        Generated task DTO list
    """
    tasks, modules_map = generate_and_store_tasks(
        db=db,
        semester_id=semester_id,
        domain_id=domain_id,
        replace_existing=replace_existing,
    )

    return [map_task_to_dto(task, modules_map) for task in tasks]

@router.patch("/{task_id}", response_model=TaskDTO)
def update_task_endpoint(
    task_id: UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
):
    """
    Updates one task

    Args:
        task_id: Task id
        payload: Update payload
        db: Database session

    Returns:
        Updated task DTO
    """
    updated = update_task(
        db=db,
        task_id=task_id,
        payload=payload,
    )

    if updated is None:
        raise HTTPException(status_code=404, detail="Task not found")

    modules = fetch_modules_for_generation(
        semester_id=updated.semester_id,
        domain_id=updated.domain_id,
    )
    modules_map = build_modules_map(modules)

    return map_task_to_dto(updated, modules_map)

@router.put("/bulk", response_model=list[TaskDTO])
def bulk_update_tasks_endpoint(
    request: TaskBulkUpdate,
    db: Session = Depends(get_db),
):
    """
    Updates multiple tasks

    Args:
        request: Bulk update request
        db: Database session

    Returns:
        Updated task DTO list
    """
    updated_tasks = bulk_update_tasks(db, request)

    if not updated_tasks:
        return []

    first = updated_tasks[0]
    modules = fetch_modules_for_generation(
        semester_id=first.semester_id,
        domain_id=first.domain_id,
    )
    modules_map = build_modules_map(modules)

    return [map_task_to_dto(task, modules_map) for task in updated_tasks]


@router.delete("/{task_id}")
def delete_task_endpoint(
    task_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Deletes one task

    Args:
        task_id: Task id
        db: Database session

    Returns:
        Deletion status payload
    """
    deleted = delete_task_by_id(
        db=db,
        task_id=task_id,
    )

    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"deleted": True, "taskId": str(task_id)}
