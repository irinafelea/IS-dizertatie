from app.mappers.map_timetable_module_to_dto import map_timetable_module_to_dto
from app.entities.Timetable import Timetable
from app.models.TimetableDTO import TimetableDTO
from app.entities.TimetableModule import TimetableModule


def map_timetable_to_dto(
    timetable: Timetable,
    modules: list[TimetableModule],
    module_by_id: dict[str, object],
    room_by_id: dict[str, object],
    day_by_id: dict[str, object],
    hour_by_id: dict[str, object],
) -> TimetableDTO:
    """
    Maps a timetable entity and its modules to a timetable DTO

    Args:
        timetable: Timetable entity
        modules: Persisted timetable modules
        module_by_id: Module map by id
        room_by_id: Room map by id
        day_by_id: Day map by id
        hour_by_id: Hour map by id

    Returns:
        Timetable DTO
    """
    return TimetableDTO(
        id=timetable.id,
        semesterId=timetable.semester_id,
        domainId=timetable.domain_id,
        version=timetable.version,
        createdAt=timetable.created_at,
        modules=[
            map_timetable_module_to_dto(
                m,
                module_by_id[str(m.module_id)],
                room_by_id[str(m.room_id)],
                day_by_id[str(m.day_id)],
                hour_by_id[str(m.hour_id)],
            )
            for m in modules
        ],
    )
