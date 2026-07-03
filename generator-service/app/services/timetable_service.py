from typing import Iterable, List
from uuid import UUID

from sqlalchemy.orm import Session

from algorithm.timetable_algorithm import timetable_algorithm
from app.entities.Timetable import Timetable
from app.entities.TimetableModule import TimetableModule
from app.entities.TimetableTask import TimetableTask
from app.external_services.availability_service import fetch_availabilities_for_generation
from app.external_services.event_service import fetch_events_for_generation
from app.external_services.module_service import fetch_modules_for_generation
from app.mappers.map_task_to_dto import map_task_to_dto
from app.mappers.map_timetable_to_dto import map_timetable_to_dto
from app.models.TaskDTO import TaskDTO
from app.models.TimetableDTO import TimetableDTO
from app.services.service_helpers import _load_generation_reference_data, get_next_timetable_version, \
    _persist_timetable_modules_from_placements, _build_study_year_label_by_id, _build_saved_item, \
    _study_year_label_for_rooms_timetable
from app.utils.build_cache_cells import build_cells_cache
from app.utils.build_teacher_rules import build_teacher_rules
from app.utils.build_teacher_task_counts import build_teacher_task_counts
from app.utils.get_rows_and_cols import get_total_columns, get_total_rows
from app.utils.matrix import empty_matrix, place_events_into_matrix
from constants.rooms import ONLINE_ROOM
from printers.print_tasks_with_candidates import print_tasks_with_candidates
from results.rooms_timetable_matrix import build_rooms_timetable_matrix
from results.study_year_timetables_matrix import build_study_year_timetables_matrix
from results.save_generation_metrics_csv import save_generation_metrics_csv


def _get_timetable_by_version(
    db: Session,
    semester_id: UUID,
    domain_id: UUID,
    version: int,
) -> Timetable:
    """
    Loads a saved timetable by version

    Args:
        db: Database session
        semester_id: Semester id
        domain_id: Domain id
        version: Timetable version

    Returns:
        Matching timetable entity
    """
    timetable = (
        db.query(Timetable)
        .filter(
            Timetable.semester_id == semester_id,
            Timetable.domain_id == domain_id,
            Timetable.version == version,
        )
        .first()
    )

    if timetable is None:
        raise ValueError(f"Timetable version {version} not found.")

    return timetable


def _get_saved_modules_for_timetable(db: Session, timetable_id: UUID) -> list[TimetableModule]:
    """
    Loads saved timetable modules for one timetable

    Args:
        db: Database session
        timetable_id: Timetable id

    Returns:
        Persisted timetable modules
    """
    return (
        db.query(TimetableModule)
        .filter(TimetableModule.timetable_id == timetable_id)
        .order_by(
            TimetableModule.day_id,
            TimetableModule.hour_id,
            TimetableModule.row_index,
            TimetableModule.column_index,
            TimetableModule.id,
        )
        .all()
    )


