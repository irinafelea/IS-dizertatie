from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BuildingDTO(BaseModel):
    id: UUID | None = None
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)