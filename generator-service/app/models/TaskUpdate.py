import uuid
from typing import Optional

from pydantic import BaseModel


class TaskUpdate(BaseModel):
    id: uuid.UUID | None = None
    online: Optional[bool] = None
    numberOfStudents: Optional[int] = None
    numberOfGroups: Optional[int] = None
    groupSpan: Optional[int] = None
    groupIndex: Optional[int] = None
