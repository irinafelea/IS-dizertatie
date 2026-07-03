from pydantic import BaseModel, ConfigDict
from uuid import UUID

from app.models.DayDTO import DayDTO
from app.models.ModuleDTO import ModuleDTO
from app.models.RoomForTimetableDTO import RoomForTimetableDTO
from app.models.TimeslotDTO import TimeslotDTO


class TimetableModuleDTO(BaseModel):
    id: UUID
    module: ModuleDTO
    room: RoomForTimetableDTO
    day: DayDTO
    hour: TimeslotDTO

    rowIndex: int
    columnIndex: int
    numberOfColumns: int

    evenWeek: bool
    oddWeek: bool
    online: bool

    showDisciplineTitle: str | None = None
    showTeacher: str | None = None

    model_config = ConfigDict(from_attributes=True)
