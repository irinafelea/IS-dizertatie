from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.ModuleDTO import ModuleDTO


class TaskDTO(BaseModel):
    id: UUID | str | None = None
    modules: List[ModuleDTO]

    category: str
    durationHours: int
    numberOfModules: int

    common: bool

    groupIndex: Optional[int] = None
    groupSpan: Optional[int] = 1

    numberOfStudents: int
    numberOfGroups: int

    studyYearsIds: tuple[str] | tuple[str, ...]
    studyYearsLabels: str

    pairGroupKey: Optional[str] = None
    online: bool

    moduleTargets: Optional[List[dict]] = None

    model_config = ConfigDict(from_attributes=True)