def _dedupe_modules_for_room_view(
    timetable_modules: Iterable[TimetableModule],
) -> list[TimetableModule]:
    """
    Removes duplicate entries for the room view

    Args:
        timetable_modules: Persisted timetable modules

    Returns:
        Unique room-view modules
    """
    unique: list[TimetableModule] = []
    seen: set[tuple] = set()

    for entity in timetable_modules:
        key = (
            str(entity.room_id),
            str(entity.day_id),
            str(entity.hour_id),
            entity.row_index,
            entity.column_index,
            entity.number_of_columns,
            entity.even_week,
            entity.odd_week,
            entity.online,
            entity.show_discipline_title or "",
            entity.show_teacher or "",
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(entity)

    return unique


def generate_timetable(
    db: Session,
    semester_id: UUID,
    domain_id: UUID,
    enforce_bachelor_third_year_free_day: bool = False,
    seed: int | None = None,
) -> TimetableDTO:
    """
    Generates, saves, and returns a new timetable version

    Args:
        db: Database session
        semester_id: Semester id
        domain_id: Domain id
        enforce_bachelor_third_year_free_day: Enables the extra free-day rule
        seed: Optional random seed

    Returns:
        Saved timetable DTO
    """
    tasks = (
        db.query(TimetableTask)
        .filter(
            TimetableTask.semester_id == semester_id,
            TimetableTask.domain_id == domain_id,
        )
        .all()
    )

    modules, modules_map, rooms, days, timeslots = _load_generation_reference_data(
        semester_id=semester_id,
        domain_id=domain_id,
    )

    tasksDTO = [map_task_to_dto(task, modules_map) for task in tasks]

    if not tasks:
        raise ValueError("No tasks found for timetable generation.")

    # tasks_list: List[TaskDTO] = [task for task in tasksDTO if not task.online]
    tasks_list: List[TaskDTO] = list(tasksDTO)

    events = fetch_events_for_generation(semester_id, domain_id)
    usable_rooms = [room for room in rooms]

    availabilities = fetch_availabilities_for_generation(semester_id, domain_id)
    teachers_availabilities = build_teacher_rules(availabilities, days, timeslots)
    teacher_task_counts = build_teacher_task_counts(tasks_list)

    cols = get_total_columns(usable_rooms)
    rows = get_total_rows(days, timeslots)

    base_matrix = empty_matrix(cols, rows)
    base_matrix = place_events_into_matrix(base_matrix, usable_rooms, days, timeslots, events)

    # schedulable_tasks=[task for task in tasks_list if task.category == "course"]
    # schedulable_tasks = [task for task in tasks_list if task.studyYearsLabels.__contains__("IR2")]
    schedulable_tasks = [task for task in tasks_list if
                         task.studyYearsLabels.__contains__("IR1") and task.modules[0].acronym == "PII"]
    # schedulable_tasks = [task for task in tasks_list if task.studyYearsLabels.__contains__("IR1")
    #                      or task.studyYearsLabels.__contains__("IR2") or task.studyYearsLabels.__contains__("IR3")]
    # schedulable_tasks = [task for task in tasks_list if task.modules[0].degreeLevel.lower().startswith("m")]
    # schedulable_tasks = [task for task in tasks_list if not task.modules[0].degreeLevel.lower().startswith("m")]
    # schedulable_tasks: List[TaskDTO] = list(tasks_list)

    cells_cache = build_cells_cache(
        schedulable_tasks,
        base_matrix,
        usable_rooms,
        days,
        timeslots,
        teachers_availabilities,
        teacher_task_counts,
    )

    print_tasks_with_candidates(
        schedulable_tasks,
        cells_cache,
        timeslots,
        usable_rooms,
    )

    # used_modules = [m for m in modules if m.get("category") == "course"]
    # used_modules = [m for m in modules if m.get("studyYear").get("acronym") == "IR2"]
    used_modules = [m for m in modules if m.get("studyYear").get("acronym") == "IR1" and m.get("acronym") == "PII"]
    # used_modules = [m for m in modules if m.get("studyYear").get("acronym") == "IR1" or
    #                 m.get("studyYear").get("acronym") == "IR2" or m.get("studyYear").get("acronym") == "IR3"]
    # used_modules = [m for m in modules if m.get("discipline").get("degreeLevel").lower().startswith("m")]
    # used_modules = [m for m in modules if not m.get("discipline").get("degreeLevel").lower().startswith("m")]
    # used_modules= list(modules)

    version = get_next_timetable_version(db, semester_id, domain_id)

    best, generation_metrics = timetable_algorithm(
        schedulable_tasks,
        base_matrix,
        usable_rooms,
        days,
        timeslots,
        cells_cache,
        teachers_availabilities,
        teacher_task_counts,
        enforce_bachelor_third_year_free_day,
        seed,
    )

    timetable = Timetable(
        semester_id=semester_id,
        domain_id=domain_id,
        version=version,
    )
    db.add(timetable)
    db.flush()

    generated_modules = _persist_timetable_modules_from_placements(
        db=db,
        timetable_id=timetable.id,
        placements=best,
        tasks=tasksDTO,
        modules=modules,
        modules_map=modules_map,
        rooms=usable_rooms,
        days=days,
        timeslots=timeslots,
    )

    save_generation_metrics_csv(
        semester_id=str(semester_id),
        domain_id=str(domain_id),
        version=version,
        modules=used_modules,
        metrics=generation_metrics,
    )

    db.commit()
    db.refresh(timetable)

    for module in generated_modules:
        db.refresh(module)

    room_by_id = {str(room.get("id")): room for room in usable_rooms if room.get("id") is not None}
    room_by_id[str(ONLINE_ROOM["id"])] = ONLINE_ROOM
    day_by_id = {str(day.get("id")): day for day in days}
    hour_by_id = {str(hour.get("id")): hour for hour in timeslots}

    return map_timetable_to_dto(
        timetable,
        generated_modules,
        modules_map,
        room_by_id,
        day_by_id,
        hour_by_id,
    )

def get_rooms_timetable_by_version(
    db: Session,
    semester_id: UUID,
    domain_id: UUID,
    version: int,
):
    """
    Builds the room timetable view for a saved version

    Args:
        db: Database session
        semester_id: Semester id
        domain_id: Domain id
        version: Timetable version

    Returns:
        Room timetable matrix
    """
    timetable = _get_timetable_by_version(db, semester_id, domain_id, version)
    timetable_modules = _get_saved_modules_for_timetable(db, timetable.id)

    modules = fetch_modules_for_generation(
        semester_id=semester_id,
        domain_id=domain_id,
    )
    study_year_label_by_id = _build_study_year_label_by_id(modules)

    _, _, rooms, days, timeslots = _load_generation_reference_data(
        semester_id=semester_id,
        domain_id=domain_id,
    )

    items = [
        _build_saved_item(
            entity,
            _study_year_label_for_rooms_timetable(entity, study_year_label_by_id),
        )
        for entity in timetable_modules
    ]

    return build_rooms_timetable_matrix(
        items=items,
        days=days,
        timeslots=timeslots,
        rooms=rooms,
    )

def get_study_year_timetable_by_version(
    db: Session,
    semester_id: UUID,
    domain_id: UUID,
    study_year_id: UUID,
    version: int,
):
    """
    Builds the study-year timetable view for a saved version

    Args:
        db: Database session
        semester_id: Semester id
        domain_id: Domain id
        study_year_id: Study-year id
        version: Timetable version

    Returns:
        Study-year timetable matrix for the requested study year
    """
    timetable = _get_timetable_by_version(db, semester_id, domain_id, version)

    timetable_modules = (
        db.query(TimetableModule)
        .filter(
            TimetableModule.timetable_id == timetable.id,
            TimetableModule.study_year_id == study_year_id,
        )
        .order_by(
            TimetableModule.day_id,
            TimetableModule.hour_id,
            TimetableModule.row_index,
            TimetableModule.column_index,
            TimetableModule.id,
        )
        .all()
    )

    modules = fetch_modules_for_generation(
        semester_id=semester_id,
        domain_id=domain_id,
    )

    study_year_label_by_id = _build_study_year_label_by_id(modules)

    modules, _, rooms, days, timeslots = _load_generation_reference_data(
        semester_id=semester_id,
        domain_id=domain_id,
    )
    items = [
        _build_saved_item(
            entity,
            _study_year_label_for_rooms_timetable(entity, study_year_label_by_id),
        )
        for entity in timetable_modules
    ]

    matrix = build_study_year_timetables_matrix(
        items=items,
        days=days,
        timeslots=timeslots,
        modules=modules,
        rooms=rooms,
    )

    target_label = study_year_label_by_id.get(str(study_year_id), "").strip()
    if target_label and target_label in matrix:
        return matrix.get(target_label, {})

    for item in items:
        study_year_label = str(item.get("studyYearLabel") or "").strip()
        if study_year_label and study_year_label in matrix:
            return matrix.get(study_year_label, {})

    return {}
