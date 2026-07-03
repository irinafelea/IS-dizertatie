from uuid import UUID
from pydantic import BaseModel, ConfigDict


class AvailabilityDTO(BaseModel):
    id: UUID | None = None
    domainId: UUID | None = None
    semesterId: UUID | None = None
    teacherId: UUID
    dayId: UUID
    timeslotId: UUID
    availability: int
    reason: str | None = None
    weight: float | None = None

    model_config = ConfigDict(from_attributes=True)