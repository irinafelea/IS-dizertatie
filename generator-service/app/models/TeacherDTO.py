from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TeacherDTO(BaseModel):
    id: UUID | None = None
    title: str | None = None
    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    phone: str | None = None
    intern: bool | None = None

    model_config = ConfigDict(from_attributes=True)
