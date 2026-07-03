from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.TimetableModuleDTO import TimetableModuleDTO


class TimetableDTO(BaseModel):
    id: UUID
    semesterId: UUID
    domainId: UUID
    version: int
    createdAt: datetime
    modules: list[TimetableModuleDTO]

    model_config = ConfigDict(from_attributes=True)