from uuid import UUID
from typing import List

from pydantic import ConfigDict, BaseModel

from app.models.BuildingDTO import BuildingDTO
from app.models.RoomDomainDTO import RoomDomainDTO


class RoomDTO(BaseModel):
    id: UUID
    officialName: str | None = None
    building: BuildingDTO | None = None
    capacity: int
    universityRoom: bool
    domains: List[RoomDomainDTO] | None = None
    hide: List[RoomDomainDTO] | None = None

    model_config = ConfigDict(from_attributes=True)
