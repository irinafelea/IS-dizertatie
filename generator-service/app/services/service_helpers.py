from typing import Iterable
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from algorithm.algorithm_classes.Placement import Placement
from algorithm.algorithm_helpers.task_segments import iter_task_segments
from app.entities.Timetable import Timetable
from app.entities.TimetableModule import TimetableModule
from app.external_services.day_service import fetch_days_for_generation
from app.external_services.module_service import fetch_modules_for_generation
from app.external_services.room_service import fetch_rooms_for_generation
from app.external_services.timeslot_service import fetch_timeslots_for_generation
from app.models.ModuleDTO import ModuleDTO
from app.models.RoomDTO import RoomDTO
from app.models.TaskDTO import TaskDTO
from app.utils.build_modules_map import build_modules_map
from constants.rooms import ONLINE_ROOM
from constants.algorithm import COLUMNS_PER_GROUP
from helpers._dget import _dget
from helpers.module import (
    groups_count,
    is_course,
    study_year_id,
    task_is_roomless,
    study_year_acr,
    build_show_discipline_title,
    build_show_teacher,
)
from helpers.task_module_target import module_target, target_study_year_entries


def get_next_timetable_version(db: Session, semester_id: UUID, domain_id: UUID) -> int:
    """
    Returns the next timetable version for a semester and domain

    Args:
        db: Database session
        semester_id: Semester id
        domain_id: Domain id

    Returns:
        Next version number
    """
    max_version = (
        db.query(func.max(Timetable.version))
        .filter(
            Timetable.semester_id == semester_id,
            Timetable.domain_id == domain_id,
        )
        .scalar()
    )

    return (max_version or 0) + 1


def _split_study_year_labels(value: str | None) -> list[str]:
    """
    Splits a combined study-year label string

    Args:
        value: Raw label string

    Returns:
        Non-empty label parts
    """
    return [part.strip() for part in str(value or "").split("+") if part.strip()]


def _build_study_year_label_map(tasks: Iterable[TaskDTO]) -> dict[str, str]:
    """
    Builds a map from study-year id to label

    Args:
        tasks: Timetable tasks

    Returns:
        Study-year label map
    """
    label_by_study_year_id: dict[str, str] = {}

    for task in tasks:
        study_year_ids = [str(x) for x in (task.studyYearsIds or [])]
        labels = _split_study_year_labels(task.studyYearsLabels)

        if len(study_year_ids) == 1 and study_year_ids[0] not in label_by_study_year_id:
            label_by_study_year_id[study_year_ids[0]] = task.studyYearsLabels
            continue

        if len(study_year_ids) == len(labels):
            for study_year_id_value, label in zip(study_year_ids, labels):
                label_by_study_year_id.setdefault(study_year_id_value, label)
    return label_by_study_year_id


def _build_study_year_targets_for_task(
    task,
    study_year_column_width_by_id: dict[str, int],
    label_by_study_year_id: dict[str, str],
) -> list[dict[str, object]]:
    """
    Builds persisted study-year targets from a task

    Args:
        task: Task-like object
        study_year_column_width_by_id: Width by study-year id
        label_by_study_year_id: Label by study-year id

    Returns:
        Study-year targets for persistence
    """
    label = str(getattr(task, "studyYearsLabels", None) or getattr(task, "study_years_labels", "") or "").strip()
    if not label:
        return []

    raw_ids = getattr(task, "studyYearsIds", None) or getattr(task, "study_years_ids", None) or []
    study_year_ids = [str(x) for x in raw_ids]
    if not study_year_ids:
        return []

    split_labels = _split_study_year_labels(label)
    targets: list[dict[str, object]] = []

    for index, study_year_id_value in enumerate(study_year_ids):
        local_label = (
            split_labels[index]
            if len(split_labels) == len(study_year_ids)
            else label_by_study_year_id.get(study_year_id_value, "")
        )
        targets.append(
            {
                "study_year_id": study_year_id_value,
                "study_year_label": local_label,
                "number_of_columns": study_year_column_width_by_id.get(study_year_id_value),
                "groupIndex": getattr(task, "groupIndex", None),
                "groupSpan": getattr(task, "groupSpan", 1),
            }
        )

    return targets


def _build_study_year_targets_for_module_target(
    target: dict,
    study_year_column_width_by_id: dict[str, int],
    label_by_study_year_id: dict[str, str],
) -> list[dict[str, object]]:
    """
    Builds persisted study-year targets from a module target

    Args:
        target: Module target payload
        study_year_column_width_by_id: Width by study-year id
        label_by_study_year_id: Label by study-year id

    Returns:
        Study-year targets for persistence
    """
    label = str(target.get("studyYearsLabels", "") or "").strip()
    if not label:
        return []

    study_year_ids = [str(x) for x in (target.get("studyYearsIds") or [])]
    if not study_year_ids:
        return []

    split_labels = _split_study_year_labels(label)
    out: list[dict[str, object]] = []
    for index, study_year_id_value in enumerate(study_year_ids):
        local_label = (
            split_labels[index]
            if len(split_labels) == len(study_year_ids)
            else label_by_study_year_id.get(study_year_id_value, "")
        )
        out.append(
            {
                "study_year_id": study_year_id_value,
                "study_year_label": local_label,
                "number_of_columns": study_year_column_width_by_id.get(study_year_id_value),
                "groupIndex": target.get("groupIndex"),
                "groupSpan": target.get("groupSpan", 1),
            }
        )
    return out


