from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.DayDTO import DayDTO
from app.models.RoomDTO import RoomDTO
from app.models.TimeslotDTO import TimeslotDTO


class EventDTO(BaseModel):
    id: UUID
    domainId: UUID | None = None
    room: RoomDTO
    day: DayDTO
    hour: TimeslotDTO
    eventTitle: str | None = None
    showTeacher: str

    model_config = ConfigDict(from_attributes=True)
