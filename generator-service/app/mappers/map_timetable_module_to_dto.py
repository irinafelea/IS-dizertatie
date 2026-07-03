from app.entities.TimetableModule import TimetableModule
from app.models.RoomForTimetableDTO import RoomForTimetableDTO
from app.models.TimetableModuleDTO import TimetableModuleDTO


def map_timetable_module_to_dto(
    entity: TimetableModule,
    module_dto,
    room_dto,
    day_dto,
    hour_dto,
) -> TimetableModuleDTO:
    """
    Maps a timetable module entity to a timetable module DTO

    Args:
        entity: Timetable module entity
        module_dto: Module DTO
        room_dto: Room DTO or room payload
        day_dto: Day DTO or day payload
        hour_dto: Hour DTO or hour payload

    Returns:
        Timetable module DTO
    """
    room = RoomForTimetableDTO(
        id=room_dto["id"] if isinstance(room_dto, dict) else room_dto.id,
        name=(room_dto.get("officialName") or room_dto.get("name") or ""),
        capacity=room_dto["capacity"] if isinstance(room_dto, dict) else room_dto.capacity,
        universityRoom=room_dto["universityRoom"] if isinstance(room_dto, dict) else room_dto.universityRoom,
        information=(room_dto.get("information") or "") if isinstance(room_dto, dict) else (getattr(room_dto, "information", "") or ""),
        text=(room_dto.get("text") or "") if isinstance(room_dto, dict) else (getattr(room_dto, "text", None) or getattr(room_dto, "officialName", None) or getattr(room_dto, "name", "") or ""),
        disable=bool(room_dto.get("disable", False)) if isinstance(room_dto, dict) else bool(getattr(room_dto, "disable", False)),
        warning=((room_dto.get("warning") or "") if isinstance(room_dto, dict) else (getattr(room_dto, "warning", "") or "")),
    )

    return TimetableModuleDTO(
        id=entity.id,
        module=module_dto,
        room=room,
        day=day_dto,
        hour=hour_dto,
        rowIndex=entity.row_index,
        columnIndex=entity.column_index,
        numberOfColumns=entity.number_of_columns,
        evenWeek=entity.even_week,
        oddWeek=entity.odd_week,
        online=entity.online,
        showDisciplineTitle=entity.show_discipline_title,
        showTeacher=entity.show_teacher,
    )