def _resolve_task_module_by_id(task, module_id: str):
    """
    Resolves a task module by id

    Args:
        task: Task-like object
        module_id: Module id

    Returns:
        Matching module or None
    """
    module_id = str(module_id or "").strip()
    if not module_id:
        return None
    for module in list(getattr(task, "modules", []) or []):
        if str(_dget(module, "id", "") or "").strip() == module_id:
            return module
    return None


def _persist_targets_for_segment(
    task,
    module_obj,
    module_index: int,
    module_ctx: dict,
    study_year_column_width_by_id: dict[str, int],
    label_by_study_year_id: dict[str, str],
) -> list[dict[str, object]]:
    """
    Builds persisted targets for one scheduled segment

    Args:
        task: Source task
        module_obj: Segment module
        module_index: Module index
        module_ctx: Module target payload
        study_year_column_width_by_id: Width by study-year id
        label_by_study_year_id: Label by study-year id

    Returns:
        Persisted targets for the segment
    """
    study_year_entries = target_study_year_entries(task, module_index, module_obj)
    targets: list[dict[str, object]] = []

    for entry in study_year_entries:
        study_year_id_value = str(entry.get("studyYearId") or "").strip()
        if not study_year_id_value:
            continue
        targets.append(
            {
                "study_year_id": study_year_id_value,
                "study_year_label": str(entry.get("studyYearLabel") or label_by_study_year_id.get(study_year_id_value, "") or ""),
                "number_of_columns": study_year_column_width_by_id.get(study_year_id_value),
                "groupIndex": module_ctx.get("groupIndex"),
                "groupSpan": module_ctx.get("groupSpan", 1),
                "moduleId": str(entry.get("moduleId") or _dget(module_obj, "id", "") or ""),
            }
        )

    if targets:
        return targets

    fallback_targets = _build_study_year_targets_for_module_target(
        module_ctx,
        study_year_column_width_by_id,
        label_by_study_year_id,
    )
    module_id = str(_dget(module_obj, "id", None) or "")
    return [{**target, "moduleId": module_id} for target in fallback_targets]


def _persisted_columns_for_module(study_year_target: dict[str, object], effective_module, default_col_idx: int, default_nr_cols: int) -> tuple[int, int]:
    """
    Computes persisted column placement for a module

    Args:
        study_year_target: Study-year target payload
        effective_module: Resolved module
        default_col_idx: Fallback group index
        default_nr_cols: Fallback group span

    Returns:
        Column index and column span
    """
    degree_level = str(
        _dget(effective_module, "degreeLevel", None)
        or _dget(_dget(effective_module, "discipline", {}) or {}, "degreeLevel", "")
        or ""
    ).strip().lower()
    columns_per_group = 1 if degree_level.startswith("m") else COLUMNS_PER_GROUP

    if is_course(effective_module):
        number_of_columns = max(1, study_year_target.get("number_of_columns") or 1)
        return 0, number_of_columns

    column_index = int(study_year_target.get("groupIndex", default_col_idx) or 0) * columns_per_group
    target_group_span = int(study_year_target.get("groupSpan", 1) or 1)
    return int(column_index), target_group_span * columns_per_group


def _build_saved_item(
    entity: TimetableModule,
    study_year_label: str,
) -> dict:
    """
    Converts a persisted module to the saved-item payload

    Args:
        entity: Persisted timetable module
        study_year_label: Display study-year label

    Returns:
        Saved-item payload
    """
    return {
        "id": str(entity.id),
        "moduleId": str(entity.module_id),
        "roomId": str(entity.room_id),
        "dayId": str(entity.day_id),
        "hourId": str(entity.hour_id),
        "rowIndex": entity.row_index,
        "columnIndex": entity.column_index,
        "numberOfColumns": entity.number_of_columns,
        "evenWeek": entity.even_week,
        "oddWeek": entity.odd_week,
        "online": entity.online,
        "showDisciplineTitle": entity.show_discipline_title,
        "showTeacher": entity.show_teacher,
        "studyYearLabel": study_year_label,
    }

def _build_study_year_label_by_id(modules: Iterable[ModuleDTO]) -> dict[str, str]:
    """
    Builds a label map from modules

    Args:
        modules: Module DTOs

    Returns:
        Study-year label map
    """
    out: dict[str, str] = {}

    for module in modules:
        sy = _dget(module, "studyYear", {}) or {}
        sy_id = str(_dget(sy, "id", "") or "").strip()
        sy_label = str(_dget(sy, "acronym", "") or "").strip()

        if sy_id and sy_label:
            out[sy_id] = sy_label

    return out

def _study_year_label_for_rooms_timetable(
    entity: TimetableModule,
    study_year_label_by_id: dict[str, str],
) -> str:
    """
    Resolves the study-year label for the room timetable

    Args:
        entity: Persisted timetable module
        study_year_label_by_id: Label by study-year id

    Returns:
        Study-year label
    """
    return study_year_label_by_id.get(str(entity.study_year_id), "")

