from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel


class TaskRequest(BaseModel):
    moduleId: UUID
    domainId: UUID
    semesterId: UUID
    kind: str
    groupIndex: Optional[int] = None
    numberOfStudents: int
    numberOfGroups: int
    studyYearsIds: List[str]
    studyYearsLabels: str
    pairGroupKey: Optional[str] = None
    pairRole: Optional[str] = None
    online: bool = False