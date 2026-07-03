from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StudyYearDTO(BaseModel):
    id: UUID | None = None
    year: int | None = None
    acronym: str | None = None
    numberOfGroups: int | None = None
    numberOfSubgroups: int | None = None
    numberOfStudents: int | None = None

    model_config = ConfigDict(from_attributes=True)