def _study_year_label_for_saved_entity(
    entity: TimetableModule,
    modules_map: dict[str, ModuleDTO],
) -> str:
    """
    Resolves the study-year label from the module map

    Args:
        entity: Persisted timetable module
        modules_map: Module map by id

    Returns:
        Study-year label
    """
    module: ModuleDTO = modules_map.get(str(entity.module_id))
    if module is None:
        return ""
    return str(study_year_acr(module) or "").strip()


def _persist_timetable_modules_from_placements(
    db: Session,
    timetable_id: UUID,
    placements: list[Placement | None],
    tasks: Iterable[TaskDTO],
    modules: Iterable[object],
    modules_map: dict[str, object],
    rooms: list[RoomDTO],
    days: list[object],
    timeslots: list[object],
) -> list[TimetableModule]:
    """
    Persists generated placements as timetable modules

    Args:
        db: Database session
        timetable_id: Timetable id
        placements: Generated placements
        tasks: Source tasks
        modules: Source modules
        modules_map: Module map by id
        rooms: Available rooms
        days: Days list
        timeslots: Timeslots list

    Returns:
        Persisted timetable modules
    """
    study_year_column_width_by_id = _build_study_year_column_width_map(modules)
    label_by_study_year_id = _build_study_year_label_map(tasks)

    generated_modules: list[TimetableModule] = []
    spd = len(timeslots)

    for placement in placements:
        if placement is None:
            continue

        task = placement.task

        ordered_segments = iter_task_segments(
            task,
            placement.row,
            placement.parity_mask,
            placement.module_order,
        )

        for module_obj, row, segment_mask, _module_index in ordered_segments:
            module_ctx = module_target(task, _module_index)
            day_index = row // spd
            slot_index = row % spd

            if day_index >= len(days) or slot_index >= len(timeslots):
                continue

            study_year_targets = _persist_targets_for_segment(
                task,
                module_obj,
                _module_index,
                module_ctx,
                study_year_column_width_by_id,
                label_by_study_year_id,
            )
            if not study_year_targets:
                continue

            for study_year_target in study_year_targets:
                effective_module = _resolve_task_module_by_id(task, study_year_target.get("moduleId", "")) or module_obj
                column_index, number_of_columns = _persisted_columns_for_module(
                    study_year_target,
                    effective_module,
                    int(module_ctx.get("groupIndex", 0) or 0),
                    int(module_ctx.get("groupSpan", 1) or 1),
                )

                entity = TimetableModule(
                    timetable_id=timetable_id,
                    module_id=UUID(str(study_year_target["moduleId"])),
                    study_year_id=UUID(str(study_year_target["study_year_id"])),
                    room_id=UUID(str(ONLINE_ROOM["id"])) if task_is_roomless(placement.task) else UUID(str(_dget(rooms[placement.col], "id", None))),
                    day_id=UUID(str(_dget(days[day_index], "id", None))),
                    hour_id=UUID(str(_dget(timeslots[slot_index], "id", None))),
                    row_index=row,
                    column_index=column_index,
                    number_of_columns=number_of_columns,
                    even_week=bool(segment_mask & 2),
                    odd_week=bool(segment_mask & 1),
                    online=bool(placement.task.online),
                    show_discipline_title=build_show_discipline_title(effective_module),
                    show_teacher=build_show_teacher(effective_module),
                )
                db.add(entity)
                generated_modules.append(entity)

    return generated_modules


def _build_study_year_column_width_map(modules: Iterable[object]) -> dict[str, int]:
    """
    Builds the persisted width for each study year

    Args:
        modules: Source modules

    Returns:
        Width by study-year id
    """
    out: dict[str, int] = {}

    for module in modules:
        sy_id = str(study_year_id(module) or "").strip()
        if not sy_id or sy_id == "SY?":
            continue

        degree_level = str(
            _dget(module, "degreeLevel", None)
            or _dget(_dget(module, "discipline", {}) or {}, "degreeLevel", "")
            or ""
        ).strip().lower()
        columns_per_group = 1 if degree_level.startswith("m") else COLUMNS_PER_GROUP
        width = max(1, int(groups_count(module) or 1)) * columns_per_group
        out.setdefault(sy_id, width)

    return out


def _load_generation_reference_data(semester_id: UUID, domain_id: UUID):
    """
    Loads the reference data needed by timetable generation

    Args:
        semester_id: Semester id
        domain_id: Domain id

    Returns:
        Modules, module map, usable rooms, days, and timeslots
    """
    modules = fetch_modules_for_generation(
        semester_id=semester_id,
        domain_id=domain_id,
    )
    modules_map = build_modules_map(modules)
    rooms = fetch_rooms_for_generation(domain_id)
    usable_rooms = [room for room in rooms if room.get("capacity") > 21]
    days = fetch_days_for_generation()
    timeslots = fetch_timeslots_for_generation(domain_id)

    return modules, modules_map, usable_rooms, days, timeslots
