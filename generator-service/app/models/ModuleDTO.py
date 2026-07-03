from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.DisciplineForModuleDTO import DisciplineForModuleDTO
from app.models.TeacherDTO import TeacherDTO


class ModuleDTO(BaseModel):
    id: UUID
    tid: UUID | None = None
    title: Optional[str] = None
    acronym: Optional[str] = None
    category: Optional[str] = None
    numberOfHours: Optional[int] = None
    typeOfDiscipline: Optional[str] = None
    completeTeacher: Optional[str] = None
    teacher: TeacherDTO
    degreeLevel: Optional[str] = None
    discipline: DisciplineForModuleDTO | None = None

    model_config = ConfigDict(from_attributes=True)
