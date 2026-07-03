from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DisciplineForModuleDTO(BaseModel):
    id: UUID | None = None
    degreeLevel: str | None = None
    title: str | None = None
    acronym: str | None = None
    color: str | None = None

    model_config = ConfigDict(from_attributes=True)
