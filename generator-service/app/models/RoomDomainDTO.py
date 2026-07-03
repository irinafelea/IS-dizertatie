from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RoomDomainDTO(BaseModel):
    id: UUID
    name: str
    roomName: str | None = None
    information: str | None = None

    model_config = ConfigDict(from_attributes=True)