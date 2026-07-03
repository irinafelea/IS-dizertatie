from uuid import UUID

from pydantic import ConfigDict
from pydantic import BaseModel


class TimeslotDTO(BaseModel):
    id: UUID
    startHour: str
    endHour: str

    model_config = ConfigDict(from_attributes=True)