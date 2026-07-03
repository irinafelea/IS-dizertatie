from pydantic import BaseModel
from uuid import UUID



class RoomForTimetableDTO(BaseModel):
    id: UUID
    name: str
    capacity: int
    universityRoom: bool
    information: str
    text: str
    disable: bool
    warning: str
